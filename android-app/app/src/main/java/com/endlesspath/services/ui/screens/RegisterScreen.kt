package com.endlesspath.services.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.endlesspath.services.ui.components.AppTextField
import com.endlesspath.services.ui.components.LoadingContent
import com.endlesspath.services.utils.endlessPathViewModelFactory
import com.endlesspath.services.viewmodel.RegisterViewModel

@Composable
fun RegisterScreen(
    onNavigateBackToLogin: () -> Unit
) {
    val viewModel: RegisterViewModel = viewModel(factory = endlessPathViewModelFactory())
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    val snackbarHostState = remember { SnackbarHostState() }

    LaunchedEffect(uiState.errorMessage) {
        uiState.errorMessage?.let { message ->
            snackbarHostState.showSnackbar(message)
            viewModel.clearError()
        }
    }

    LaunchedEffect(uiState.isRegistrationSuccessful) {
        if (uiState.isRegistrationSuccessful) {
            snackbarHostState.showSnackbar(uiState.successMessage ?: "Registration successful.")
            viewModel.onRegistrationHandled()
            onNavigateBackToLogin()
        }
    }

    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
        snackbarHost = { SnackbarHost(hostState = snackbarHostState) }
    ) { innerPadding ->
        if (uiState.isLoading) {
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(innerPadding)
            ) {
                LoadingContent(message = "Creating your account...")
            }
            return@Scaffold
        }

        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .padding(horizontal = 24.dp, vertical = 32.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            Text(
                text = "Create account",
                style = MaterialTheme.typography.headlineMedium
            )
            Text(
                text = "Register as a customer to start booking services.",
                style = MaterialTheme.typography.bodyLarge
            )

            AppTextField(
                value = uiState.name,
                onValueChange = viewModel::onNameChanged,
                label = "Full name"
            )

            AppTextField(
                value = uiState.phone,
                onValueChange = viewModel::onPhoneChanged,
                label = "Phone",
                keyboardOptions = androidx.compose.foundation.text.KeyboardOptions(
                    keyboardType = KeyboardType.Phone
                )
            )

            AppTextField(
                value = uiState.password,
                onValueChange = viewModel::onPasswordChanged,
                label = "Password",
                keyboardOptions = androidx.compose.foundation.text.KeyboardOptions(
                    keyboardType = KeyboardType.Password
                ),
                visualTransformation = PasswordVisualTransformation()
            )

            AppTextField(
                value = uiState.confirmPassword,
                onValueChange = viewModel::onConfirmPasswordChanged,
                label = "Confirm password",
                keyboardOptions = androidx.compose.foundation.text.KeyboardOptions(
                    keyboardType = KeyboardType.Password
                ),
                visualTransformation = PasswordVisualTransformation()
            )

            Button(onClick = viewModel::register) {
                Text(text = "Register")
            }

            TextButton(onClick = onNavigateBackToLogin) {
                Text(text = "Already have an account? Login")
            }
        }
    }
}
