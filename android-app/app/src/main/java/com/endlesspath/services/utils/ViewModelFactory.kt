package com.endlesspath.services.utils

import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.platform.LocalContext
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import com.endlesspath.services.AppContainer
import com.endlesspath.services.EndlessPathApplication
import com.endlesspath.services.viewmodel.AppViewModel
import com.endlesspath.services.viewmodel.BookingsViewModel
import com.endlesspath.services.viewmodel.HomeViewModel
import com.endlesspath.services.viewmodel.LoginViewModel
import com.endlesspath.services.viewmodel.PremiumViewModel
import com.endlesspath.services.viewmodel.RegisterViewModel
import com.endlesspath.services.viewmodel.ServiceDetailViewModel

class EndlessPathViewModelFactory(
    private val appContainer: AppContainer
) : ViewModelProvider.Factory {

    @Suppress("UNCHECKED_CAST")
    override fun <T : ViewModel> create(modelClass: Class<T>): T {
        return when {
            modelClass.isAssignableFrom(AppViewModel::class.java) -> {
                AppViewModel(appContainer.authRepository, appContainer.tokenStorage) as T
            }

            modelClass.isAssignableFrom(LoginViewModel::class.java) -> {
                LoginViewModel(appContainer.authRepository) as T
            }

            modelClass.isAssignableFrom(RegisterViewModel::class.java) -> {
                RegisterViewModel(appContainer.authRepository) as T
            }

            modelClass.isAssignableFrom(HomeViewModel::class.java) -> {
                HomeViewModel(
                    appContainer.serviceRepository,
                    appContainer.authRepository
                ) as T
            }

            modelClass.isAssignableFrom(ServiceDetailViewModel::class.java) -> {
                ServiceDetailViewModel(
                    appContainer.serviceRepository,
                    appContainer.bookingRepository
                ) as T
            }

            modelClass.isAssignableFrom(PremiumViewModel::class.java) -> {
                PremiumViewModel(appContainer.premiumRepository) as T
            }

            modelClass.isAssignableFrom(BookingsViewModel::class.java) -> {
                BookingsViewModel(appContainer.bookingRepository) as T
            }

            else -> error("Unknown ViewModel class: ${modelClass.name}")
        }
    }
}

@Composable
fun endlessPathViewModelFactory(): ViewModelProvider.Factory {
    val application = LocalContext.current.applicationContext as EndlessPathApplication
    return remember(application) {
        EndlessPathViewModelFactory(application.appContainer)
    }
}
