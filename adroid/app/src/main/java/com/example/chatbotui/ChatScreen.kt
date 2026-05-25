package com.example.chatbotui

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.ChatBubbleOutline
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Send
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ChatScreen(
    sessionId: String?,
    viewModel: ChatViewModel,
    onNavigateBack: () -> Unit,
    modifier: Modifier = Modifier
) {
    // Khởi tạo tải chi tiết phiên hội thoại cũ hoặc tạo phiên mới
    LaunchedEffect(sessionId) {
        if (!sessionId.isNullOrBlank()) {
            viewModel.loadSessionDetail(sessionId)
        } else {
            viewModel.createNewChatSession()
        }
    }

    val lazyListState = rememberLazyListState()
    val uiState = viewModel.chatUiState

    // Tự động cuộn xuống cuối LazyColumn khi có tin nhắn mới
    LaunchedEffect(uiState) {
        if (uiState is ChatUiState.Success) {
            val size = uiState.messages.size
            if (size > 0) {
                lazyListState.animateScrollToItem(size - 1)
            }
        }
    }

    // Tự động cuộn khi bot đang gõ tin nhắn
    LaunchedEffect(viewModel.isBotTyping) {
        if (viewModel.isBotTyping) {
            if (uiState is ChatUiState.Success && uiState.messages.isNotEmpty()) {
                lazyListState.animateScrollToItem(uiState.messages.size)
            }
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text(
                            text = "AI Assistant",
                            fontWeight = FontWeight.Bold,
                            fontSize = 18.sp,
                            color = Color.White
                        )
                        val subTitle = if (viewModel.activeSessionId != null) {
                            "Phiên: ...${viewModel.activeSessionId!!.takeLast(8)}"
                        } else {
                            "Cuộc hội thoại mới"
                        }
                        Text(
                            text = subTitle,
                            fontSize = 11.sp,
                            color = Color(0xFF8E8EA9)
                        )
                    }
                },
                navigationIcon = {
                    IconButton(onClick = onNavigateBack) {
                        Icon(
                            imageVector = Icons.Default.ArrowBack,
                            contentDescription = "Quay lại",
                            tint = Color.White
                        )
                    }
                },
                actions = {
                    IconButton(onClick = { viewModel.createNewChatSession() }) {
                        Icon(
                            imageVector = Icons.Default.AutoAwesome,
                            contentDescription = "Trò chuyện mới",
                            tint = Color(0xFF6C63FF)
                        )
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = Color(0xFF0F0F1A)
                )
            )
        },
        containerColor = Color(0xFF0F0F1A),
        modifier = modifier
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .background(Color(0xFF0F0F1A))
        ) {
            // Phần hiển thị nội dung chat (Chiếm diện tích chính)
            Box(
                modifier = Modifier
                    .weight(1f)
                    .fillMaxWidth()
            ) {
                when (val state = viewModel.chatUiState) {
                    is ChatUiState.Loading -> {
                        Box(
                            modifier = Modifier.fillMaxSize(),
                            contentAlignment = Alignment.Center
                        ) {
                            CircularProgressIndicator(color = Color(0xFF6C63FF))
                        }
                    }

                    is ChatUiState.Error -> {
                        Column(
                            modifier = Modifier
                                .fillMaxSize()
                                .padding(24.dp),
                            horizontalAlignment = Alignment.CenterHorizontally,
                            verticalArrangement = Arrangement.Center
                        ) {
                            Text(
                                text = "Lỗi: ${state.message}",
                                color = Color(0xFFFF5252),
                                fontSize = 15.sp,
                                modifier = Modifier.padding(bottom = 16.dp)
                            )
                            Button(
                                onClick = {
                                    val id = sessionId ?: viewModel.activeSessionId
                                    if (id != null) viewModel.loadSessionDetail(id)
                                },
                                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF6C63FF))
                            ) {
                                Text("Thử tải lại")
                            }
                        }
                    }

                    is ChatUiState.Success -> {
                        val messages = state.messages
                        if (messages.isEmpty() && !viewModel.isBotTyping) {
                            Column(
                                modifier = Modifier
                                    .fillMaxSize()
                                    .padding(32.dp),
                                horizontalAlignment = Alignment.CenterHorizontally,
                                verticalArrangement = Arrangement.Center
                            ) {
                                Icon(
                                    imageVector = Icons.Default.AutoAwesome,
                                    contentDescription = null,
                                    tint = Color(0x336C63FF),
                                    modifier = Modifier.size(72.dp)
                                )
                                Spacer(modifier = Modifier.height(16.dp))
                                Text(
                                    text = "Xin chào! Tôi có thể giúp gì cho bạn?",
                                    fontWeight = FontWeight.Bold,
                                    color = Color.White,
                                    fontSize = 18.sp
                                )
                                Spacer(modifier = Modifier.height(8.dp))
                                Text(
                                    text = "Nhập tin nhắn bên dưới để nhận phản hồi phân tích từ mô hình AI của FastAPI.",
                                    color = Color(0xFF8E8EA9),
                                    fontSize = 13.sp,
                                    modifier = Modifier.fillMaxWidth(0.8f),
                                    softWrap = true
                                )
                            }
                        } else {
                            LazyColumn(
                                state = lazyListState,
                                modifier = Modifier
                                    .fillMaxSize()
                                    .padding(horizontal = 16.dp),
                                verticalArrangement = Arrangement.spacedBy(12.dp)
                            ) {
                                items(messages, key = { it.id }) { message ->
                                    MessageBubbleItem(message = message)
                                }

                                // Hiển thị Typing Indicator khi bot đang xử lý
                                if (viewModel.isBotTyping) {
                                    item {
                                        TypingIndicatorItem()
                                    }
                                }
                                
                                // Thêm khoảng đệm bên dưới cùng
                                item {
                                    Spacer(modifier = Modifier.height(16.dp))
                                }
                            }
                        }
                    }

                    is ChatUiState.Idle -> {
                        // Trạng thái chờ khởi tạo
                    }
                }
            }

            // Phần nhập liệu ở dưới cùng
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(Color(0xFF1E1E2F))
                    .padding(horizontal = 16.dp, vertical = 12.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                OutlinedTextField(
                    value = viewModel.messageInput,
                    onValueChange = { viewModel.messageInput = it },
                    placeholder = { Text("Nhập tin nhắn...", color = Color(0xFF8E8EA9)) },
                    maxLines = 4,
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = Color(0xFF6C63FF),
                        unfocusedBorderColor = Color(0x22FFFFFF),
                        focusedTextColor = Color.White,
                        unfocusedTextColor = Color.White,
                        focusedContainerColor = Color(0xFF0F0F1A),
                        unfocusedContainerColor = Color(0xFF0F0F1A)
                    ),
                    shape = RoundedCornerShape(24.dp),
                    modifier = Modifier.weight(1f)
                )

                Spacer(modifier = Modifier.width(12.dp))

                IconButton(
                    onClick = { viewModel.sendMessage() },
                    enabled = viewModel.messageInput.isNotBlank() && !viewModel.isBotTyping,
                    modifier = Modifier
                        .size(48.dp)
                        .background(
                            if (viewModel.messageInput.isNotBlank() && !viewModel.isBotTyping) Color(0xFF6C63FF) else Color(0x22FFFFFF),
                            shape = CircleShape
                        )
                ) {
                    Icon(
                        imageVector = Icons.AutoMirrored.Filled.Send,
                        contentDescription = "Gửi tin nhắn",
                        tint = Color.White,
                        modifier = Modifier.size(20.dp)
                    )
                }
            }
        }
    }
}

