"""Authentication endpoints (local password + sessions + API tokens + OIDC)."""

from __future__ import annotations

import base64
import hashlib
import io
import json
import secrets
import zipfile

import pyotp
import qrcode
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse, StreamingResponse
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from covet.auth import oidc as oidc_service
from covet.auth import service as auth_service
from covet.auth.deps import AuthContext, require_admin, require_user
from covet.config import Settings, get_settings
from covet.db import get_session
from covet.hardening import DEFAULT_LOGIN_LIMIT, limiter
from covet.models import APIToken, User
from covet.schemas import (
    LoginRequest,
    MeUpdate,
    RegisterRequest,
    SessionInfo,
    TokenInfo,
    UserCreate,
    UserRead,
)
from covet.schemas.auth import (
    AccountDeleteRequest,
    TOTPDisableRequest,
    TOTPLoginChallenge,
    TOTPLoginRequest,
    TOTPSetupResponse,
    TOTPStatusResponse,
    TOTPVerifyRequest,
)

router = APIRouter(prefix="/auth", tags=["auth"])

_TOTP_TICKET_SALT = "covet-totp-login"
_TOTP_TICKET_MAX_AGE = 300  # 5 minutes
_BACKUP_CODE_COUNT = 8
_BACKUP_CODE_LEN = 10


def _set_session_cookie(response: Response, raw: str, settings: Settings) -> None:
    response.set_cookie(
        settings.session_cookie_name,
        raw,
        max_age=settings.session_ttl_hours * 3600,
        httponly=True,
        secure=bool(settings.session_cookie_secure),
        samesite=settings.session_cookie_samesite,
        path="/",
    )


def _sign_totp_ticket(user_id: str, secret_key: str) -> str:
    s = URLSafeTimedSerializer(secret_key, salt=_TOTP_TICKET_SALT)
    return s.dumps(user_id)


