"""Tests for the observability surface (/metrics + access log)."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_metrics_endpoint_exposes_prometheus_format(client: TestClient) -> None:
    # Generate some traffic to ensure counters appear.
    client.get("/api/healthz")
    client.get("/api/healthz")
    r = client.get("/metrics")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/plain")
    body = r.text
    assert "tangible_http_requests_total" in body
    assert "tangible_http_request_duration_seconds" in body
    # Healthz traffic should be visible by route template.
    assert "/healthz" in body
