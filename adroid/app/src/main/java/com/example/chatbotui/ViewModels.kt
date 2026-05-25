package com.example.chatbotui

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.launch

// --- UI STATE REPRESENTATIONS ---

sealed interface AuthUiState {
    object Idle : AuthUiState
    object Loading : AuthUiState
    data class Success(val userId: Int, val username: String) : AuthUiState
    data class Error(val message: String) : AuthUiState
}

sealed interface HistoryUiState {
    object Idle : HistoryUiState
    object Loading : HistoryUiState
    data class Success(val sessions: List<SessionResponse>) : HistoryUiState
    data class Error(val message: String) : HistoryUiState
}

sealed interface ChatUiState {
    object Idle : ChatUiState
    object Loading : ChatUiState
    // Danh sách tin nhắn động để dễ dàng cập nhật trực tiếp tại local UI trước/sau khi API phản hồi
    data class Success(val messages: List<MessageResponse>) : ChatUiState
    data class Error(val message: String) : ChatUiState
}

// --- AUTH VIEWMODEL ---

class AuthViewModel(private val repository: ChatRepository) : ViewModel() {

    val isLoggedIn: Flow<Boolean> = repository.isLoggedIn
    val currentUserId: Flow<Int?> = repository.userId

    var usernameInput by mutableStateOf("")
    var passwordInput by mutableStateOf("")
    var authUiState by mutableStateOf<AuthUiState>(AuthUiState.Idle)
        private set

    fun resetInput() {
        usernameInput = ""
        passwordInput = ""
        authUiState = AuthUiState.Idle
    }

    fun login(onSuccess: () -> Unit) {
        if (usernameInput.isBlank() || passwordInput.isBlank()) {
            authUiState = AuthUiState.Error("Tài khoản và mật khẩu không được để trống.")
            return
        }

        viewModelScope.launch {
            authUiState = AuthUiState.Loading
            val payload = UserCreate(usernameInput, passwordInput)
            repository.login(payload)
                .onSuccess { loginResponse ->
                    authUiState = AuthUiState.Success(loginResponse.user.id, loginResponse.user.username)
                    resetInput()
                    onSuccess()
                }
                .onFailure { exception ->
                    val errorMsg = exception.message ?: "Đăng nhập thất bại. Vui lòng kiểm tra lại."
                    authUiState = AuthUiState.Error(errorMsg)
                }
        }
    }

    fun register(onSuccess: () -> Unit) {
        if (usernameInput.isBlank() || passwordInput.isBlank()) {
            authUiState = AuthUiState.Error("Tài khoản và mật khẩu không được để trống.")
            return
        }

        viewModelScope.launch {
            authUiState = AuthUiState.Loading
            val payload = UserCreate(usernameInput, passwordInput)
            repository.register(payload)
                .onSuccess {
                    // Đăng ký xong, tự động đăng nhập luôn
                    login(onSuccess)
                }
                .onFailure { exception ->
                    val errorMsg = exception.message ?: "Tài khoản đã tồn tại hoặc đăng ký thất bại."
                    authUiState = AuthUiState.Error(errorMsg)
                }
        }
    }

    fun logout(onSuccess: () -> Unit) {
        viewModelScope.launch {
            repository.logout()
            resetInput()
            onSuccess()
        }
    }
}

// --- CHAT & HISTORY VIEWMODEL ---

class ChatViewModel(private val repository: ChatRepository) : ViewModel() {

    var historyUiState by mutableStateOf<HistoryUiState>(HistoryUiState.Idle)
        private set

    var chatUiState by mutableStateOf<ChatUiState>(ChatUiState.Idle)
        private set

    var activeSessionId by mutableStateOf<String?>(null)
    var messageInput by mutableStateOf("")
    var isBotTyping by mutableStateOf(false)
        private set

    // --- QUẢN LÝ LỊCH SỬ PHIÊN ---

    fun loadHistory() {
        viewModelScope.launch {
            historyUiState = HistoryUiState.Loading
            repository.getSessions()
                .onSuccess { sessions ->
                    historyUiState = HistoryUiState.Success(sessions)
                }
                .onFailure { exception ->
                    historyUiState = HistoryUiState.Error(
                        exception.message ?: "Không thể tải lịch sử trò chuyện."
                    )
                }
        }
    }

    fun createNewChatSession() {
        activeSessionId = null
        chatUiState = ChatUiState.Success(emptyList())
        messageInput = ""
        isBotTyping = false
    }

