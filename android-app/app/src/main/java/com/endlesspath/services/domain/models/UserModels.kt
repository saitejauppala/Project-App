package com.endlesspath.services.domain.models

data class User(
    val id: String,
    val name: String,
    val phone: String,
    val role: String,
    val isActive: Boolean,
    val createdAt: String,
    val providerProfile: ProviderProfile? = null
)

data class ProviderProfile(
    val id: String,
    val userId: String,
    val rating: Double,
    val totalReviews: Int,
    val isAvailable: Boolean,
    val isVerified: Boolean,
    val bio: String?,
    val skills: List<String>
)

