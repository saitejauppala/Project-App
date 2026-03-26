package com.endlesspath.services.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.endlesspath.services.data.repository.AuthRepository
import com.endlesspath.services.data.repository.ServiceRepository
import com.endlesspath.services.domain.models.Service
import com.endlesspath.services.utils.AppException
import kotlinx.coroutines.async
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class HomeUiState(
    val isLoading: Boolean = true,
    val services: List<Service> = emptyList(),
    val currentUserName: String = "",
    val errorMessage: String? = null
)

class HomeViewModel(
    private val serviceRepository: ServiceRepository,
    private val authRepository: AuthRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow(HomeUiState())
    val uiState: StateFlow<HomeUiState> = _uiState.asStateFlow()

    init {
        refresh()
    }

    fun refresh() {
        viewModelScope.launch {
            _uiState.update { state -> state.copy(isLoading = true, errorMessage = null) }
            try {
                val servicesDeferred = async { serviceRepository.getServices() }
                val userDeferred = async { authRepository.getCurrentUser() }
                val services = servicesDeferred.await()
                val currentUser = userDeferred.await()

                _uiState.update { state ->
                    state.copy(
                        isLoading = false,
                        services = services,
                        currentUserName = currentUser.name
                    )
                }
            } catch (exception: AppException) {
                _uiState.update { state ->
                    state.copy(
                        isLoading = false,
                        errorMessage = exception.message
                    )
                }
            }
        }
    }

    fun clearError() {
        _uiState.update { state -> state.copy(errorMessage = null) }
    }
}
