package com.endlesspath.services.utils

import java.text.NumberFormat
import java.text.ParseException
import java.text.SimpleDateFormat
import java.util.Calendar
import java.util.Locale
import java.util.TimeZone

object DateTimeUtils {

    private val dateInputFormat = SimpleDateFormat("yyyy-MM-dd", Locale.getDefault())
    private val timeInputFormat = SimpleDateFormat("HH:mm", Locale.getDefault())
    private val apiFormat = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", Locale.US)
    private val outputFormat = SimpleDateFormat("dd MMM yyyy, hh:mm a", Locale.getDefault())
    private val serverFormats = listOf(
        SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSSSSS", Locale.US),
        SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSS", Locale.US),
        SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", Locale.US),
        SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ssX", Locale.US),
        SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSSX", Locale.US)
    )

    fun defaultBookingDate(): String {
        val calendar = Calendar.getInstance().apply {
            add(Calendar.DAY_OF_YEAR, 1)
        }
        return dateInputFormat.format(calendar.time)
    }

    fun defaultBookingTime(): String {
        val calendar = Calendar.getInstance().apply {
            add(Calendar.HOUR_OF_DAY, 2)
            set(Calendar.MINUTE, 0)
            set(Calendar.SECOND, 0)
            set(Calendar.MILLISECOND, 0)
        }
        return timeInputFormat.format(calendar.time)
    }

    fun toApiDateTime(date: String, time: String): String {
        return try {
            val parsedDate = dateInputFormat.parse(date.trim()) ?: error("Invalid date")
            val parsedTime = timeInputFormat.parse(time.trim()) ?: error("Invalid time")

            val dateCalendar = Calendar.getInstance().apply { this.time = parsedDate }
            val timeCalendar = Calendar.getInstance().apply { this.time = parsedTime }

            Calendar.getInstance().apply {
                set(Calendar.YEAR, dateCalendar.get(Calendar.YEAR))
                set(Calendar.MONTH, dateCalendar.get(Calendar.MONTH))
                set(Calendar.DAY_OF_MONTH, dateCalendar.get(Calendar.DAY_OF_MONTH))
                set(Calendar.HOUR_OF_DAY, timeCalendar.get(Calendar.HOUR_OF_DAY))
                set(Calendar.MINUTE, timeCalendar.get(Calendar.MINUTE))
                set(Calendar.SECOND, 0)
                set(Calendar.MILLISECOND, 0)
            }.let { calendar ->
                apiFormat.format(calendar.time)
            }
        } catch (_: Exception) {
            throw AppException.Validation("Enter a valid date and time.")
        }
    }

    fun formatServerDateTime(value: String?): String {
        if (value.isNullOrBlank()) {
            return "Not scheduled"
        }

        for (format in serverFormats) {
            try {
                if (format.toPattern().contains("X")) {
                    format.timeZone = TimeZone.getTimeZone("UTC")
                }
                val parsedDate = format.parse(value)
                if (parsedDate != null) {
                    return outputFormat.format(parsedDate)
                }
            } catch (_: ParseException) {
                continue
            }
        }

        return value
    }

    fun formatPrice(amount: Double): String {
        val currencyFormatter = NumberFormat.getCurrencyInstance(Locale("en", "IN"))
        return currencyFormatter.format(amount)
    }
}

