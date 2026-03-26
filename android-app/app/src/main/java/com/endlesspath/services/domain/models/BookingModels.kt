package com.endlesspath.services.domain.models

enum class BookingStatus(val rawValue: String) {
    PENDING("pending"),
    ASSIGNED("assigned"),
    IN_PROGRESS("in_progress"),
    COMPLETED("completed"),
    CANCELLED("cancelled");

    companion object {
        fun fromValue(value: String): BookingStatus {
            return entries.firstOrNull { it.rawValue == value } ?: PENDING
        }
    }
}

data class Booking(
    val id: String,
    val userId: String,
    val serviceId: String,
    val providerId: String?,
    val status: BookingStatus,
    val scheduledTime: String,
    val address: String,
    val notes: String?,
    val price: Double,
    val assignedAt: String?,
    val startedAt: String?,
    val completedAt: String?,
    val cancelledAt: String?,
    val cancellationReason: String?,
    val createdAt: String,
    val updatedAt: String,
    val service: Service,
    val customerName: String,
    val providerName: String?
)
