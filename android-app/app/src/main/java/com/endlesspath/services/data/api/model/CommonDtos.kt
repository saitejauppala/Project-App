package com.endlesspath.services.data.api.model

import com.endlesspath.services.domain.models.PremiumActivationResult
import com.google.gson.JsonElement
import com.google.gson.annotations.SerializedName

data class ApiErrorEnvelope(
    val error: ApiErrorBody? = null,
    val detail: JsonElement? = null
)

data class ApiErrorBody(
    val code: String? = null,
    val message: String? = null,
    val errors: List<ApiFieldError>? = null
)

data class ApiFieldError(
    val field: String? = null,
    val message: String? = null,
    val type: String? = null
)

data class GenericMessageResponse(
    val message: String? = null
)

data class PremiumActivationRequest(
    val code: String
)

data class PremiumActivationResponse(
    val message: String? = null,
    @SerializedName("success") val success: Boolean? = null
)

fun PremiumActivationResponse.toDomain(): PremiumActivationResult {
    return PremiumActivationResult(
        message = message ?: "Premium activated successfully.",
        success = success ?: true
    )
}

