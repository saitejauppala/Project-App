package com.endlesspath.services.data.api.model

import com.endlesspath.services.domain.models.Booking
import com.endlesspath.services.domain.models.BookingStatus
import com.google.gson.annotations.SerializedName

data class BookingCreateRequest(
    @SerializedName("service_id") val serviceId: String,
    @SerializedName("scheduled_time") val scheduledTime: String,
    val address: String,
    val notes: String?
)

data class BookingDto(
    val id: String,
    @SerializedName("user_id") val userId: String,
    @SerializedName("service_id") val serviceId: String,
    @SerializedName("provider_id") val providerId: String? = null,
    val status: String,
    @SerializedName("scheduled_time") val scheduledTime: String,
    val address: String,
    val notes: String? = null,
    val price: Double,
    @SerializedName("assigned_at") val assignedAt: String? = null,
    @SerializedName("started_at") val startedAt: String? = null,
    @SerializedName("completed_at") val completedAt: String? = null,
    @SerializedName("cancelled_at") val cancelledAt: String? = null,
    @SerializedName("cancellation_reason") val cancellationReason: String? = null,
    @SerializedName("created_at") val createdAt: String,
    @SerializedName("updated_at") val updatedAt: String,
    val service: ServiceDto,
    val user: UserResponseDto,
    val provider: UserResponseDto? = null
)

data class BookingListResponseDto(
    val items: List<BookingDto> = emptyList(),
    val total: Int = 0,
    val page: Int = 1,
    val limit: Int = 20,
    val pages: Int = 1
)

fun BookingDto.toDomain(): Booking {
    return Booking(
        id = id,
        userId = userId,
        serviceId = serviceId,
        providerId = providerId,
        status = BookingStatus.fromValue(status),
        scheduledTime = scheduledTime,
        address = address,
        notes = notes,
        price = price,
        assignedAt = assignedAt,
        startedAt = startedAt,
        completedAt = completedAt,
        cancelledAt = cancelledAt,
        cancellationReason = cancellationReason,
        createdAt = createdAt,
        updatedAt = updatedAt,
        service = service.toDomain(),
        customerName = user.name,
        providerName = provider?.name
    )
}
