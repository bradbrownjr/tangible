"""API routers."""

from fastapi import APIRouter
from starlette.requests import Request
from starlette.responses import RedirectResponse

from tangible.api import audit as audit_router
from tangible.api import auth as auth_router
from tangible.api import categories as categories_router
from tangible.api import chores as chores_router
from tangible.api import collections as collections_router
from tangible.api import comments as comments_router
from tangible.api import contacts as contacts_router
from tangible.api import documents as documents_router
from tangible.api import ha as ha_router
from tangible.api import imports as imports_router
from tangible.api import inventory as inventory_router
from tangible.api import invitations as invitations_router
from tangible.api import item_templates as item_templates_router
from tangible.api import items as items_router
from tangible.api import loans as loans_router
from tangible.api import locations as locations_router
from tangible.api import maintenance as maintenance_router
from tangible.api import manual_bundles as manual_bundles_router
from tangible.api import meta as meta_router
from tangible.api import metadata as metadata_router
from tangible.api import notifications as notifications_router
from tangible.api import photos as photos_router
from tangible.api import share as share_router
from tangible.api import shopping as shopping_router
from tangible.api import sync as sync_router
from tangible.api import system as system_router
from tangible.api import tags as tags_router
from tangible.api import webhooks as webhooks_router

api_router = APIRouter()
api_router.include_router(meta_router.router)
api_router.include_router(auth_router.router)
api_router.include_router(collections_router.router)
api_router.include_router(categories_router.router)
api_router.include_router(items_router.router)
api_router.include_router(comments_router.router)
api_router.include_router(inventory_router.router)
api_router.include_router(item_templates_router.router)
api_router.include_router(tags_router.router)
api_router.include_router(contacts_router.router)
api_router.include_router(loans_router.router)
api_router.include_router(locations_router.router)
api_router.include_router(sync_router.router)
api_router.include_router(imports_router.router)
api_router.include_router(share_router.router)
api_router.include_router(invitations_router.router)
api_router.include_router(audit_router.router)
api_router.include_router(metadata_router.router)
api_router.include_router(documents_router.router)
api_router.include_router(shopping_router.router)
# Backward-compat shim: redirect /grocery/* -> /lists/* for older Android clients
_grocery_compat = APIRouter(prefix="/grocery", tags=["shopping"])

@_grocery_compat.api_route("/{path:path}", methods=["GET", "POST", "PATCH", "DELETE", "PUT"])
async def _grocery_compat_redirect(request: Request, path: str = ""):
    # Swap /grocery/ -> /lists/ in the path while preserving scheme, host, port and query string.
    new_path = request.url.path.replace("/grocery/", "/lists/", 1)
    redirect_url = request.url.replace(path=new_path)
    return RedirectResponse(url=str(redirect_url), status_code=307)

api_router.include_router(_grocery_compat)
api_router.include_router(maintenance_router.router)
api_router.include_router(chores_router.router)
api_router.include_router(notifications_router.router)
api_router.include_router(photos_router.router)
api_router.include_router(manual_bundles_router.router)
api_router.include_router(system_router.router)
api_router.include_router(webhooks_router.router)
api_router.include_router(ha_router.router)

__all__ = ["api_router"]
