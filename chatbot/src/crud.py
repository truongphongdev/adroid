from datetime import datetime, timedelta, timezone
import uuid
import json
from sqlalchemy.orm import Session
from src import models
from src import schemas
from src.security import get_password_hash

# --- USER OPERATIONS ---

def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()

def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = get_password_hash(user.password)
    db_user = models.User(username=user.username, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# --- AUTH SESSION OPERATIONS ---

def create_auth_session(db: Session, user_id: int, expires_in_days: int = 7):
    token = str(uuid.uuid4())
    expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=expires_in_days)
    db_session = models.AuthSession(id=token, user_id=user_id, expires_at=expires_at)
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session

def get_auth_session(db: Session, session_token: str):
    session = db.query(models.AuthSession).filter(models.AuthSession.id == session_token).first()
    if session and session.expires_at > datetime.now(timezone.utc).replace(tzinfo=None):
        return session
    return None

def delete_auth_session(db: Session, session_token: str):
    db_session = db.query(models.AuthSession).filter(models.AuthSession.id == session_token).first()
    if db_session:
        db.delete(db_session)
        db.commit()
        return True
    return False

# --- CHAT SESSION OPERATIONS ---

def get_chat_session(db: Session, session_id: str, user_id: int = None):
    query = db.query(models.ChatSession).filter(models.ChatSession.id == session_id)
    if user_id is not None:
        query = query.filter(models.ChatSession.user_id == user_id)
    return query.first()

def create_chat_session(db: Session, session_id: str = None, user_id: int = None):
    # Nếu session_id đã được truyền vào, kiểm tra xem nó đã tồn tại chưa
    if session_id:
        existing_session = get_chat_session(db, session_id, user_id)
        if existing_session:
            return existing_session
        db_session = models.ChatSession(id=session_id, user_id=user_id)
    else:
        db_session = models.ChatSession(user_id=user_id)
    
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session

def get_chat_sessions(db: Session, user_id: int = None, skip: int = 0, limit: int = 100):
    query = db.query(models.ChatSession)
    if user_id is not None:
        query = query.filter(models.ChatSession.user_id == user_id)
    return query.order_by(models.ChatSession.created_at.desc()).offset(skip).limit(limit).all()

# --- CHAT MESSAGE OPERATIONS ---

def create_chat_message(
    db: Session, 
    session_id: str, 
    sender: str, 
    message: str, 
    intent: str = None, 
    confidence: float = None
):
    db_message = models.ChatMessage(
        session_id=session_id,
        sender=sender,
        message=message,
        intent=intent,
        confidence=confidence
    )
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    return db_message

def get_session_messages(db: Session, session_id: str):
    return db.query(models.ChatMessage).filter(models.ChatMessage.session_id == session_id).order_by(models.ChatMessage.created_at.asc()).all()


# --- BOT RESPONSE OPERATIONS (DATABASE RESPONSES STORAGE) ---

def sync_bot_response(db: Session, tag: str, category: str, responses: list):
    """
    Đồng bộ danh sách câu trả lời của một tag vào cơ sở dữ liệu (tự động update nếu đã có).
    """
    responses_str = json.dumps(responses, ensure_ascii=False)
    
    db_resp = db.query(models.BotResponse).filter(models.BotResponse.tag == tag).first()
    if db_resp:
        db_resp.category = category
        db_resp.responses = responses_str
    else:
        db_resp = models.BotResponse(tag=tag, category=category, responses=responses_str)
        db.add(db_resp)
        
    db.commit()
    db.refresh(db_resp)
    return db_resp

def get_bot_responses(db: Session, tag: str) -> list:
    """
    Lấy danh sách các phản hồi của một tag cụ thể dưới dạng List.
    """
    db_resp = db.query(models.BotResponse).filter(models.BotResponse.tag == tag).first()
    if db_resp:
        try:
            return json.loads(db_resp.responses)
        except Exception:
            return []
    return []
