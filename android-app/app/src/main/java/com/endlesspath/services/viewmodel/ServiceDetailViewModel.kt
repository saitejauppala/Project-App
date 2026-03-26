package com.endlesspath.services.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.endlesspath.services.data.repository.BookingRepository
import com.endlesspath.services.data.repository.ServiceRepository
import com.endlesspath.services.domain.models.Service
import com.endlesspath.services.utils.AppException
import com.endlesspath.services.utils.DateTimeUtils
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class ServiceDetailUiState(
    val isLoading: Boolean = true,
    val service: Service? = null,
    val address: String = "",
    val notes: String = "",
    val bookingDate: String = DateTimeUtils.defaultBookingDate(),
    val bookingTime: String = DateTimeUtils.defaultBookingTime(),
    val isBooking: Boolean = false,
    val errorMessage: String? = null,
    val successMessage: String? = null,
    val bookingCompleted: Boolean = false
)

class ServiceDetailViewModel(
    private val serviceRepository: ServiceRepository,
    private val bookingRepository: BookingRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow(ServiceDetailUiState())
    val uiState: StateFlow<ServiceDetailUiState> = _uiState.asStateFlow()

    private var loadedServiceId: String? = null

    fun loadService(serviceId: String) {
        if (loadedServiceId == serviceId && uiState.value.service != null) {
            return
        }

        loadedServiceId = serviceId
        viewModelScope.launch {
            _uiState.update { state ->
                state.copy(isLoading = true, errorMessage = null, successMessage = null)
            }
            try {
                val service = serviceRepository.getServiceById(serviceId)
                _uiState.update { state ->
                    state.copy(isLoading = false, service = service)
                }
            } catch (exception: AppException) {
                _uiState.update { state ->
                    state.copy(isLoading = false, errorMessage = exception.message)
                }
            }
        }
    }

    fun onAddressChanged(value: String) {
        _uiState.update { state -> state.copy(address = value, errorMessage = null) }
    }

    fun onNotesChanged(value: String) {
        _uiState.update { state -> state.copy(notes = value, errorMessage = null) }
    }

    fun onBookingDateChanged(value: String) {
        _uiState.update { state -> state.copy(bookingDate = value, errorMessage = null) }
    }

    fun onBookingTimeChanged(value: String) {
        _uiState.update { state -> state.copy(bookingTime = value, errorMessage = null) }
    }

    fun bookService() {
        val currentState = uiState.value
        val service = currentState.service ?: return

        if (currentState.address.trim().length < 10) {
            _uiState.update { state ->
                state.copy(errorMessage = "Enter the complete service address.")
            }
            return
        }

        viewModelScope.launch {
            _uiState.update { state ->
                state.copy(isBooking = true, errorMessage = null, successMessage = null)
            }
            try {
                val scheduledTime = DateTimeUtils.toApiDateTime(
                    currentState.bookingDate,
                    currentState.bookingTime
                )
                bookingRepository.createBooking(
                    serviceId = service.id,
                    scheduledTime = scheduledTime,
                    address = currentState.address.trim(),
                    notes = currentState.notes.trim()
                )
                _uiState.update { state ->
                    state.copy(
                        isBooking = false,
                        successMessage = "Booking created successfully.",
                        bookingCompleted = true
                    )
                }
            } catch (exception: AppException) {
                _uiState.update { state ->
                    state.copy(
                        isBooking = false,
                        errorMessage = exception.message
                    )
                }
            }
        }
    }

    fun onBookingHandled() {
        _uiState.update { state ->
            state.copy(
                bookingCompleted = false,
                successMessage = null
            )
        }
    }

    fun clearError() {
        _uiState.update { state -> state.copy(errorMessage = null) }
    }
}