    fun deleteSession(sessionId: String) {
        viewModelScope.launch {
            repository.deleteSession(sessionId)
                .onSuccess {
                    // Tải lại lịch sử sau khi xóa thành công
                    loadHistory()
                    // Nếu đang hiển thị đúng phiên bị xóa thì reset về chat mới
                    if (activeSessionId == sessionId) {
                        createNewChatSession()
                    }
                }
                .onFailure {
                    // Log hoặc thông báo nếu cần
                }
        }
    }

    // --- QUẢN LÝ HỘI THOẠI & TIN NHẮN ---

    fun loadSessionDetail(sessionId: String) {
        activeSessionId = sessionId
        viewModelScope.launch {
            chatUiState = ChatUiState.Loading
            repository.getSessionDetail(sessionId)
                .onSuccess { detailResponse ->
                    chatUiState = ChatUiState.Success(detailResponse.messages)
                }
                .onFailure { exception ->
                    chatUiState = ChatUiState.Error(
                        exception.message ?: "Không thể tải nội dung cuộc hội thoại."
                    )
                }
        }
    }

    fun sendMessage() {
        val text = messageInput.trim()
        if (text.isEmpty()) return

        // 1. Reset ô nhập
        messageInput = ""

        // Lấy danh sách tin nhắn hiện tại
        val currentMessages = when (val state = chatUiState) {
            is ChatUiState.Success -> state.messages.toMutableList()
            else -> mutableListOf()
        }

        // 2. Tạo tin nhắn người dùng cục bộ và hiển thị ngay trên UI
        val tempUserMsg = MessageResponse(
            id = -(System.currentTimeMillis() % 100000).toInt(), // ID âm tạm thời
            session_id = activeSessionId ?: "",
            sender = "user",
            message = text,
            intent = null,
            confidence = null,
            created_at = ""
        )
        currentMessages.add(tempUserMsg)
        chatUiState = ChatUiState.Success(currentMessages)

        // 3. Hiển thị bot đang phản hồi (typing indicator)
        isBotTyping = true

        viewModelScope.launch {
            repository.sendMessage(text, activeSessionId)
                .onSuccess { chatResponse ->
                    isBotTyping = false
                    
                    // Cập nhật lại session_id nếu đây là tin nhắn đầu tiên của phiên
                    if (activeSessionId == null) {
                        activeSessionId = chatResponse.session_id
                    }

                    // Thêm câu trả lời của Bot vào UI cục bộ
                    val tempBotMsg = MessageResponse(
                        id = -(System.currentTimeMillis() % 100000).toInt() - 1,
                        session_id = chatResponse.session_id,
                        sender = "bot",
                        message = chatResponse.bot_response,
                        intent = chatResponse.intent,
                        confidence = chatResponse.confidence,
                        created_at = ""
                    )
                    
                    val updatedMessages = when (val state = chatUiState) {
                        is ChatUiState.Success -> state.messages.toMutableList().apply { add(tempBotMsg) }
                        else -> mutableListOf(tempBotMsg)
                    }
                    chatUiState = ChatUiState.Success(updatedMessages)
                }
                .onFailure { exception ->
                    isBotTyping = false
                    
                    val tempErrorMsg = MessageResponse(
                        id = -(System.currentTimeMillis() % 100000).toInt() - 2,
                        session_id = activeSessionId ?: "",
                        sender = "bot",
                        message = "⚠️ Gửi tin thất bại: ${exception.message ?: "Lỗi kết nối máy chủ"}",
                        intent = "error",
                        confidence = 0.0,
                        created_at = ""
                    )
                    
                    val updatedMessages = when (val state = chatUiState) {
                        is ChatUiState.Success -> state.messages.toMutableList().apply { add(tempErrorMsg) }
                        else -> mutableListOf(tempErrorMsg)
                    }
                    chatUiState = ChatUiState.Success(updatedMessages)
                }
        }
    }
}

// --- VIEWMODEL PROVIDER FACTORY ---

class ViewModelFactory(private val repository: ChatRepository) : ViewModelProvider.Factory {
    override fun <T : ViewModel> create(modelClass: Class<T>): T {
        if (modelClass.isAssignableFrom(AuthViewModel::class.java)) {
            @Suppress("UNCHECKED_CAST")
            return AuthViewModel(repository) as T
        }
        if (modelClass.isAssignableFrom(ChatViewModel::class.java)) {
            @Suppress("UNCHECKED_CAST")
            return ChatViewModel(repository) as T
        }
        throw IllegalArgumentException("Unknown ViewModel class: ${modelClass.name}")
    }
}
