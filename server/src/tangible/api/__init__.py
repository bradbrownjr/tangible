"""API routers."""

from fastapi import APIRouter

from tangible.api import audit as audit_router
from tangible.api import auth as auth_router
from tangible.api import categories as categories_router
from tangible.api import chores as chores_router
from tangible.api import collections as collections_router
from tangible.api import comments as comments_router
from tangible.api import contacts as contacts_router
from tangible.api import documents as documents_router
from tangible.api import grocery as grocery_router
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
api_router.include_router(grocery_router.router)
api_router.include_router(maintenance_router.router)
api_router.include_router(chores_router.router)
api_router.include_router(notifications_router.router)
api_router.include_router(photos_router.router)
api_router.include_router(manual_bundles_router.router)
api_router.include_router(system_router.router)
api_router.include_router(webhooks_router.router)
api_router.include_router(ha_router.router)

__all__ = ["api_router"]
