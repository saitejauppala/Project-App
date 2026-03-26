package com.endlesspath.services.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.endlesspath.services.data.repository.PremiumRepository
import com.endlesspath.services.utils.AppException
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class PremiumUiState(
    val code: String = "",
    val isLoading: Boolean = false,
    val errorMessage: String? = null,
    val successMessage: String? = null
)

class PremiumViewModel(
    private val premiumRepository: PremiumRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow(PremiumUiState())
    val uiState: StateFlow<PremiumUiState> = _uiState.asStateFlow()

    fun onCodeChanged(value: String) {
        _uiState.update { state ->
            state.copy(code = value.uppercase(), errorMessage = null, successMessage = null)
        }
    }

    fun activatePremium() {
        val code = uiState.value.code.trim()
        if (code.isBlank()) {
            _uiState.update { state ->
                state.copy(errorMessage = "Enter a premium activation code.")
            }
            return
        }

        viewModelScope.launch {
            _uiState.update { state ->
                state.copy(isLoading = true, errorMessage = null, successMessage = null)
            }
            try {
                val result = premiumRepository.activatePremium(code)
                _uiState.update { state ->
                    state.copy(
                        isLoading = false,
                        successMessage = result.message
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

    fun clearMessages() {
        _uiState.update { state ->
            state.copy(errorMessage = null, successMessage = null)
        }
    }
}

