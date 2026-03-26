package com.endlesspath.services.data.api

import com.endlesspath.services.data.api.model.BookingCreateRequest
import com.endlesspath.services.data.api.model.BookingDto
import com.endlesspath.services.data.api.model.BookingListResponseDto
import com.endlesspath.services.data.api.model.GenericMessageResponse
import com.endlesspath.services.data.api.model.LoginRequest
import com.endlesspath.services.data.api.model.LoginResponse
import com.endlesspath.services.data.api.model.PremiumActivationRequest
import com.endlesspath.services.data.api.model.PremiumActivationResponse
import com.endlesspath.services.data.api.model.RegisterRequest
import com.endlesspath.services.data.api.model.ServiceDto
import com.endlesspath.services.data.api.model.ServiceListResponseDto
import com.endlesspath.services.data.api.model.UserResponseDto
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query

interface ApiService {

    @POST("api/v1/auth/login")
    suspend fun login(
        @Body request: LoginRequest
    ): Response<LoginResponse>

    @POST("api/v1/auth/register")
    suspend fun register(
        @Body request: RegisterRequest
    ): Response<UserResponseDto>

    @GET("api/v1/auth/me")
    suspend fun getCurrentUser(): Response<UserResponseDto>

    @POST("api/v1/auth/logout")
    suspend fun logout(): Response<GenericMessageResponse>

    @GET("api/v1/services/")
    suspend fun getServices(
        @Query("page") page: Int = 1,
        @Query("limit") limit: Int = 50
    ): Response<ServiceListResponseDto>

    @GET("api/v1/services/{serviceId}")
    suspend fun getService(
        @Path("serviceId") serviceId: String
    ): Response<ServiceDto>

    @POST("api/v1/bookings/create")
    suspend fun createBooking(
        @Body request: BookingCreateRequest
    ): Response<BookingDto>

    @GET("api/v1/bookings/me")
    suspend fun getMyBookings(
        @Query("page") page: Int = 1,
        @Query("limit") limit: Int = 50
    ): Response<BookingListResponseDto>

    @POST("api/v1/premium/activate")
    suspend fun activatePremium(
        @Body request: PremiumActivationRequest
    ): Response<PremiumActivationResponse>
}

