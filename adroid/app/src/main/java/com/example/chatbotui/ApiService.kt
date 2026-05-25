package com.example.chatbotui

import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import java.util.concurrent.TimeUnit

// --- DATA CLASSES (DTOs) MATCHING FASTAPI ---

data class UserCreate(
    val username: String,
    val password: String
)

data class UserResponse(
    val id: Int,
    val username: String,
    val created_at: String
)

data class LoginResponse(
    val session_token: String,
    val user: UserResponse
)

data class MessageCreate(
    val message: String,
    val session_id: String? = null,
    val user_id: Int? = null
)

data class ChatResponse(
    val session_id: String,
    val bot_response: String,
    val intent: String,
    val confidence: Double
)

data class SessionResponse(
    val id: String,
    val user_id: Int?,
    val created_at: String
)

data class MessageResponse(
    val id: Int,
    val session_id: String,
    val sender: String,
    val message: String,
    val intent: String?,
    val confidence: Double?,
    val created_at: String
)

data class SessionDetailResponse(
    val id: String,
    val user_id: Int?,
    val created_at: String,
    val messages: List<MessageResponse>
)

data class LogoutResponse(
    val message: String
)

data class DeleteResponse(
    val message: String
)

// --- RETROFIT INTERFACE ---

interface ApiService {

    // --- AUTHENTICATION ---

    @POST("api/auth/register")
    suspend fun register(
        @Body payload: UserCreate
    ): UserResponse

    @POST("api/auth/login")
    suspend fun login(
        @Body payload: UserCreate // UserLogin structure is the same as UserCreate
    ): LoginResponse

    @POST("api/auth/logout")
    suspend fun logout(
        @Header("X-Session-Token") sessionToken: String?
    ): LogoutResponse

    // --- CHAT & HISTORY ---

    @POST("api/chat")
    suspend fun chat(
        @Header("X-Session-Token") sessionToken: String?,
        @Body payload: MessageCreate
    ): ChatResponse

    @GET("api/sessions")
    suspend fun getSessions(
        @Header("X-Session-Token") sessionToken: String?,
        @Query("skip") skip: Int = 0,
        @Query("limit") limit: Int = 100
    ): List<SessionResponse>

    @GET("api/sessions/{session_id}")
    suspend fun getSessionDetail(
        @Path("session_id") sessionId: String,
        @Header("X-Session-Token") sessionToken: String?
    ): SessionDetailResponse

    @DELETE("api/sessions/{session_id}")
    suspend fun deleteSession(
        @Path("session_id") sessionId: String,
        @Header("X-Session-Token") sessionToken: String?
    ): DeleteResponse

    companion object {
        // Địa chỉ kết nối đến Backend FastAPI cục bộ từ giả lập Android
        private const val BASE_URL = "http://10.0.2.2:8000/"

        fun create(): ApiService {
            val loggingInterceptor = HttpLoggingInterceptor().apply {
                level = HttpLoggingInterceptor.Level.BODY
            }

            val okHttpClient = OkHttpClient.Builder()
                .addInterceptor(loggingInterceptor)
                .connectTimeout(30, TimeUnit.SECONDS)
                .readTimeout(30, TimeUnit.SECONDS)
                .writeTimeout(30, TimeUnit.SECONDS)
                .build()

            return Retrofit.Builder()
                .baseUrl(BASE_URL)
                .client(okHttpClient)
                .addConverterFactory(GsonConverterFactory.create())
                .build()
                .create(ApiService::class.java)
        }
    }
}
