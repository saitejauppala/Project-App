package com.endlesspath.services.data.repository

import com.endlesspath.services.data.api.ApiService
import com.endlesspath.services.data.api.model.LoginRequest
import com.endlesspath.services.data.api.model.RegisterRequest
import com.endlesspath.services.data.api.model.toDomain
import com.endlesspath.services.domain.models.AuthSession
import com.endlesspath.services.domain.models.User
import com.endlesspath.services.utils.TokenStorage
import kotlinx.coroutines.flow.Flow

class AuthRepository(
    private val apiService: ApiService,
    private val tokenStorage: TokenStorage
) : BaseRepository(tokenStorage) {

    val isLoggedInFlow: Flow<Boolean> = tokenStorage.isLoggedInFlow

    suspend fun loginUser(
        phone: String,
        password: String
    ): AuthSession {
        val authResponse = safeApiCall {
            apiService.login(LoginRequest(phone = phone, password = password))
        }

        tokenStorage.saveTokens(
            accessToken = authResponse.accessToken,
            refreshToken = authResponse.refreshToken
        )

        return authResponse.toDomain()
    }

    suspend fun registerUser(
        name: String,
        phone: String,
        password: String
    ): User {
        return safeApiCall {
            apiService.register(
                RegisterRequest(
                    name = name,
                    phone = phone,
                    password = password
                )
            )
        }.toDomain()
    }

    suspend fun getCurrentUser(): User {
        return safeApiCall {
            apiService.getCurrentUser()
        }.toDomain()
    }

    suspend fun logout() {
        runCatching {
            safeApiCall { apiService.logout() }
        }
        tokenStorage.clearTokens()
    }
}

