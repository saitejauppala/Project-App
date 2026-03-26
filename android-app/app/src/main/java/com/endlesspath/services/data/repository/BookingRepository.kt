package com.endlesspath.services.data.repository

import com.endlesspath.services.data.api.ApiService
import com.endlesspath.services.data.api.model.BookingCreateRequest
import com.endlesspath.services.data.api.model.toDomain
import com.endlesspath.services.domain.models.Booking
import com.endlesspath.services.utils.TokenStorage

class BookingRepository(
    private val apiService: ApiService,
    tokenStorage: TokenStorage
) : BaseRepository(tokenStorage) {

    suspend fun createBooking(
        serviceId: String,
        scheduledTime: String,
        address: String,
        notes: String
    ): Booking {
        return safeApiCall {
            apiService.createBooking(
                BookingCreateRequest(
                    serviceId = serviceId,
                    scheduledTime = scheduledTime,
                    address = address,
                    notes = notes.ifBlank { null }
                )
            )
        }.toDomain()
    }

    suspend fun getMyBookings(): List<Booking> {
        return safeApiCall {
            apiService.getMyBookings()
        }.items.map { it.toDomain() }
    }
}

