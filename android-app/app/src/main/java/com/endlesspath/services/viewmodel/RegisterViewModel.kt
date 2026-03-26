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

data class RegisterUiState(
    val name: String = "",
    val phone: String = "",
    val password: String = "",
    val confirmPassword: String = "",
    val isLoading: Boolean = false,
    val errorMessage: String? = null,
    val successMessage: String? = null,
    val isRegistrationSuccessful: Boolean = false
)

class RegisterViewModel(
    private val authRepository: AuthRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow(RegisterUiState())
    val uiState: StateFlow<RegisterUiState> = _uiState.asStateFlow()

    fun onNameChanged(value: String) {
        _uiState.update { state -> state.copy(name = value, errorMessage = null) }
    }

    fun onPhoneChanged(value: String) {
        _uiState.update { state -> state.copy(phone = value, errorMessage = null) }
    }

    fun onPasswordChanged(value: String) {
        _uiState.update { state -> state.copy(password = value, errorMessage = null) }
    }

    fun onConfirmPasswordChanged(value: String) {
        _uiState.update { state -> state.copy(confirmPassword = value, errorMessage = null) }
    }

    fun register() {
        val currentState = uiState.value

        when {
            currentState.name.trim().length < 2 -> {
                showError("Enter a valid name.")
                return
            }

            currentState.phone.trim().length < 10 -> {
                showError("Enter a valid phone number.")
                return
            }

            currentState.password.length < 8 -> {
                showError("Password must be at least 8 characters.")
                return
            }

            currentState.password != currentState.confirmPassword -> {
                showError("Passwords do not match.")
                return
            }
        }

        viewModelScope.launch {
            _uiState.update { state -> state.copy(isLoading = true, errorMessage = null) }
            try {
                authRepository.registerUser(
                    name = currentState.name.trim(),
                    phone = currentState.phone.trim(),
                    password = currentState.password
                )
                _uiState.update { state ->
                    state.copy(
                        isLoading = false,
                        successMessage = "Account created successfully. Please log in.",
                        isRegistrationSuccessful = true
                    )
                }
            } catch (exception: AppException) {
                showError(exception.message)
            }
        }
    }

    fun onRegistrationHandled() {
        _uiState.update { state ->
            state.copy(
                isRegistrationSuccessful = false,
                successMessage = null
            )
        }
    }

    fun clearError() {
        _uiState.update { state -> state.copy(errorMessage = null) }
    }

    private fun showError(message: String?) {
        _uiState.update { state ->
            state.copy(
                isLoading = false,
                errorMessage = message ?: "Something went wrong."
            )
        }
    }
}

