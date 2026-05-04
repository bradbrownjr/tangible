"""ORM models package.

Importing this module registers all model classes with :class:`tangible.db.Base`.
"""

from tangible.models.app_setting import AppSetting
from tangible.models.audit import AuditLogEntry
from tangible.models.base import TimestampMixin, ULIDPrimaryKey, ulid_str
from tangible.models.category import Category
from tangible.models.collection import Collection
from tangible.models.contact import Contact
from tangible.models.document import Document
from tangible.models.invitation import Invitation
from tangible.models.item import Item
from tangible.models.item_comment import ItemComment
from tangible.models.item_lot import ItemLot
from tangible.models.item_template import ItemTemplate
from tangible.models.loan import Loan
from tangible.models.location import Location
from tangible.models.maintenance import (
    Chore,
    ChoreCompletion,
    MaintenanceCompletion,
    MaintenanceTask,
    MaintenanceTaskConsumable,
)
from tangible.models.manual_bundle import BundleAsset, BundleItem, ManualBundle
from tangible.models.metadata_cache import MetadataCacheEntry
from tangible.models.notification import NotificationPreference
from tangible.models.photo import Photo
from tangible.models.scraper_registry_pin import ScraperRegistryPin
from tangible.models.share_link import ShareLink
from tangible.models.shopping import ListType, ShoppingItem, ShoppingStore, ShoppingStoreAisle
from tangible.models.sync_doc import AutomergeChange, AutomergeDoc
from tangible.models.tag import ItemTag, Tag
from tangible.models.user import (
    APIToken,
    CollectionMembership,
    OIDCIdentity,
    Session,
    User,
)
from tangible.models.webhook import Webhook, WebhookDelivery, WebhookEventType

__all__ = [
    "APIToken",
    "AppSetting",
    "AuditLogEntry",
    "AutomergeChange",
    "AutomergeDoc",
    "BundleAsset",
    "BundleItem",
    "Category",
    "Chore",
    "ChoreCompletion",
    "Collection",
    "CollectionMembership",
    "Contact",
    "Document",
    "Invitation",
    "Item",
    "ItemComment",
    "ItemLot",
    "ItemTag",
    "ItemTemplate",
    "ListType",
    "Loan",
    "Location",
    "MaintenanceCompletion",
    "MaintenanceTask",
    "MaintenanceTaskConsumable",
    "ManualBundle",
    "MetadataCacheEntry",
    "NotificationPreference",
    "OIDCIdentity",
    "Photo",
    "ScraperRegistryPin",
    "Session",
    "ShareLink",
    "ShoppingItem",
    "ShoppingStore",
    "ShoppingStoreAisle",
    "Tag",
    "TimestampMixin",
    "ULIDPrimaryKey",
    "User",
    "Webhook",
    "WebhookDelivery",
    "WebhookEventType",
    "ulid_str",
]
