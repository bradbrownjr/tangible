"""Auth subsystem (local password + session/token)."""

from tangible.auth.deps import (
    AuthContext,
    require_admin,
    require_collection_role,
    require_user,
)
from tangible.auth.service import (
    authenticate,
    create_api_token,
    create_session,
    create_user,
    revoke_session,
)

__all__ = [
    "AuthContext",
    "authenticate",
    "create_api_token",
    "create_session",
    "create_user",
    "require_admin",
    "require_collection_role",
    "require_user",
    "revoke_session",
]
