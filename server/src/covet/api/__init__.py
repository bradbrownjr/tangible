"""API routers."""

from fastapi import APIRouter

from covet.api import audit as audit_router
from covet.api import auth as auth_router
from covet.api import collections as collections_router
from covet.api import contacts as contacts_router
from covet.api import documents as documents_router
from covet.api import imports as imports_router
from covet.api import invitations as invitations_router
from covet.api import item_templates as item_templates_router
from covet.api import items as items_router
from covet.api import loans as loans_router
from covet.api import meta as meta_router
from covet.api import metadata as metadata_router
from covet.api import share as share_router
from covet.api import sync as sync_router
from covet.api import tags as tags_router

api_router = APIRouter()
api_router.include_router(meta_router.router)
api_router.include_router(auth_router.router)
api_router.include_router(collections_router.router)
api_router.include_router(items_router.router)
api_router.include_router(item_templates_router.router)
api_router.include_router(tags_router.router)
api_router.include_router(contacts_router.router)
api_router.include_router(loans_router.router)
api_router.include_router(sync_router.router)
api_router.include_router(imports_router.router)
api_router.include_router(share_router.router)
api_router.include_router(invitations_router.router)
api_router.include_router(audit_router.router)
api_router.include_router(metadata_router.router)
api_router.include_router(documents_router.router)

__all__ = ["api_router"]
