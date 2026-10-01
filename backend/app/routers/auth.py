"""Authentication: first-run setup, login, logout, and current-owner lookup."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response, status

from ..deps import AccountsDep, OwnerDep, RateLimiterDep, SettingsDep, client_ip
from ..schemas import AuthStatus, AuthUser, LoginRequest, SetupRequest
from ..security import create_token
from ..services.accounts import OwnerExists

router = APIRouter(prefix="/api/auth", tags=["auth"])

GENERIC_ERROR = "Invalid username or password"


def _set_session_cookie(response: Response, token: str, settings) -> None:
    response.set_cookie(
        key=settings.cookie_name,
        value=token,
        max_age=settings.session_max_age,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


def _check_rate_limit(limiter, ip: str) -> None:
    if limiter.is_limited(ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed attempts. Try again later.",
        )


@router.get("/status", response_model=AuthStatus)
async def status_(accounts: AccountsDep):
    """Public: tells the client whether to show setup or the login form."""
    return AuthStatus(setup_required=not await accounts.exists())


@router.post("/setup", response_model=AuthUser, status_code=status.HTTP_201_CREATED)
async def setup(
    payload: SetupRequest,
    request: Request,
    response: Response,
    settings: SettingsDep,
    accounts: AccountsDep,
    limiter: RateLimiterDep,
):
    """Create the single owner account (allowed only once) and sign in."""
    ip = client_ip(request)
    _check_rate_limit(limiter, ip)

    try:
        owner = await accounts.create_owner(payload.username, payload.password)
    except OwnerExists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Setup has already been completed",
        )

    limiter.reset(ip)
    secret = await accounts.session_secret(settings.secret_key)
    token = create_token(owner["username"], secret)
    _set_session_cookie(response, token, settings)
    return AuthUser(username=owner["username"])


@router.post("/login", response_model=AuthUser)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    settings: SettingsDep,
    accounts: AccountsDep,
    limiter: RateLimiterDep,
):
    ip = client_ip(request)
    _check_rate_limit(limiter, ip)

    if not await accounts.verify(payload.username, payload.password):
        limiter.record_failure(ip)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=GENERIC_ERROR)

    limiter.reset(ip)
    secret = await accounts.session_secret(settings.secret_key)
    token = create_token(payload.username, secret)
    _set_session_cookie(response, token, settings)
    return AuthUser(username=payload.username)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response, settings: SettingsDep, owner: OwnerDep):
    response.delete_cookie(key=settings.cookie_name, path="/")
    return None


@router.get("/me", response_model=AuthUser)
async def me(owner: OwnerDep):
    return AuthUser(username=owner)
