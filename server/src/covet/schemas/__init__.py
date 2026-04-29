"""Pydantic v2 schemas for the public API."""

from covet.schemas.audit import AuditLogRead
from covet.schemas.auth import (
    LoginRequest,
    OIDCProviderInfo,
    RegisterRequest,
    SessionInfo,
    TokenInfo,
)
from covet.schemas.collection import (
    CollectionCreate,
    CollectionRead,
    CollectionUpdate,
    MembershipCreate,
    MembershipDetail,
    MembershipRead,
    MembershipUpdate,
    ShareLinkCreate,
    ShareLinkRead,
)
from covet.schemas.contact import ContactCreate, ContactRead, ContactUpdate
from covet.schemas.document import DocumentRead, DocumentUpdate
from covet.schemas.invitation import (
    InvitationCreate,
    InvitationCreated,
    InvitationPreview,
    InvitationRead,
)
from covet.schemas.item import ItemCreate, ItemRead, ItemUpdate
from covet.schemas.item_template import (
    ItemTemplateCreate,
    ItemTemplateRead,
    ItemTemplateUpdate,
    TemplateField,
)
from covet.schemas.loan import LoanCreate, LoanRead, LoanUpdate
from covet.schemas.maintenance import (
    MaintenanceTaskCreate,
    MaintenanceTaskRead,
    MaintenanceTaskUpdate,
)
from covet.schemas.photo import PhotoFromUrl, PhotoRead, PhotoUpdate
from covet.schemas.sync import (
    SyncChange,
    SyncChangeUpload,
    SyncDocSummary,
    SyncPullResponse,
    SyncPushRequest,
    SyncPushResponse,
    SyncSnapshotResponse,
    SyncSnapshotUpload,
)
from covet.schemas.tag import TagCreate, TagRead, TagUpdate
from covet.schemas.user import UserCreate, UserRead, UserUpdate

__all__ = [
    "AuditLogRead",
    "CollectionCreate",
    "CollectionRead",
    "CollectionUpdate",
    "ContactCreate",
    "ContactRead",
    "ContactUpdate",
    "DocumentRead",
    "DocumentUpdate",
    "InvitationCreate",
    "InvitationCreated",
    "InvitationPreview",
    "InvitationRead",
    "ItemCreate",
    "ItemRead",
    "ItemTemplateCreate",
    "ItemTemplateRead",
    "ItemTemplateUpdate",
    "ItemUpdate",
    "LoanCreate",
    "LoanRead",
    "LoanUpdate",
    "LoginRequest",
    "MaintenanceTaskCreate",
    "MaintenanceTaskRead",
    "MaintenanceTaskUpdate",
    "MembershipCreate",
    "MembershipDetail",
    "MembershipRead",
    "MembershipUpdate",
    "OIDCProviderInfo",
    "PhotoFromUrl",
    "PhotoRead",
    "PhotoUpdate",
    "RegisterRequest",
    "SessionInfo",
    "ShareLinkCreate",
    "ShareLinkRead",
    "SyncChange",
    "SyncChangeUpload",
    "SyncDocSummary",
    "SyncPullResponse",
    "SyncPushRequest",
    "SyncPushResponse",
    "SyncSnapshotResponse",
    "SyncSnapshotUpload",
    "TagCreate",
    "TagRead",
    "TagUpdate",
    "TemplateField",
    "TokenInfo",
    "UserCreate",
    "UserRead",
    "UserUpdate",
]
