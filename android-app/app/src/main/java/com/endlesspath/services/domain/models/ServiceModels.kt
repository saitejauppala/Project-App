package com.endlesspath.services.domain.models

data class ServiceCategory(
    val id: String,
    val name: String,
    val description: String?,
    val icon: String?,
    val isActive: Boolean,
    val createdAt: String
)

data class Service(
    val id: String,
    val categoryId: String,
    val name: String,
    val description: String?,
    val basePrice: Double,
    val durationMinutes: Int,
    val isActive: Boolean,
    val createdAt: String,
    val updatedAt: String,
    val category: ServiceCategory,
    val isPremium: Boolean
)

