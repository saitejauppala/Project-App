package com.endlesspath.services.data.repository

import com.endlesspath.services.data.api.model.ApiErrorEnvelope
import com.endlesspath.services.utils.AppException
import com.endlesspath.services.utils.TokenStorage
import com.google.gson.Gson
import com.google.gson.JsonElement
import okhttp3.ResponseBody
import retrofit2.Response
import java.io.IOException

abstract class BaseRepository(
    private val tokenStorage: TokenStorage
) {

    private val gson = Gson()

    protected suspend fun <T> safeApiCall(apiCall: suspend () -> Response<T>): T {
        try {
            val response = apiCall()
            if (response.isSuccessful) {
                return response.body()
                    ?: throw AppException.Unknown("The server returned an empty response.")
            }

            val message = parseErrorMessage(response.errorBody(), response.code())

            when (response.code()) {
                400, 422 -> throw AppException.Validation(message)
                401 -> {
                    tokenStorage.clearTokens()
                    throw AppException.Unauthorized(message)
                }

                404 -> throw AppException.NotFound(message)
                409 -> throw AppException.Conflict(message)
                in 500..599 -> throw AppException.Server(message)
                else -> throw AppException.Http(response.code(), message)
            }
        } catch (exception: IOException) {
            throw AppException.Network(
                message = "Unable to reach the server. Check your internet connection and API base URL.",
                cause = exception
            )
        } catch (exception: AppException) {
            throw exception
        } catch (exception: Exception) {
            throw AppException.Unknown(
                message = exception.message ?: "An unexpected error occurred.",
                cause = exception
            )
        }
    }

    private fun parseErrorMessage(errorBody: ResponseBody?, statusCode: Int): String {
        val rawError = errorBody?.string().orEmpty()
        if (rawError.isBlank()) {
            return defaultMessage(statusCode)
        }

        return try {
            val envelope = gson.fromJson(rawError, ApiErrorEnvelope::class.java)
            envelope.error?.message
                ?: detailMessage(envelope.detail)
                ?: defaultMessage(statusCode)
        } catch (_: Exception) {
            defaultMessage(statusCode)
        }
    }

    private fun detailMessage(detail: JsonElement?): String? {
        if (detail == null || detail.isJsonNull) {
            return null
        }

        return when {
            detail.isJsonPrimitive -> detail.asString
            detail.isJsonArray -> {
                detail.asJsonArray.firstOrNull()?.let { first ->
                    if (first.isJsonObject) {
                        first.asJsonObject.get("msg")?.asString
                    } else {
                        first.toString()
                    }
                }
            }

            detail.isJsonObject -> {
                detail.asJsonObject.get("message")?.asString
                    ?: detail.asJsonObject.get("msg")?.asString
            }

            else -> null
        }
    }

    private fun defaultMessage(statusCode: Int): String {
        return when (statusCode) {
            400 -> "The request could not be processed."
            401 -> "Your session expired. Please log in again."
            404 -> "The requested resource was not found."
            409 -> "A conflicting request already exists."
            422 -> "Some of the submitted values are invalid."
            in 500..599 -> "The server is having trouble. Please try again shortly."
            else -> "Something went wrong. Please try again."
        }
    }
}

