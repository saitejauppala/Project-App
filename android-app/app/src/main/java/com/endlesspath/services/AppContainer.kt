package com.endlesspath.services

import android.content.Context
import com.endlesspath.services.data.api.RetrofitInstance
import com.endlesspath.services.data.repository.AuthRepository
import com.endlesspath.services.data.repository.BookingRepository
import com.endlesspath.services.data.repository.PremiumRepository
import com.endlesspath.services.data.repository.ServiceRepository
import com.endlesspath.services.utils.TokenStorage

class AppContainer(context: Context) {

    private val appContext = context.applicationContext

    val tokenStorage: TokenStorage by lazy {
        TokenStorage(appContext)
    }

    private val apiService by lazy {
        RetrofitInstance.create(tokenStorage)
    }

    val authRepository: AuthRepository by lazy {
        AuthRepository(apiService, tokenStorage)
    }

    val serviceRepository: ServiceRepository by lazy {
        ServiceRepository(apiService, tokenStorage)
    }

    val bookingRepository: BookingRepository by lazy {
        BookingRepository(apiService, tokenStorage)
    }

    val premiumRepository: PremiumRepository by lazy {
        PremiumRepository(apiService, tokenStorage)
    }
}

