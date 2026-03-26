package com.endlesspath.services.domain.models

data class AuthSession(
    val accessToken: String,
    val refreshToken: String,
    val tokenType: String
)

data class PremiumActivationResult(
    val message: String,
    val success: Boolean
)

