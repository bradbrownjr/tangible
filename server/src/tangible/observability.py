"""Observability: request logging + Prometheus metrics.

Both pieces are optional and gated by settings (`metrics_enabled`,
`request_log_enabled`). Metrics use ``prometheus_client``'s default
registry; the ``/metrics`` endpoint is unauthenticated by design — bind
it behind your reverse proxy if exposure matters.
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable

import structlog
from fastapi import FastAPI, Request
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Histogram,
    generate_latest,
    multiprocess,
)
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from starlette.types import ASGIApp

from tangible.config import Settings

log = structlog.get_logger("tangible.access")


# --- Metrics -----------------------------------------------------------------------------


REQUESTS_TOTAL = Counter(
    "tangible_http_requests_total",
    "Count of HTTP requests by method, route template and status class.",
    labelnames=("method", "route", "status"),
)

REQUEST_DURATION = Histogram(
    "tangible_http_request_duration_seconds",
    "HTTP request latency by method and route template.",
    labelnames=("method", "route"),
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)


def _route_template(request: Request) -> str:
    """Return the matched route's path template, or the raw path as fallback.

    Using the template keeps cardinality bounded — `/items/{id}` instead of
    one series per UUID.
    """
    route = request.scope.get("route")
    if route is not None and getattr(route, "path", None):
        return route.path
    return request.url.path


# --- Middleware --------------------------------------------------------------------------


class AccessLogMiddleware(BaseHTTPMiddleware):
    """Emit one structured log line per request and record metrics."""

    def __init__(self, app: ASGIApp, *, log_requests: bool, record_metrics: bool) -> None:
        super().__init__(app)
        self._log = log_requests
        self._metrics = record_metrics

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        start = time.perf_counter()
        response: Response | None = None
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            duration = time.perf_counter() - start
            route = _route_template(request)
            if self._metrics:
                status_class = f"{status_code // 100}xx"
                REQUESTS_TOTAL.labels(
                    method=request.method, route=route, status=status_class
                ).inc()
                REQUEST_DURATION.labels(method=request.method, route=route).observe(duration)
            if self._log:
                log.info(
                    "http_request",
                    method=request.method,
                    path=request.url.path,
                    route=route,
                    status=status_code,
                    duration_ms=round(duration * 1000, 2),
                    client=request.client.host if request.client else None,
                )


# --- Wiring ------------------------------------------------------------------------------


def install_observability(app: FastAPI, settings: Settings) -> None:
    """Attach the access-log + metrics middleware and mount /metrics."""
    if not (settings.request_log_enabled or settings.metrics_enabled):
        return
    app.add_middleware(
        AccessLogMiddleware,
        log_requests=settings.request_log_enabled,
        record_metrics=settings.metrics_enabled,
    )
    if settings.metrics_enabled:

        @app.get("/metrics", include_in_schema=False)
        def metrics() -> Response:
            # Support multi-process deployments (gunicorn/uvicorn workers) when
            # PROMETHEUS_MULTIPROC_DIR is set; fall back to default registry.
            import os

            if os.environ.get("PROMETHEUS_MULTIPROC_DIR"):
                registry = CollectorRegistry()
                multiprocess.MultiProcessCollector(registry)
                payload = generate_latest(registry)
            else:
                payload = generate_latest()
            return Response(content=payload, media_type=CONTENT_TYPE_LATEST)
