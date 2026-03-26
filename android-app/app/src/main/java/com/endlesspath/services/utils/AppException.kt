package com.endlesspath.services.utils

sealed class AppException(
    message: String,
    cause: Throwable? = null
) : Exception(message, cause) {

    class Network(message: String, cause: Throwable? = null) : AppException(message, cause)

    class Unauthorized(message: String = "Your session expired. Please log in again.") :
        AppException(message)

    class Validation(message: String) : AppException(message)

    class NotFound(message: String) : AppException(message)

    class Conflict(message: String) : AppException(message)

    class Server(message: String) : AppException(message)

    class Http(val statusCode: Int, message: String) : AppException(message)

    class Unknown(message: String, cause: Throwable? = null) : AppException(message, cause)
}

