"""Pydantic v2 schemas for the public API."""

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
from covet.schemas.item import ItemCreate, ItemRead, ItemUpdate
from covet.schemas.loan import LoanCreate, LoanRead, LoanUpdate
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
    "CollectionCreate",
    "CollectionRead",
    "CollectionUpdate",
    "ContactCreate",
    "ContactRead",
    "ContactUpdate",
    "ItemCreate",
    "ItemRead",
    "ItemUpdate",
    "LoanCreate",
    "LoanRead",
    "LoanUpdate",
    "LoginRequest",
    "MembershipCreate",
    "MembershipDetail",
    "MembershipRead",
    "MembershipUpdate",
    "OIDCProviderInfo",
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
    "TokenInfo",
    "UserCreate",
    "UserRead",
    "UserUpdate",
]