def _unsign_totp_ticket(ticket: str, secret_key: str) -> str | None:
    s = URLSafeTimedSerializer(secret_key, salt=_TOTP_TICKET_SALT)
    try:
        return s.loads(ticket, max_age=_TOTP_TICKET_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None


def _hash_backup_code(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


def _generate_backup_codes() -> tuple[list[str], list[str]]:
    """Return (plaintext_codes, hashed_codes)."""
    plain = [secrets.token_urlsafe(_BACKUP_CODE_LEN)[:_BACKUP_CODE_LEN].upper() for _ in range(_BACKUP_CODE_COUNT)]
    hashed = [_hash_backup_code(c) for c in plain]
    return plain, hashed


def _verify_totp_or_backup(user: User, code: str) -> bool:
    """Verify a 6-digit TOTP code or a backup code. Consumes backup codes."""
    if not user.totp_secret:
        return False
    totp = pyotp.TOTP(user.totp_secret)
    if totp.verify(code, valid_window=1):
        return True
    # Check backup codes
    stored: list[str] = json.loads(user.totp_backup_codes) if user.totp_backup_codes else []
    code_hash = _hash_backup_code(code.upper().strip())
    if code_hash in stored:
        stored.remove(code_hash)
        user.totp_backup_codes = json.dumps(stored)
        return True
    return False


def _make_qr_png_b64(uri: str) -> str:
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


@router.post("/login")
@limiter.limit(DEFAULT_LOGIN_LIMIT)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: DBSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> SessionInfo | TOTPLoginChallenge:
    user = auth_service.authenticate(db, username=payload.username, password=payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )
    if user.totp_enabled:
        ticket = _sign_totp_ticket(user.id, settings.secret_key)
        return TOTPLoginChallenge(totp_required=True, ticket=ticket)
    session, raw = auth_service.create_session(
        db,
        user=user,
        settings=settings,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    _set_session_cookie(response, raw, settings)
    return SessionInfo(user=UserRead.model_validate(user), expires_at=session.expires_at)


@router.post("/totp/confirm-login", response_model=SessionInfo)
@limiter.limit(DEFAULT_LOGIN_LIMIT)
def totp_confirm_login(
    payload: TOTPLoginRequest,
    request: Request,
    response: Response,
    db: DBSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> SessionInfo:
    user_id = _unsign_totp_ticket(payload.ticket, settings.secret_key)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="TOTP ticket expired or invalid",
        )
    user = db.get(User, user_id)
    if user is None or not user.is_active or not user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )
    if not _verify_totp_or_backup(user, payload.code):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid TOTP code"
        )
    session, raw = auth_service.create_session(
        db,
        user=user,
        settings=settings,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    _set_session_cookie(response, raw, settings)
    return SessionInfo(user=UserRead.model_validate(user), expires_at=session.expires_at)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    response: Response,
    db: DBSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> Response:
    cookie = request.cookies.get(settings.session_cookie_name)
    if cookie:
        auth_service.revoke_session(db, raw_token=cookie)
        db.commit()
    response.delete_cookie(settings.session_cookie_name, path="/")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
@limiter.limit(DEFAULT_LOGIN_LIMIT)
def register(
    payload: RegisterRequest,
    request: Request,
    db: DBSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> UserRead:
    is_first_user = db.scalar(select(User.id).limit(1)) is None
    if not is_first_user and not settings.registration_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Registration is disabled"
        )
    user = auth_service.create_user(
        db,
        username=payload.username,
        password=payload.password,
        email=payload.email,
        display_name=payload.display_name,
        is_admin=is_first_user,
    )
    db.commit()
    return UserRead.model_validate(user)


@router.get("/me", response_model=UserRead)
def me(auth: AuthContext = Depends(require_user)) -> UserRead:
    return UserRead.model_validate(auth.user)


@router.patch("/me", response_model=UserRead)
def update_me(
    payload: MeUpdate,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> UserRead:
    user = auth.user
    if payload.display_name is not None:
        user.display_name = payload.display_name or None
    if payload.email is not None:
        user.email = payload.email or None
    if payload.password:
        from covet.security import hash_password

        user.password_hash = hash_password(payload.password)
    db.flush()
    db.commit()
    return UserRead.model_validate(user)


# --- TOTP 2FA -------------------------------------------------------------------------


@router.get("/totp", response_model=TOTPStatusResponse)
def totp_status(auth: AuthContext = Depends(require_user)) -> TOTPStatusResponse:
    user = auth.user
    remaining = 0
    if user.totp_enabled and user.totp_backup_codes:
        remaining = len(json.loads(user.totp_backup_codes))
    return TOTPStatusResponse(enabled=user.totp_enabled, backup_codes_remaining=remaining)


@router.post("/totp/setup", response_model=TOTPSetupResponse)
def totp_setup(
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> TOTPSetupResponse:
    """Generate a TOTP secret for the account. Does NOT enable 2FA yet — call
    POST /auth/totp/verify with a valid code to activate."""
    user = auth.user
    if user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="2FA is already enabled"
        )
    secret = pyotp.random_base32()
    user.totp_secret = secret
    db.commit()
    totp = pyotp.TOTP(secret)
    qr_uri = totp.provisioning_uri(name=user.username, issuer_name="Covet")
    return TOTPSetupResponse(
        secret=secret,
        qr_uri=qr_uri,
        qr_png_b64=_make_qr_png_b64(qr_uri),
    )


@router.post("/totp/verify")
def totp_verify(
    payload: TOTPVerifyRequest,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> dict:
    """Verify a TOTP code and activate 2FA. Returns plaintext backup codes (shown once)."""
    user = auth.user
    if not user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Call /auth/totp/setup first",
        )
    if user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="2FA is already enabled"
        )
    totp = pyotp.TOTP(user.totp_secret)
    if not totp.verify(payload.code, valid_window=1):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid TOTP code"
        )
    plain_codes, hashed_codes = _generate_backup_codes()
    user.totp_enabled = True
    user.totp_backup_codes = json.dumps(hashed_codes)
    db.commit()
    return {"enabled": True, "backup_codes": plain_codes}


@router.delete("/totp", status_code=status.HTTP_204_NO_CONTENT)
def totp_disable(
    payload: TOTPDisableRequest,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
    settings: Settings = Depends(get_settings),
) -> Response:
    """Disable 2FA. Requires current password and (if 2FA is active) a valid TOTP code."""
    user = auth.user
    if not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot disable 2FA on an OIDC-only account",
        )
    from covet.security import verify_password

    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password"
        )
    if user.totp_enabled:
        if not payload.totp_code:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="totp_code is required to disable 2FA",
            )
        if not _verify_totp_or_backup(user, payload.totp_code):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid TOTP code"
            )
    user.totp_secret = None
    user.totp_enabled = False
    user.totp_backup_codes = None
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/totp/regenerate-backup-codes")
def totp_regenerate_backup_codes(
    payload: TOTPVerifyRequest,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> dict:
    """Regenerate backup codes (requires a valid TOTP code to prove device access)."""
    user = auth.user
    if not user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="2FA is not enabled"
        )
    if not _verify_totp_or_backup(user, payload.code):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid TOTP code"
        )
    plain_codes, hashed_codes = _generate_backup_codes()
    user.totp_backup_codes = json.dumps(hashed_codes)
    db.commit()
    return {"backup_codes": plain_codes}


