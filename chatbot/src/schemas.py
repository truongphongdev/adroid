from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict

# --- SCHEMAS CHO NGƯỜI DÙNG (USER) ---
class UserCreate(BaseModel):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LoginResponse(BaseModel):
    session_token: str
    user: UserResponse



# --- SCHEMAS CHO TIN NHẮN (MESSAGE) ---
class MessageCreate(BaseModel):
    message: str
    session_id: Optional[str] = None  # Nếu không truyền, API sẽ tự động tạo session mới
    user_id: Optional[int] = None      # ID của user (nếu có đăng nhập)

class MessageResponse(BaseModel):
    id: int
    session_id: str
    sender: str
    message: str
    intent: Optional[str] = None
    confidence: Optional[float] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- SCHEMAS CHO PHẢN HỒI CHATBOT (CHAT RESPONSE) ---
class ChatResponse(BaseModel):
    session_id: str
    bot_response: str
    intent: str
    confidence: float


# --- SCHEMAS CHO PHIÊN HỘI THOẠI (SESSION) ---
class SessionResponse(BaseModel):
    id: str
    user_id: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class SessionDetailResponse(BaseModel):
    id: str
    user_id: Optional[int] = None
    created_at: datetime
    messages: List[MessageResponse]

    model_config = ConfigDict(from_attributes=True)
