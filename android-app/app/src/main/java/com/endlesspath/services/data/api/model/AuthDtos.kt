package com.endlesspath.services.data.api.model

import com.endlesspath.services.domain.models.AuthSession
import com.endlesspath.services.domain.models.ProviderProfile
import com.endlesspath.services.domain.models.User
import com.google.gson.annotations.SerializedName

data class LoginRequest(
    val phone: String,
    val password: String
)

data class LoginResponse(
    @SerializedName("access_token") val accessToken: String,
    @SerializedName("refresh_token") val refreshToken: String,
    @SerializedName("token_type") val tokenType: String
)

data class RegisterRequest(
    val name: String,
    val phone: String,
    val password: String,
    val role: String = "customer"
)

data class ProviderProfileDto(
    val id: String,
    @SerializedName("user_id") val userId: String,
    val skills: List<String> = emptyList(),
    val bio: String? = null,
    val rating: Double = 0.0,
    @SerializedName("total_reviews") val totalReviews: Int = 0,
    @SerializedName("is_available") val isAvailable: Boolean = false,
    @SerializedName("is_verified") val isVerified: Boolean = false
)

data class UserResponseDto(
    val id: String,
    val name: String,
    val phone: String,
    val role: String,
    @SerializedName("is_active") val isActive: Boolean,
    @SerializedName("created_at") val createdAt: String,
    @SerializedName("provider_profile") val providerProfile: ProviderProfileDto? = null
)

fun LoginResponse.toDomain(): AuthSession {
    return AuthSession(
        accessToken = accessToken,
        refreshToken = refreshToken,
        tokenType = tokenType
    )
}

fun ProviderProfileDto.toDomain(): ProviderProfile {
    return ProviderProfile(
        id = id,
        userId = userId,
        rating = rating,
        totalReviews = totalReviews,
        isAvailable = isAvailable,
        isVerified = isVerified,
        bio = bio,
        skills = skills
    )
}

fun UserResponseDto.toDomain(): User {
    return User(
        id = id,
        name = name,
        phone = phone,
        role = role,
        isActive = isActive,
        createdAt = createdAt,
        providerProfile = providerProfile?.toDomain()
    )
}

