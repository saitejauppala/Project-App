package com.endlesspath.services.data.repository

import com.endlesspath.services.data.api.ApiService
import com.endlesspath.services.data.api.model.toDomain
import com.endlesspath.services.domain.models.Service
import com.endlesspath.services.utils.TokenStorage

class ServiceRepository(
    private val apiService: ApiService,
    tokenStorage: TokenStorage
) : BaseRepository(tokenStorage) {

    suspend fun getServices(): List<Service> {
        return safeApiCall {
            apiService.getServices()
        }.items.map { it.toDomain() }
    }

    suspend fun getServiceById(serviceId: String): Service {
        return safeApiCall {
            apiService.getService(serviceId)
        }.toDomain()
    }
}

