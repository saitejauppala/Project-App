from pydantic import BaseModel, Field


class ForgotPasswordRequest(BaseModel):
    """Request schema for forgot password."""
    email_or_phone: str = Field(..., min_length=3, max_length=255)


class ForgotPasswordResponse(BaseModel):
    """Response schema for forgot password."""
    message: str = "If an account exists, a reset link has been sent."
    # Token included for development/testing - remove in production
    token: str | None = None


class ResetPasswordRequest(BaseModel):
    """Request schema for reset password."""
    token: str = Field(..., min_length=10)
    new_password: str = Field(..., min_length=8, max_length=72)


class ResetPasswordResponse(BaseModel):
    """Response schema for reset password."""
    message: str = "Password reset successful."


class ValidateTokenRequest(BaseModel):
    """Request schema for validating reset token."""
    token: str = Field(..., min_length=10)


class ValidateTokenResponse(BaseModel):
    """Response schema for token validation."""
    valid: bool
    message: str