package com.example.chatbotui

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.lifecycle.ViewModelProvider
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.example.chatbotui.ui.theme.ChatbotUITheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        // Khởi tạo các phụ thuộc
        val repository = ChatRepository(applicationContext)
        val authViewModel = ViewModelProvider(this, ViewModelFactory(repository))[AuthViewModel::class.java]
        val chatViewModel = ViewModelProvider(this, ViewModelFactory(repository))[ChatViewModel::class.java]
        
        enableEdgeToEdge()
        setContent {
            ChatbotUITheme {
                AppNavigation(
                    authViewModel = authViewModel,
                    chatViewModel = chatViewModel
                )
            }
        }
    }
}

@Composable
fun AppNavigation(
    authViewModel: AuthViewModel,
    chatViewModel: ChatViewModel
) {
    val navController = rememberNavController()
    // Theo dõi trạng thái đăng nhập từ DataStore Preferences qua Flow
    val isLoggedIn by authViewModel.isLoggedIn.collectAsState(initial = null)

    // Lắng nghe thay đổi trạng thái đăng nhập để tự động điều hướng
    LaunchedEffect(isLoggedIn) {
        if (isLoggedIn == true) {
            // Đã đăng nhập -> Chuyển thẳng tới Lịch sử hội thoại, xóa màn hình Auth khỏi Backstack
            navController.navigate("history") {
                popUpTo("auth") { inclusive = true }
            }
        } else if (isLoggedIn == false) {
            // Chưa đăng nhập / Đã đăng xuất -> Quay lại màn hình Xác thực, xóa toàn bộ lịch sử điều hướng
            navController.navigate("auth") {
                popUpTo(0) { inclusive = true }
            }
        }
    }

    NavHost(
        navController = navController,
        startDestination = "auth"
    ) {
        // Màn hình 1: Xác thực (Đăng ký / Đăng nhập)
        composable("auth") {
            AuthScreen(
                viewModel = authViewModel,
                onAuthSuccess = {
                    navController.navigate("history") {
                        popUpTo("auth") { inclusive = true }
                    }
                }
            )
        }

        // Màn hình 2: Danh sách lịch sử các cuộc hội thoại cũ
        composable("history") {
            HistoryScreen(
                chatViewModel = chatViewModel,
                authViewModel = authViewModel,
                onNavigateToChat = { sessionId ->
                    navController.navigate("chat/$sessionId")
                },
                onNavigateToNewChat = {
                    navController.navigate("chat/new_chat")
                },
                onLoggedOut = {
                    // Logic đăng xuất được LaunchedEffect phía trên tự động xử lý
                }
            )
        }

        // Màn hình 3: Khung nhắn tin hội thoại cụ thể (hoặc tạo hội thoại mới)
        composable(
            route = "chat/{sessionId}",
            arguments = listOf(navArgument("sessionId") { type = NavType.StringType })
        ) { backStackEntry ->
            val sessionId = backStackEntry.arguments?.getString("sessionId")
            // Nếu sessionId là "new_chat", hiểu là tạo phiên trò chuyện mới (truyền null)
            val cleanSessionId = if (sessionId == "new_chat") null else sessionId

            ChatScreen(
                sessionId = cleanSessionId,
                viewModel = chatViewModel,
                onNavigateBack = {
                    navController.popBackStack()
                }
            )
        }
    }
}