@Composable
fun MessageBubbleItem(
    message: MessageResponse,
    modifier: Modifier = Modifier
) {
    val isUser = message.sender == "user"

    Row(
        modifier = modifier
            .fillMaxWidth()
            .padding(vertical = 2.dp),
        horizontalArrangement = if (isUser) Arrangement.End else Arrangement.Start,
        verticalAlignment = Alignment.Top
    ) {
        if (!isUser) {
            // Avatar Bot
            Box(
                modifier = Modifier
                    .size(32.dp)
                    .background(Color(0xFF6C63FF), shape = CircleShape)
                    .align(Alignment.Top),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    imageVector = Icons.Default.AutoAwesome,
                    contentDescription = null,
                    tint = Color.White,
                    modifier = Modifier.size(16.dp)
                )
            }
            Spacer(modifier = Modifier.width(8.dp))
        }

        Column(
            horizontalAlignment = if (isUser) Alignment.End else Alignment.Start,
            modifier = Modifier.weight(1f, fill = false)
        ) {
            Box(
                modifier = Modifier
                    .background(
                        color = if (isUser) Color(0xFF6C63FF) else Color(0xFF1E1E2F),
                        shape = if (isUser) {
                            RoundedCornerShape(16.dp, 16.dp, 0.dp, 16.dp)
                        } else {
                            RoundedCornerShape(16.dp, 16.dp, 16.dp, 0.dp)
                        }
                    )
                    .padding(horizontal = 16.dp, vertical = 12.dp)
            ) {
                Column {
                    Text(
                        text = message.message,
                        color = Color.White,
                        fontSize = 15.sp,
                        lineHeight = 20.sp
                    )

                    // Hiển thị Intent & Độ tự tin nếu có từ mô hình PyTorch (rất hữu ích & thú vị)
                    if (!isUser && message.intent != null && message.intent != "unknown" && message.confidence != null) {
                        val confidencePercent = (message.confidence * 100).toInt()
                        Spacer(modifier = Modifier.height(6.dp))
                        Text(
                            text = "🤖 AI Phân Tích: #${message.intent} (${confidencePercent}%)",
                            color = Color(0xFF00E676),
                            fontSize = 10.sp,
                            fontWeight = FontWeight.Bold,
                            fontStyle = FontStyle.Italic
                        )
                    }
                }
            }
        }

        if (isUser) {
            Spacer(modifier = Modifier.width(8.dp))
            // Avatar User
            Box(
                modifier = Modifier
                    .size(32.dp)
                    .background(Color(0x33FFFFFF), shape = CircleShape)
                    .align(Alignment.Top),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    imageVector = Icons.Default.Person,
                    contentDescription = null,
                    tint = Color.White,
                    modifier = Modifier.size(16.dp)
                )
            }
        }
    }
}

