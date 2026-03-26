package com.endlesspath.services.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.endlesspath.services.ui.components.InfoCard

@Composable
fun AppPlaceholderScreen(contentPadding: PaddingValues) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(contentPadding)
            .padding(horizontal = 20.dp, vertical = 24.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        Text(
            text = "EndlessPath Services",
            style = MaterialTheme.typography.headlineMedium
        )
        Text(
            text = "Step 1 sets up the Android app shell and clean architecture packages.",
            style = MaterialTheme.typography.bodyLarge
        )
        InfoCard(
            modifier = Modifier.fillMaxWidth(),
            title = "Architecture Ready",
            description = "Packages created: ui/screens, ui/components, data/api, data/repository, domain/models, viewmodel, utils."
        )
    }
}

