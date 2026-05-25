import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Load các biến môi trường từ .env
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    DATABASE_URL = "mysql+pymysql://root:root@localhost:3306/chatbot_db"

def create_resilient_engine():
    # Thử kết nối MySQL trước
    if DATABASE_URL and DATABASE_URL.startswith("mysql"):
        try:
            # Tạo engine thử kết nối nhanh
            temp_engine = create_engine(
                DATABASE_URL,
                pool_pre_ping=True,
                pool_recycle=3600,
            )
            # Thử kết nối thực tế để đảm bảo credentials đúng
            with temp_engine.connect() as conn:
                print("Successfully connected to MySQL database!")
                return temp_engine
        except Exception as e:
            print(f"WARNING: MySQL connection failed. Error: {e}")
            print("Falling back to local SQLite database (sqlite:///./chatbot.db) to keep the application running...")

    # Cấu hình SQLite làm dự phòng (cần check_same_thread=False cho SQLite)
    sqlite_url = "sqlite:///./chatbot.db"
    return create_engine(
        sqlite_url, 
        connect_args={"check_same_thread": False}
    )

engine = create_resilient_engine()

# Khởi tạo SessionLocal để thực thi truy vấn
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class cho các model ORM
Base = declarative_base()

# Dependency để lấy DB session trong FastAPI endpoints
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
