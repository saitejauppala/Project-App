package com.endlesspath.services.ui

import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavType
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.endlesspath.services.ui.navigation.AppDestination
import com.endlesspath.services.ui.screens.HomeScreen
import com.endlesspath.services.ui.screens.LoginScreen
import com.endlesspath.services.ui.screens.MyBookingsScreen
import com.endlesspath.services.ui.screens.PremiumActivationScreen
import com.endlesspath.services.ui.screens.RegisterScreen
import com.endlesspath.services.ui.screens.ServiceDetailScreen
import com.endlesspath.services.ui.screens.SessionLoadingScreen
import com.endlesspath.services.utils.endlessPathViewModelFactory
import com.endlesspath.services.viewmodel.AppViewModel

@Composable
fun EndlessPathApp() {
    val navController = rememberNavController()
    val appViewModel: AppViewModel = viewModel(factory = endlessPathViewModelFactory())
    val appUiState by appViewModel.uiState.collectAsStateWithLifecycle()

    if (appUiState.isSessionLoading) {
        SessionLoadingScreen()
        return
    }

    val startDestination = if (appUiState.isAuthenticated) {
        AppDestination.Home.route
    } else {
        AppDestination.Login.route
    }

    LaunchedEffect(appUiState.isAuthenticated) {
        val targetRoute = if (appUiState.isAuthenticated) {
            AppDestination.Home.route
        } else {
            AppDestination.Login.route
        }

        val currentRoute = navController.currentBackStackEntry?.destination?.route
        if (currentRoute != null && currentRoute != targetRoute) {
            navController.navigate(targetRoute) {
                popUpTo(navController.graph.findStartDestination().id) {
                    inclusive = true
                }
                launchSingleTop = true
            }
        }
    }

    NavHost(
        navController = navController,
        startDestination = startDestination
    ) {
        composable(AppDestination.Login.route) {
            LoginScreen(
                onNavigateToRegister = {
                    navController.navigate(AppDestination.Register.route)
                },
                onLoginSuccess = {
                    navController.navigate(AppDestination.Home.route) {
                        popUpTo(AppDestination.Login.route) {
                            inclusive = true
                        }
                        launchSingleTop = true
                    }
                }
            )
        }

        composable(AppDestination.Register.route) {
            RegisterScreen(
                onNavigateBackToLogin = {
                    navController.popBackStack()
                }
            )
        }

        composable(AppDestination.Home.route) {
            HomeScreen(
                onServiceClick = { serviceId ->
                    navController.navigate(AppDestination.ServiceDetail.createRoute(serviceId))
                },
                onMyBookingsClick = {
                    navController.navigate(AppDestination.MyBookings.route)
                },
                onPremiumClick = {
                    navController.navigate(AppDestination.Premium.route)
                },
                onLogoutClick = appViewModel::logout
            )
        }

        composable(
            route = AppDestination.ServiceDetail.route,
            arguments = listOf(
                navArgument("serviceId") {
                    type = NavType.StringType
                }
            )
        ) { backStackEntry ->
            ServiceDetailScreen(
                serviceId = backStackEntry.arguments?.getString("serviceId").orEmpty(),
                onBackClick = { navController.popBackStack() },
                onBookingSuccess = {
                    navController.navigate(AppDestination.MyBookings.route) {
                        launchSingleTop = true
                    }
                }
            )
        }

        composable(AppDestination.Premium.route) {
            PremiumActivationScreen(
                onBackClick = { navController.popBackStack() }
            )
        }

        composable(AppDestination.MyBookings.route) {
            MyBookingsScreen(
                onBackClick = { navController.popBackStack() }
            )
        }
    }
}
