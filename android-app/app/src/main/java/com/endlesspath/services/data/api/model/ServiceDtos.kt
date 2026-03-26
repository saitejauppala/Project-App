package com.endlesspath.services.data.api.model

import com.endlesspath.services.domain.models.Service
import com.endlesspath.services.domain.models.ServiceCategory
import com.google.gson.annotations.SerializedName

data class ServiceCategoryDto(
    val id: String,
    val name: String,
    val description: String? = null,
    val icon: String? = null,
    @SerializedName("is_active") val isActive: Boolean,
    @SerializedName("created_at") val createdAt: String
)

data class ServiceDto(
    val id: String,
    @SerializedName("category_id") val categoryId: String,
    val name: String,
    val description: String? = null,
    @SerializedName("base_price") val basePrice: Double,
    @SerializedName("duration_minutes") val durationMinutes: Int,
    @SerializedName("is_active") val isActive: Boolean,
    @SerializedName("created_at") val createdAt: String,
    @SerializedName("updated_at") val updatedAt: String,
    val category: ServiceCategoryDto,
    @SerializedName("is_premium") val isPremium: Boolean? = null
)

data class ServiceListResponseDto(
    val items: List<ServiceDto> = emptyList(),
    val total: Int = 0,
    val page: Int = 1,
    val limit: Int = 20,
    val pages: Int = 1
)

fun ServiceCategoryDto.toDomain(): ServiceCategory {
    return ServiceCategory(
        id = id,
        name = name,
        description = description,
        icon = icon,
        isActive = isActive,
        createdAt = createdAt
    )
}

fun ServiceDto.toDomain(): Service {
    return Service(
        id = id,
        categoryId = categoryId,
        name = name,
        description = description,
        basePrice = basePrice,
        durationMinutes = durationMinutes,
        isActive = isActive,
        createdAt = createdAt,
        updatedAt = updatedAt,
        category = category.toDomain(),
        isPremium = isPremium ?: false
    )
}

