"""ORM models package.

Importing this module registers all model classes with :class:`covet.db.Base`.
"""

from covet.models.app_setting import AppSetting
from covet.models.audit import AuditLogEntry
from covet.models.base import TimestampMixin, ULIDPrimaryKey, ulid_str
from covet.models.category import Category
from covet.models.collection import Collection
from covet.models.contact import Contact
from covet.models.document import Document
from covet.models.invitation import Invitation
from covet.models.item import Item
from covet.models.item_comment import ItemComment
from covet.models.item_lot import ItemLot
from covet.models.item_template import ItemTemplate
from covet.models.loan import Loan
from covet.models.location import Location
from covet.models.maintenance import (
    Chore,
    ChoreCompletion,
    MaintenanceCompletion,
    MaintenanceTask,
    MaintenanceTaskConsumable,
)
from covet.models.manual_bundle import BundleAsset, BundleItem, ManualBundle
from covet.models.metadata_cache import MetadataCacheEntry
from covet.models.notification import NotificationPreference
from covet.models.photo import Photo
from covet.models.scraper_registry_pin import ScraperRegistryPin
from covet.models.share_link import ShareLink
from covet.models.sync_doc import AutomergeChange, AutomergeDoc
from covet.models.tag import ItemTag, Tag
from covet.models.user import (
    APIToken,
    CollectionMembership,
    OIDCIdentity,
    Session,
    User,
)
from covet.models.webhook import Webhook, WebhookDelivery, WebhookEventType

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
    "Tag",
    "TimestampMixin",
    "ULIDPrimaryKey",
    "User",
    "Webhook",
    "WebhookDelivery",
    "WebhookEventType",
    "ulid_str",
]
