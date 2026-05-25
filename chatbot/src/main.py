import os
import json
import random
import torch
from typing import List
from fastapi import FastAPI, Depends, HTTPException, status, Cookie, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional

from src.database import engine, get_db, Base
from src import models
from src import schemas
from src import crud
from src.nltk_utils import tokenize, bag_of_words
from src.model import NeuralNet

# Dependency để lấy người dùng hiện tại thông qua Auth Session
async def get_current_user(
    x_session_token: Optional[str] = Header(None, alias="X-Session-Token"),
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    token = x_session_token or session_token
    if not token:
        return None
    
    db_session = crud.get_auth_session(db, session_token=token)
    if not db_session:
        return None
        
    return db_session.user

# Dependency bắt buộc người dùng đăng nhập
async def get_current_user_required(
    current_user: Optional[models.User] = Depends(get_current_user)
):
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bạn cần đăng nhập để thực hiện hành động này."
        )
    return current_user


# Tự động tạo các bảng trong cơ sở dữ liệu MySQL nếu chưa tồn tại
try:
    Base.metadata.create_all(bind=engine)
    print("MySQL database tables initialized successfully.")
except Exception as e:
    print(f"WARNING: Could not connect to MySQL database to initialize tables. Error: {e}")
    print("Please make sure your MySQL server is running and the DATABASE_URL in .env is correct.")

app = FastAPI(
    title="AI Chatbot API",
    description="Backend API cho Chatbot sử dụng FastAPI, PyTorch và MySQL",
    version="1.0.0"
)

# Cấu hình CORS để cho phép gọi API từ frontend an toàn (tránh xung đột Credentials + Wildcard Origin)
cors_origins_str = os.getenv("CORS_ALLOWED_ORIGINS")
if cors_origins_str:
    # Tách các domain bằng dấu phẩy
    allowed_origins = [origin.strip() for origin in cors_origins_str.split(",") if origin.strip()]
else:
    # Mặc định hỗ trợ các domain phổ biến khi phát triển
    allowed_origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

import glob

# Xác định đường dẫn file
script_dir = os.path.dirname(os.path.abspath(__file__))
intents_dir = os.path.join(script_dir, "..", "data", "intents")
data_pth_path = os.path.join(script_dir, "..", "data.pth")

# Cấu hình phần cứng
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# Tải dữ liệu intents (Hỗ trợ quét đa file và tự động gộp)
intents_files = []
if os.path.exists(intents_dir):
    intents_files = glob.glob(os.path.join(intents_dir, "*.json"))

# Nếu không tìm thấy file nào trong thư mục data/intents/, quay lại dùng intents.json gốc làm dự phòng
if not intents_files:
    fallback_paths = [
        os.path.join(script_dir, '..', 'intents.json'),
        os.path.join(script_dir, 'intents.json'),
        'intents.json'
    ]
    for path in fallback_paths:
        if os.path.exists(path):
            intents_files = [path]
            break

intents = {"intents": []}
for file_path in intents_files:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if "intents" in data and isinstance(data["intents"], list):
                intents["intents"].extend(data["intents"])
                print(f"Loaded {len(data['intents'])} intents from {os.path.basename(file_path)} for serving.")
    except Exception as e:
        print(f"WARNING: Could not load {file_path} in API serving. Error: {e}")

# Tải các mô hình học máy PyTorch (Định tuyến phân cấp)
router_model = None
router_words = []
router_categories = []

specialized_models = {}
specialized_words = {}
specialized_tags = {}

def load_hierarchical_models():
    global router_model, router_words, router_categories, specialized_models, specialized_words, specialized_tags
    
    router_path = os.path.join(script_dir, "..", "data_router.pth")
    if os.path.exists(router_path):
        try:
            router_data = torch.load(router_path, map_location=device)
            r_input_size = router_data["input_size"]
            r_hidden_size = router_data["hidden_size"]
            r_output_size = router_data["output_size"]
            router_words = router_data["all_words"]
            router_categories = router_data["categories"]
            
            router_model = NeuralNet(r_input_size, r_hidden_size, r_output_size).to(device)
            router_model.load_state_dict(router_data["model_state"])
            router_model.eval()
            print("Router Model loaded successfully.")
            
            # Tải động các mô hình chuyên sâu dựa trên categories định tuyến được
            for category in router_categories:
                spec_path = os.path.join(script_dir, "..", f"data_{category}.pth")
                if os.path.exists(spec_path):
                    try:
                        spec_data = torch.load(spec_path, map_location=device)
                        s_input_size = spec_data["input_size"]
                        s_hidden_size = spec_data["hidden_size"]
                        s_output_size = spec_data["output_size"]
                        
                        spec_model = NeuralNet(s_input_size, s_hidden_size, s_output_size).to(device)
                        spec_model.load_state_dict(spec_data["model_state"])
                        spec_model.eval()
                        
                        specialized_models[category] = spec_model
                        specialized_words[category] = spec_data["all_words"]
                        specialized_tags[category] = spec_data["tags"]
                        print(f"Specialized Bot [{category}] loaded successfully.")
                    except Exception as spec_err:
                        print(f"ERROR: Failed to load specialized model for category '{category}'. Error: {spec_err}")
                else:
                    print(f"WARNING: Specialized model file {spec_path} not found.")
        except Exception as e:
            print(f"ERROR: Failed to load Router Model. Error: {e}")
    else:
        print("WARNING: data_router.pth not found. Please run train.py first!")

