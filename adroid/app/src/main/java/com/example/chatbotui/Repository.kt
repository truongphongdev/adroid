package com.example.chatbotui

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.intPreferencesKey
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.firstOrNull
import kotlinx.coroutines.flow.map

// Khởi tạo DataStore Preferences dạng Extension Property trên Context
val Context.dataStore: DataStore<Preferences> by preferencesDataStore(name = "user_prefs")

class ChatRepository(
    private val context: Context,
    private val apiService: ApiService = ApiService.create()
) {
    companion object {
        private val USER_ID = intPreferencesKey("user_id")
        private val SESSION_TOKEN = stringPreferencesKey("session_token")
    }

    // --- QUẢN LÝ SESSION TRÊN DATASTORE ---

    val userId: Flow<Int?> = context.dataStore.data.map { preferences ->
        preferences[USER_ID]
    }

    val sessionToken: Flow<String?> = context.dataStore.data.map { preferences ->
        preferences[SESSION_TOKEN]
    }

    val isLoggedIn: Flow<Boolean> = context.dataStore.data.map { preferences ->
        preferences[SESSION_TOKEN] != null
    }

    // Lấy token tức thời (sync-like trong coroutine) để gửi Header
    suspend fun getActiveToken(): String? {
        return sessionToken.firstOrNull()
    }

    // Lấy user_id tức thời để gửi kèm Body tin nhắn
    suspend fun getActiveUserId(): Int? {
        return userId.firstOrNull()
    }

    suspend fun saveSession(userId: Int, token: String) {
        context.dataStore.edit { preferences ->
            preferences[USER_ID] = userId
            preferences[SESSION_TOKEN] = token
        }
    }

    suspend fun clearSession() {
        context.dataStore.edit { preferences ->
            preferences.remove(USER_ID)
            preferences.remove(SESSION_TOKEN)
        }
    }

    // --- GỌI API QUA RETROFIT VỚI XỬ LÝ LỖI ---

    suspend fun register(payload: UserCreate): Result<UserResponse> = runCatching {
        apiService.register(payload)
    }

    suspend fun login(payload: UserCreate): Result<LoginResponse> = runCatching {
        val response = apiService.login(payload)
        // Lưu thông tin vào DataStore khi đăng nhập thành công
        saveSession(response.user.id, response.session_token)
        response
    }

    suspend fun logout(): Result<LogoutResponse> = runCatching {
        val token = getActiveToken()
        val response = apiService.logout(token)
        // Xóa thông tin DataStore khi đăng xuất thành công hoặc hết hạn
        clearSession()
        response
    }.onFailure {
        // Dự phòng: Xóa session local ngay cả khi API lỗi để người dùng không bị kẹt
        clearSession()
    }

    suspend fun sendMessage(message: String, sessionId: String?): Result<ChatResponse> = runCatching {
        val token = getActiveToken()
        val userId = getActiveUserId()
        val payload = MessageCreate(
            message = message,
            session_id = sessionId,
            user_id = userId
        )
        apiService.chat(token, payload)
    }

    suspend fun getSessions(): Result<List<SessionResponse>> = runCatching {
        val token = getActiveToken()
        apiService.getSessions(token)
    }

    suspend fun getSessionDetail(sessionId: String): Result<SessionDetailResponse> = runCatching {
        val token = getActiveToken()
        apiService.getSessionDetail(sessionId, token)
    }

    suspend fun deleteSession(sessionId: String): Result<DeleteResponse> = runCatching {
        val token = getActiveToken()
        apiService.deleteSession(sessionId, token)
    }
}
