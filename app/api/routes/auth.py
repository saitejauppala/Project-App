from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user
from app.core.redis import rate_limiter
from app.schemas.user import (
    UserRegister, UserLogin, Token, UserResponse, UserWithProfile,
    ProviderRegister, ProviderLoginResponse,
)
from app.schemas.password_reset import (
    ForgotPasswordRequest, ForgotPasswordResponse,
    ResetPasswordRequest, ResetPasswordResponse,
)
from app.services.user_service import UserService
from app.services.password_reset_service import PasswordResetService
from app.utils.security import create_token_pair, decode_token, get_password_hash
from app.models.user import UserRole

router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegister,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user (customer or provider)."""
    user_service = UserService(db)
    
    try:
        user = await user_service.create_user(user_data)
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/login", response_model=Token)
async def login(
    request: Request,
    login_data: UserLogin,
    db: AsyncSession = Depends(get_db),
):
    """Login with phone and password (rate limited: 5 attempts per minute)."""
    # Rate limiting by IP
    client_ip = request.client.host if request.client else "unknown"
    rate_key = f"login_attempts:{client_ip}"
    
    allowed, current, _ = await rate_limiter.is_allowed(rate_key, limit=5, window=60)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later.",
        )
    
    user_service = UserService(db)
    
    user = await user_service.authenticate(login_data.phone, login_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid phone number or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token, refresh_token = create_token_pair(
        str(user.id), user.role.value
    )
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    credentials: str = Depends(security),
):
    """Refresh access token using refresh token."""
    token = credentials.credentials
    payload = decode_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Validate token type
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type - refresh token required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    role = payload.get("role")
    
    if not user_id or not role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create new token pair
    access_token, refresh_token = create_token_pair(user_id, role)
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.get("/me", response_model=UserWithProfile)
async def get_current_user_info(
    current_user = Depends(get_current_user),
):
    """Get current authenticated user information."""
    return current_user


@router.post("/logout")
async def logout(
    current_user = Depends(get_current_user),
):
    """Logout and blacklist token."""
    from app.core.redis import token_blacklist
    from app.utils.security import decode_token
    from fastapi import Request
    from fastapi.security import HTTPAuthorizationCredentials
    
    # Note: In a real implementation, you'd extract the jti from the token
    # and add it to the blacklist with TTL matching token expiry
    # For now, we just acknowledge the logout
    
    return {"message": "Successfully logged out"}


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password(
    request_data: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Request password reset.
    
    Returns generic success message regardless of whether user exists
    to prevent user enumeration attacks.
    """
    reset_service = PasswordResetService(db)
    
    # Request reset - returns token if user found, None otherwise
    token = await reset_service.request_password_reset(request_data.email_or_phone)
    
    # Return generic message to prevent user enumeration
    # Token included for development/testing - remove in production
    return ForgotPasswordResponse(
        message="If an account exists, a reset link has been sent.",
        token=token,  # TODO: Remove in production - send via email/SMS instead
    )


@router.post("/reset-password", response_model=ResetPasswordResponse)
async def reset_password(
    reset_data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Reset password using token.
    
    Validates token, updates password, and marks token as used.
    """
    reset_service = PasswordResetService(db)
    user_service = UserService(db)
    
    # Validate token
    reset_token = await reset_service.validate_token(reset_data.token)
    
    if not reset_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )
    
    # Get user
    user = await user_service.get_user_by_id(reset_token.user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )
    
    # Update password
    user.password_hash = get_password_hash(reset_data.new_password)
    await db.commit()
    
    # Mark token as used
    await reset_service.mark_token_used(reset_token)
    
    return ResetPasswordResponse(message="Password reset successful.")


# ─────────────────────────────────────────────
# Provider-specific auth endpoints
# ─────────────────────────────────────────────

@router.post(
    "/provider/register",
    response_model=UserWithProfile,
    status_code=status.HTTP_201_CREATED,
    summary="Register as a provider",
)
async def provider_register(
    provider_data: ProviderRegister,
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new provider account.
    Role is automatically set to PROVIDER.
    A provider profile is created with the optional bio.
    """
    user_service = UserService(db)

    # Build a UserRegister with role forced to PROVIDER
    user_reg = UserRegister(
        name=provider_data.name,
        phone=provider_data.phone,
        password=provider_data.password,
        role=UserRole.PROVIDER,
    )

    try:
        user = await user_service.create_user(user_reg)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    # Set bio on the auto-created provider profile if provided
    if provider_data.bio and user.provider_profile:
        user.provider_profile.bio = provider_data.bio
        await db.commit()
        await db.refresh(user)

    return user


@router.post(
    "/provider/login",
    response_model=ProviderLoginResponse,
    summary="Provider login",
)
async def provider_login(
    request: Request,
    login_data: UserLogin,
    db: AsyncSession = Depends(get_db),
):
    """
    Provider login with phone and password.
    Returns JWT tokens plus provider profile details
    (verification status, availability, rating).
    """
    # Rate limiting by IP
    client_ip = request.client.host if request.client else "unknown"
    rate_key = f"provider_login_attempts:{client_ip}"

    allowed, _, _ = await rate_limiter.is_allowed(rate_key, limit=5, window=60)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later.",
        )

    user_service = UserService(db)
    user = await user_service.authenticate(login_data.phone, login_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid phone number or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.role != UserRole.PROVIDER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This login is for providers only. Please use the customer login.",
        )

    profile = user.provider_profile
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Provider profile not found. Please contact support.",
        )

    access_token, refresh_token = create_token_pair(str(user.id), user.role.value)

    return ProviderLoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        provider_id=str(user.id),
        name=user.name,
        phone=user.phone,
        is_verified=profile.is_verified,
        is_available=profile.is_available,
        rating=profile.rating,
        total_reviews=profile.total_reviews,
    )