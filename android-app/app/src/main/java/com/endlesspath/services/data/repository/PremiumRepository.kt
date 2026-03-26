package com.endlesspath.services.data.repository

import com.endlesspath.services.data.api.ApiService
import com.endlesspath.services.data.api.model.PremiumActivationRequest
import com.endlesspath.services.data.api.model.toDomain
import com.endlesspath.services.domain.models.PremiumActivationResult
import com.endlesspath.services.utils.AppException
import com.endlesspath.services.utils.TokenStorage

class PremiumRepository(
    private val apiService: ApiService,
    tokenStorage: TokenStorage
) : BaseRepository(tokenStorage) {

    suspend fun activatePremium(code: String): PremiumActivationResult {
        return try {
            safeApiCall {
                apiService.activatePremium(
                    PremiumActivationRequest(code = code.trim())
                )
            }.toDomain()
        } catch (_: AppException.NotFound) {
            throw AppException.NotFound(
                "Premium activation is not available on the current backend yet."
            )
        }
    }
}
