package com.endlesspath.services.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.endlesspath.services.data.repository.AuthRepository
import com.endlesspath.services.utils.AppException
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class LoginUiState(
    val phone: String = "",
    val password: String = "",
    val isLoading: Boolean = false,
    val errorMessage: String? = null,
    val isLoginSuccessful: Boolean = false
)

class LoginViewModel(
    private val authRepository: AuthRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow(LoginUiState())
    val uiState: StateFlow<LoginUiState> = _uiState.asStateFlow()

    fun onPhoneChanged(value: String) {
        _uiState.update { state ->
            state.copy(phone = value, errorMessage = null)
        }
    }

    fun onPasswordChanged(value: String) {
        _uiState.update { state ->
            state.copy(password = value, errorMessage = null)
        }
    }

    fun login() {
        val phone = uiState.value.phone.trim()
        val password = uiState.value.password

        if (phone.isBlank() || password.isBlank()) {
            _uiState.update { state ->
                state.copy(errorMessage = "Phone and password are required.")
            }
            return
        }

        viewModelScope.launch {
            _uiState.update { state -> state.copy(isLoading = true, errorMessage = null) }
            try {
                authRepository.loginUser(phone = phone, password = password)
                _uiState.update { state ->
                    state.copy(
                        isLoading = false,
                        isLoginSuccessful = true
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

    fun onLoginHandled() {
        _uiState.update { state ->
            state.copy(isLoginSuccessful = false)
        }
    }

    fun clearError() {
        _uiState.update { state -> state.copy(errorMessage = null) }
    }
}

