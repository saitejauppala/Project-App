package com.endlesspath.services.ui.navigation

sealed class AppDestination(val route: String) {
    data object Login : AppDestination("login")
    data object Register : AppDestination("register")
    data object Home : AppDestination("home")
    data object Premium : AppDestination("premium")
    data object MyBookings : AppDestination("my_bookings")
    data object ServiceDetail : AppDestination("service_detail/{serviceId}") {
        fun createRoute(serviceId: String): String = "service_detail/$serviceId"
    }
}
