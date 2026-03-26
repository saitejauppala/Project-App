package com.endlesspath.services.ui.components

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.AssistChip
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.endlesspath.services.domain.models.Booking
import com.endlesspath.services.domain.models.BookingStatus
import com.endlesspath.services.utils.DateTimeUtils

@Composable
fun BookingCard(
    booking: Booking,
    modifier: Modifier = Modifier
) {
    Card(modifier = modifier.fillMaxWidth()) {
        Column(
            modifier = Modifier.padding(18.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Text(
                    text = booking.service.name,
                    style = MaterialTheme.typography.titleMedium,
                    modifier = Modifier.weight(1f)
                )
                AssistChip(
                    onClick = { },
                    label = { Text(text = booking.status.rawValue.replace('_', ' ')) }
                )
            }

            Text(
                text = DateTimeUtils.formatServerDateTime(booking.scheduledTime),
                style = MaterialTheme.typography.bodyMedium,
                color = statusColor(booking.status)
            )

            Text(
                text = booking.address,
                style = MaterialTheme.typography.bodyMedium
            )

            booking.providerName?.let { providerName ->
                Text(
                    text = "Provider: $providerName",
                    style = MaterialTheme.typography.bodyMedium
                )
            }

            booking.cancellationReason?.let { reason ->
                Text(
                    text = "Reason: $reason",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.error
                )
            }

            Text(
                text = DateTimeUtils.formatPrice(booking.price),
                style = MaterialTheme.typography.titleSmall
            )
        }
    }
}

private fun statusColor(status: BookingStatus): Color {
    return when (status) {
        BookingStatus.PENDING -> Color(0xFFD97706)
        BookingStatus.ASSIGNED -> Color(0xFF2563EB)
        BookingStatus.IN_PROGRESS -> Color(0xFF7C3AED)
        BookingStatus.COMPLETED -> Color(0xFF15803D)
        BookingStatus.CANCELLED -> Color(0xFFB91C1C)
    }
}