# Load các mô hình khi khởi động app
load_hierarchical_models()

# Hàm dự đoán phản hồi từ chatbot (Hỗ trợ định tuyến 2 lớp & Query MySQL lấy câu trả lời)
def generate_bot_reply(user_text: str, db: Session = None):
    global router_model, router_words, router_categories, specialized_models, specialized_words, specialized_tags
    
    # Nếu mô hình chưa được tải, thử tải lại
    if router_model is None:
        load_hierarchical_models()
    
    if router_model is None:
        return "Xin chào! Hệ thống AI hiện đang trong quá trình bảo trì. Tôi sẽ sớm quay lại!", "maintenance", 0.0

    # 1. Định tuyến thông qua Router Model để tìm Chủ đề lớn (Category)
    sentence = tokenize(user_text)
    X_router = bag_of_words(sentence, router_words)
    X_router = X_router.reshape(1, X_router.shape[0])
    X_router = torch.from_numpy(X_router).to(device)

    outputs_router = router_model(X_router)
    _, predicted_router = torch.max(outputs_router, dim=1)
    category = router_categories[predicted_router.item()]

    probs_router = torch.softmax(outputs_router, dim=1)
    prob_router = probs_router[0][predicted_router.item()].item()

    # Ngưỡng tin cậy của Router (nếu router không tự tin, chọn 'general' làm mặc định)
    if prob_router < 0.60:
        category = "general"

    # 2. Dự đoán tag ý định cụ thể thông qua Specialized Bot tương ứng
    if category not in specialized_models:
        category = "general"

    if category not in specialized_models:
        return "Xin lỗi, tôi gặp sự cố khi xử lý câu hỏi này.", "error", 0.0

    spec_model = specialized_models[category]
    spec_vocab = specialized_words[category]
    spec_tags = specialized_tags[category]

    X_spec = bag_of_words(sentence, spec_vocab)
    X_spec = X_spec.reshape(1, X_spec.shape[0])
    X_spec = torch.from_numpy(X_spec).to(device)

    outputs_spec = spec_model(X_spec)
    _, predicted_spec = torch.max(outputs_spec, dim=1)
    tag = spec_tags[predicted_spec.item()]

    probs_spec = torch.softmax(outputs_spec, dim=1)
    prob = probs_spec[0][predicted_spec.item()].item()

    # 3. Phục hồi và trả về phản hồi thích hợp
    # Ngưỡng tin cậy chấp nhận ý định (70%)
    if prob > 0.70:
        # Cách A: Truy vấn danh sách phản hồi từ MySQL/SQLite Database (Phương pháp 2)
        if db is not None:
            try:
                responses = crud.get_bot_responses(db, tag=tag)
                if responses:
                    return random.choice(responses), tag, prob
            except Exception as db_err:
                print(f"WARNING: Could not fetch responses from DB. Error: {db_err}")

        # Cách B (Dự phòng): Lấy phản hồi trực tiếp từ tệp kịch bản trong bộ nhớ
        for intent in intents.get('intents', []):
            if tag == intent["tag"]:
                return random.choice(intent['responses']), tag, prob

    # Trả về câu trả lời mặc định nếu không hiểu rõ ý định
    fallback_responses = [
        "Xin lỗi, tôi chưa hiểu rõ ý bạn. Bạn có thể diễn đạt lại câu hỏi được không?",
        "Xin lỗi, câu hỏi này nằm ngoài phạm vi hiểu biết của tôi hiện tại.",
        "Tôi chưa có câu trả lời chính xác cho vấn đề này. Bạn có cần hỗ trợ gì khác không?"
    ]
    return random.choice(fallback_responses), "unknown", prob


# --- API ENDPOINTS ---

@app.get("/", tags=["General"])
def read_root():
    return {
        "status": "active",
        "message": "AI Chatbot FastAPI & MySQL API is running smoothly!",
        "model_loaded": router_model is not None
    }