# --- Account self-service (export + delete) -------------------------------------------


@router.get("/me/export")
def export_account(
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> StreamingResponse:
    """Download a ZIP of all account data (JSON backup + photo/document file list).

    The JSON backup uses the same format as ``covet backup`` CLI and can be
    restored via ``covet restore`` or the web import wizard.
    """
    from covet.importers.json_backup import export_user

    user = auth.user
    payload = export_user(db, user=user)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "backup.json",
            json.dumps(payload, indent=2, default=str),
        )
        zf.writestr(
            "README.txt",
            (
                "This archive was exported from Covet.\n\n"
                "backup.json contains all collections, items, tags, contacts, and loans.\n"
                "Restore it via: covet restore backup.json\n"
                "or through the web UI at /import (JSON restore tab).\n"
            ),
        )
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="covet-export-{user.username}.zip"'},
    )


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    payload: AccountDeleteRequest,
    request: Request,
    response: Response,
    db: DBSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    auth: AuthContext = Depends(require_user),
) -> Response:
    """Permanently delete the signed-in account and all owned data.

    Requires current password. If 2FA is enabled, ``totp_code`` is also required.
    Collections where this user is the **sole owner** are deleted (cascade). Collections
    with other owners are left intact; only this user's membership is removed.
    """
    from covet.models.collection import Collection, CollectionMembership

    user = auth.user
    if not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete an OIDC-only account via this endpoint",
        )
    from covet.security import verify_password

    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password"
        )
    if user.totp_enabled:
        if not payload.totp_code:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="totp_code is required",
            )
        if not _verify_totp_or_backup(user, payload.totp_code):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid TOTP code"
            )

    # Delete collections where this user is the sole owner.
    owned = db.scalars(
        select(Collection).where(Collection.owner_id == user.id)
    ).all()
    for col in owned:
        other_owners = db.scalar(
            select(CollectionMembership).where(
                CollectionMembership.collection_id == col.id,
                CollectionMembership.user_id != user.id,
                CollectionMembership.role == "owner",
            )
        )
        if other_owners is None:
            db.delete(col)

    db.delete(user)
    db.commit()

    cookie = request.cookies.get(settings.session_cookie_name)
    if cookie:
        response.delete_cookie(settings.session_cookie_name, path="/")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- Admin user management ---------------------------------------------------------------


