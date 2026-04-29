"""URL metadata scraping endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from covet.auth.deps import AuthContext, require_user
from covet.services.metadata import ScrapeError, scrape

router = APIRouter(prefix="/metadata", tags=["metadata"])


class ScrapeRequest(BaseModel):
    url: str = Field(min_length=8, max_length=2048)


class ScrapeResponse(BaseModel):
    provider: str
    url: str
    title: str | None = None
    description: str | None = None
    image_url: str | None = None
    category: str | None = None
    attrs: dict = {}


@router.post("/scrape", response_model=ScrapeResponse)
def scrape_url(
    payload: ScrapeRequest,
    _: AuthContext = Depends(require_user),
) -> ScrapeResponse:
    try:
        result = scrape(payload.url)
    except ScrapeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return ScrapeResponse(
        provider=result.provider,
        url=result.url,
        title=result.title,
        description=result.description,
        image_url=result.image_url,
        category=result.category,
        attrs=result.attrs,
    )
