package com.endlesspath.services.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.endlesspath.services.data.repository.AuthRepository
import com.endlesspath.services.utils.TokenStorage
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

data class AppUiState(
    val isSessionLoading: Boolean = true,
    val isAuthenticated: Boolean = false
)

class AppViewModel(
    private val authRepository: AuthRepository,
    tokenStorage: TokenStorage
) : ViewModel() {

    val uiState: StateFlow<AppUiState> = tokenStorage.isLoggedInFlow
        .map { isLoggedIn ->
            AppUiState(
                isSessionLoading = false,
                isAuthenticated = isLoggedIn
            )
        }
        .stateIn(
            scope = viewModelScope,
            started = SharingStarted.WhileSubscribed(5_000),
            initialValue = AppUiState()
        )

    fun logout() {
        viewModelScope.launch {
            authRepository.logout()
        }
    }
}