# --- AUTHENTICATION ENDPOINTS ---

@app.post("/api/auth/register", response_model=schemas.UserResponse, tags=["Authentication"])
def register(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    """
    Đăng ký tài khoản người dùng mới.
    """
    db_user = crud.get_user_by_username(db, username=payload.username)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tên tài khoản đã tồn tại."
        )
    return crud.create_user(db, payload)


@app.post("/api/auth/login", response_model=schemas.LoginResponse, tags=["Authentication"])
def login(payload: schemas.UserLogin, db: Session = Depends(get_db)):
    """
    Đăng nhập hệ thống, tạo phiên đăng nhập (session) trong database.
    """
    from src.security import verify_password
    db_user = crud.get_user_by_username(db, username=payload.username)
    if not db_user or not verify_password(payload.password, db_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tên tài khoản hoặc mật khẩu không chính xác."
        )
    
    # Tạo session trong database hết hạn sau 7 ngày
    auth_session = crud.create_auth_session(db, user_id=db_user.id, expires_in_days=7)
    
    return schemas.LoginResponse(
        session_token=auth_session.id,
        user=schemas.UserResponse.model_validate(db_user)
    )


@app.post("/api/auth/logout", tags=["Authentication"])
def logout(
    x_session_token: Optional[str] = Header(None, alias="X-Session-Token"),
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """
    Đăng xuất, xóa phiên đăng nhập khỏi database.
    """
    token = x_session_token or session_token
    if token:
        crud.delete_auth_session(db, session_token=token)
    return {"message": "Đã đăng xuất thành công."}


# --- CHAT & HISTORY ENDPOINTS ---

@app.post("/api/chat", response_model=schemas.ChatResponse, tags=["Chat"])
def chat(
    payload: schemas.MessageCreate, 
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(get_current_user)
):
    """
    Gửi tin nhắn lên Chatbot.
    API tự động quản lý phiên chat (session) và lưu lịch sử cuộc hội thoại.
    Nếu người dùng đã đăng nhập, cuộc hội thoại sẽ được gắn với tài khoản của họ.
    """
    user_id = current_user.id if current_user else None

    # 1. Quản lý session
    session = crud.create_chat_session(db, session_id=payload.session_id, user_id=user_id)
    session_id = session.id

    # 2. Lưu tin nhắn của người dùng (User Message)
    crud.create_chat_message(
        db=db,
        session_id=session_id,
        sender="user",
        message=payload.message
    )

    # 3. Sử dụng mô hình AI dự đoán câu trả lời (Truyền thêm database session)
    bot_reply, intent, confidence = generate_bot_reply(payload.message, db=db)

    # 4. Lưu phản hồi của Bot (Bot Message) kèm thông tin phân tích
    crud.create_chat_message(
        db=db,
        session_id=session_id,
        sender="bot",
        message=bot_reply,
        intent=intent,
        confidence=confidence
    )

    return schemas.ChatResponse(
        session_id=session_id,
        bot_response=bot_reply,
        intent=intent,
        confidence=confidence
    )


@app.get("/api/sessions", response_model=List[schemas.SessionResponse], tags=["History"])
def get_sessions(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user_required)
):
    """
    Lấy danh sách các phiên hội thoại (chat sessions) của người dùng đang đăng nhập.
    """
    sessions = crud.get_chat_sessions(db, user_id=current_user.id, skip=skip, limit=limit)
    return sessions


@app.get("/api/sessions/{session_id}", response_model=schemas.SessionDetailResponse, tags=["History"])
def get_session_detail(
    session_id: str, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user_required)
):
    """
    Lấy toàn bộ lịch sử tin nhắn trong một phiên hội thoại cụ thể thuộc về người dùng đang đăng nhập.
    """
    session = crud.get_chat_session(db, session_id=session_id, user_id=current_user.id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Phiên hội thoại với ID {session_id} không tồn tại hoặc bạn không có quyền truy cập."
        )
    return session


@app.delete("/api/sessions/{session_id}", status_code=status.HTTP_200_OK, tags=["History"])
def delete_session(
    session_id: str, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user_required)
):
    """
    Xóa một phiên hội thoại và toàn bộ tin nhắn liên quan thuộc về người dùng đang đăng nhập.
    """
    session = crud.get_chat_session(db, session_id=session_id, user_id=current_user.id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Phiên hội thoại với ID {session_id} không tồn tại hoặc bạn không có quyền truy cập."
        )
    db.delete(session)
    db.commit()
    return {"message": f"Đã xóa thành công phiên hội thoại {session_id}."}

