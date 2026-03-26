package com.endlesspath.services.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.AssistChip
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CenterAlignedTopAppBar
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.endlesspath.services.ui.components.AppTextField
import com.endlesspath.services.ui.components.EmptyStateCard
import com.endlesspath.services.ui.components.LoadingContent
import com.endlesspath.services.utils.DateTimeUtils
import com.endlesspath.services.utils.endlessPathViewModelFactory
import com.endlesspath.services.viewmodel.ServiceDetailViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ServiceDetailScreen(
    serviceId: String,
    onBackClick: () -> Unit,
    onBookingSuccess: () -> Unit
) {
    val viewModel: ServiceDetailViewModel = viewModel(factory = endlessPathViewModelFactory())
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    val snackbarHostState = remember { SnackbarHostState() }

    LaunchedEffect(serviceId) {
        viewModel.loadService(serviceId)
    }

    LaunchedEffect(uiState.errorMessage) {
        uiState.errorMessage?.let { message ->
            snackbarHostState.showSnackbar(message)
            viewModel.clearError()
        }
    }

    LaunchedEffect(uiState.bookingCompleted) {
        if (uiState.bookingCompleted) {
            snackbarHostState.showSnackbar(
                uiState.successMessage ?: "Booking created successfully."
            )
            viewModel.onBookingHandled()
            onBookingSuccess()
        }
    }

    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
        snackbarHost = { SnackbarHost(hostState = snackbarHostState) },
        topBar = {
            CenterAlignedTopAppBar(
                title = { Text(text = "Service Details") },
                navigationIcon = {
                    IconButton(onClick = onBackClick) {
                        Icon(
                            imageVector = Icons.AutoMirrored.Filled.ArrowBack,
                            contentDescription = "Back"
                        )
                    }
                }
            )
        }
    ) { innerPadding ->
        when {
            uiState.isLoading -> {
                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(innerPadding)
                ) {
                    LoadingContent(message = "Loading service details...")
                }
            }

            uiState.service == null -> {
                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(innerPadding)
                        .padding(24.dp)
                ) {
                    EmptyStateCard(
                        title = "Service unavailable",
                        description = "This service could not be loaded from the backend."
                    )
                }
            }

            else -> {
                val service = uiState.service
                Column(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(innerPadding)
                        .verticalScroll(rememberScrollState())
                        .padding(horizontal = 20.dp, vertical = 20.dp),
                    verticalArrangement = Arrangement.spacedBy(18.dp)
                ) {
                    Card(modifier = Modifier.fillMaxWidth()) {
                        Column(
                            modifier = Modifier.padding(18.dp),
                            verticalArrangement = Arrangement.spacedBy(10.dp)
                        ) {
                            Text(
                                text = service?.name.orEmpty(),
                                style = MaterialTheme.typography.headlineSmall
                            )
                            Text(
                                text = service?.category?.name.orEmpty(),
                                style = MaterialTheme.typography.labelLarge,
                                color = MaterialTheme.colorScheme.secondary
                            )
                            if (service?.isPremium == true) {
                                AssistChip(
                                    onClick = { },
                                    label = { Text(text = "Premium service") }
                                )
                            }
                            Text(
                                text = service?.description ?: "Reliable service by trained professionals.",
                                style = MaterialTheme.typography.bodyMedium
                            )
                            Text(
                                text = DateTimeUtils.formatPrice(service?.basePrice ?: 0.0),
                                style = MaterialTheme.typography.titleMedium
                            )
                            Text(
                                text = "${service?.durationMinutes ?: 0} mins estimated",
                                style = MaterialTheme.typography.bodyMedium
                            )
                        }
                    }

                    Text(
                        text = "Book this service",
                        style = MaterialTheme.typography.titleLarge
                    )

                    AppTextField(
                        value = uiState.address,
                        onValueChange = viewModel::onAddressChanged,
                        label = "Service address",
                        singleLine = false,
                        maxLines = 3,
                        supportingText = "Minimum 10 characters"
                    )

                    AppTextField(
                        value = uiState.notes,
                        onValueChange = viewModel::onNotesChanged,
                        label = "Notes",
                        singleLine = false,
                        maxLines = 4,
                        supportingText = "Optional instructions for the provider"
                    )

                    AppTextField(
                        value = uiState.bookingDate,
                        onValueChange = viewModel::onBookingDateChanged,
                        label = "Date",
                        supportingText = "Format: YYYY-MM-DD"
                    )

                    AppTextField(
                        value = uiState.bookingTime,
                        onValueChange = viewModel::onBookingTimeChanged,
                        label = "Time",
                        supportingText = "Format: HH:MM"
                    )

                    Button(
                        onClick = viewModel::bookService,
                        enabled = !uiState.isBooking
                    ) {
                        Text(
                            text = if (uiState.isBooking) {
                                "Booking..."
                            } else {
                                "Book Service"
                            }
                        )
                    }
                }
            }
        }
    }
}