@router.post("/users", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def admin_create_user(
    payload: UserCreate,
    db: DBSession = Depends(get_session),
    _: AuthContext = Depends(require_admin),
) -> UserRead:
    user = auth_service.create_user(
        db,
        username=payload.username,
        password=payload.password,
        email=payload.email,
        display_name=payload.display_name,
        is_admin=payload.is_admin,
    )
    db.commit()
    return UserRead.model_validate(user)


# --- API tokens ---------------------------------------------------------------------------


@router.post("/tokens", response_model=TokenInfo, status_code=status.HTTP_201_CREATED)
def create_token(
    name: str,
    db: DBSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    auth: AuthContext = Depends(require_user),
) -> TokenInfo:
    token, raw = auth_service.create_api_token(
        db, user=auth.user, name=name, ttl_days=settings.api_token_ttl_days
    )
    db.commit()
    return TokenInfo(
        id=token.id,
        name=token.name,
        token=raw,
        last_used_at=token.last_used_at,
        expires_at=token.expires_at,
        created_at=token.created_at,
    )


@router.get("/tokens", response_model=list[TokenInfo])
def list_tokens(
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> list[TokenInfo]:
    rows = db.scalars(
        select(APIToken).where(APIToken.user_id == auth.user.id).order_by(APIToken.created_at)
    ).all()
    return [
        TokenInfo(
            id=t.id,
            name=t.name,
            token=None,
            last_used_at=t.last_used_at,
            expires_at=t.expires_at,
            created_at=t.created_at,
        )
        for t in rows
        if not t.revoked
    ]


@router.delete("/tokens/{token_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_token(
    token_id: str,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> Response:
    token = db.get(APIToken, token_id)
    if token is None or token.user_id != auth.user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token not found")
    token.revoked = True
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- OIDC ---------------------------------------------------------------------------------


def _redirect_uri(request: Request, settings: Settings, provider_name: str) -> str:
    provider = oidc_service.get_provider(settings, provider_name)
    if provider and provider.redirect_uri:
        return provider.redirect_uri
    base = settings.public_url.rstrip("/")
    return f"{base}/auth/oidc/{provider_name}/callback"


@router.get("/oidc/{provider_name}/login", include_in_schema=False)
async def oidc_login(
    provider_name: str,
    request: Request,
    next: str = "/",
    settings: Settings = Depends(get_settings),
) -> Response:
    if not settings.oidc_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OIDC disabled")
    client = oidc_service.client_for(settings, provider_name)
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown OIDC provider")
    request.session["oidc_next"] = next or "/"
    return await client.authorize_redirect(
        request, _redirect_uri(request, settings, provider_name)
    )


@router.get("/oidc/{provider_name}/callback", include_in_schema=False)
async def oidc_callback(
    provider_name: str,
    request: Request,
    db: DBSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> Response:
    if not settings.oidc_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OIDC disabled")
    provider = oidc_service.get_provider(settings, provider_name)
    client = oidc_service.client_for(settings, provider_name)
    if provider is None or client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown OIDC provider")

    try:
        token = await client.authorize_access_token(request)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OIDC exchange failed: {exc.__class__.__name__}",
        ) from exc

    claims = token.get("userinfo") or {}
    if not claims:
        try:
            resp = await client.userinfo(token=token)
            claims = dict(resp)
        except Exception:
            claims = {}

    user = oidc_service.upsert_user_from_claims(
        db, settings=settings, provider=provider, claims=claims
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="OIDC login rejected (user creation disabled or missing subject)",
        )

    _session, raw = auth_service.create_session(
        db,
        user=user,
        settings=settings,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
    db.commit()

    next_url = request.session.pop("oidc_next", "/") or "/"
    if not next_url.startswith("/"):
        next_url = "/"
    response = RedirectResponse(url=next_url, status_code=status.HTTP_303_SEE_OTHER)
    _set_session_cookie(response, raw, settings)
    return response



