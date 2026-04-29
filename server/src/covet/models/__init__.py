"""ORM models package.

Importing this module registers all model classes with :class:`covet.db.Base`.
"""

from covet.models.audit import AuditLogEntry
from covet.models.base import TimestampMixin, ULIDPrimaryKey, ulid_str
from covet.models.collection import Collection
from covet.models.contact import Contact
from covet.models.invitation import Invitation
from covet.models.item import Item, ItemType
from covet.models.loan import Loan
from covet.models.metadata_cache import MetadataCacheEntry
from covet.models.photo import Photo
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

__all__ = [
    "APIToken",
    "AuditLogEntry",
    "AutomergeChange",
    "AutomergeDoc",
    "Collection",
    "CollectionMembership",
    "Contact",
    "Invitation",
    "Item",
    "ItemTag",
    "ItemType",
    "Loan",
    "MetadataCacheEntry",
    "OIDCIdentity",
    "Photo",
    "Session",
    "ShareLink",
    "Tag",
    "TimestampMixin",
    "ULIDPrimaryKey",
    "User",
    "ulid_str",
]