// Typing Indicator thiết kế nhấp nháy sang trọng
@Composable
fun TypingIndicatorItem(
    modifier: Modifier = Modifier
) {
    val infiniteTransition = rememberInfiniteTransition(label = "typing")
    val alpha by infiniteTransition.animateFloat(
        initialValue = 0.3f,
        targetValue = 1.0f,
        animationSpec = infiniteRepeatable(
            animation = tween(800),
            repeatMode = RepeatMode.Reverse
        ),
        label = "alpha"
    )

    Row(
        modifier = modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp),
        horizontalArrangement = Arrangement.Start,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Box(
            modifier = Modifier
                .size(32.dp)
                .background(Color(0xFF6C63FF), shape = CircleShape),
            contentAlignment = Alignment.Center
        ) {
            Icon(
                imageVector = Icons.Default.AutoAwesome,
                contentDescription = null,
                tint = Color.White,
                modifier = Modifier.size(16.dp)
            )
        }
        Spacer(modifier = Modifier.width(8.dp))
        Box(
            modifier = Modifier
                .background(
                    color = Color(0xFF1E1E2F),
                    shape = RoundedCornerShape(16.dp, 16.dp, 16.dp, 0.dp)
                )
                .alpha(alpha)
                .padding(horizontal = 16.dp, vertical = 12.dp)
        ) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(4.dp)
            ) {
                Text(
                    text = "Bot đang suy nghĩ",
                    color = Color(0xFF8E8EA9),
                    fontSize = 13.sp
                )
                // Các chấm động
                CircularProgressIndicator(
                    color = Color(0xFF6C63FF),
                    strokeWidth = 1.5.dp,
                    modifier = Modifier.size(12.dp)
                )
            }
        }
    }
}
