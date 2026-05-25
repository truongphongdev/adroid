# AI Chatbot FastAPI & PyTorch Backend

Hệ thống Backend API cho Chatbot thông minh, được xây dựng trên nền tảng **FastAPI**, kết hợp với mô hình học máy **PyTorch** và cơ sở dữ liệu **MySQL / SQLite** thông qua **SQLAlchemy**.

Dự án sở hữu kiến trúc phân loại ý định 2 lớp (Hierarchical Intent Classification) gồm một **Router Classifier** để phân loại chủ đề lớn và các **Specialized Bots** chuyên sâu xử lý từng lĩnh vực cụ thể (General, Sales, Health, v.v.).

---

## 🌟 Tính năng nổi bật

*   **FastAPI High Performance:** Cung cấp API bất đồng bộ (async), hiệu năng cao, tự động sinh tài liệu Swagger UI trực quan.
*   **Phân loại ý định 2 lớp (PyTorch):**
    *   **Lớp 1 (Router Model):** Nhận diện chủ đề chung của câu hỏi (Ví dụ: `general`, `sales`, `health`).
    *   **Lớp 2 (Specialized Model):** Dự đoán thẻ ý định (`tag`) chi tiết trong chủ đề đó và trả về phản hồi tương ứng.
*   **Cơ chế dự phòng Cơ sở dữ liệu thông minh (Resilient DB):** Hỗ trợ kết nối **MySQL** mạnh mẽ cho môi trường Production. Nếu kết nối MySQL thất bại, hệ thống tự động chuyển cấu hình sang sử dụng **SQLite** cục bộ (`chatbot.db`) để giữ ứng dụng luôn hoạt động mượt mà.
*   **Quản lý Hội thoại & Lịch sử Chat:** Tự động tạo và quản lý phiên hội thoại (`session_id`), tự động ghi nhận lịch sử trao đổi của người dùng và phản hồi kèm độ tin cậy (`confidence`) của AI.
*   **Hệ thống Xác thực người dùng (Authentication):** Hỗ trợ Đăng ký, Đăng nhập và quản lý phiên làm việc thông qua Database-backed Session Token.
*   **Tự động Đồng bộ Dữ liệu Phản hồi:** Khi chạy huấn luyện, hệ thống tự động đồng bộ tất cả kịch bản trả lời từ file JSON vào Database để dễ dàng quản lý động mà không cần khởi động lại mô hình.

---

## 🛠️ Công nghệ sử dụng

*   **Ngôn ngữ:** Python 3.10+
*   **Web Framework:** FastAPI, Uvicorn
*   **AI/NLP:** PyTorch, NumPy, NLTK (Natural Language Toolkit)
*   **Database & ORM:** MySQL, SQLite, SQLAlchemy, PyMySQL
*   **Môi trường:** Python-dotenv, Cryptography, Bcrypt

---

## 📁 Cấu trúc thư mục dự án

```text
chatbot/
├── .env                  # Cấu hình biến môi trường (Database, CORS, v.v.)
├── chatbot.db            # Cơ sở dữ liệu SQLite cục bộ (tự động tạo)
├── migrate_intents.py    # Tập lệnh phân nhóm dữ liệu kịch bản intents
├── requirements.txt      # Danh sách thư viện phụ thuộc
├── data/                 # Thư mục chứa dữ liệu kịch bản
│   └── intents/          # Dữ liệu intent dạng JSON đã phân nhóm (general.json, sales.json...)
├── src/                  # Mã nguồn chính của ứng dụng
│   ├── main.py           # Entrypoint khởi chạy FastAPI API & Endpoints
│   ├── database.py       # Cấu hình kết nối DB và cơ chế tự động fallback SQLite
│   ├── models.py         # Định nghĩa các bảng Database (SQLAlchemy Models)
│   ├── schemas.py        # Định nghĩa kiểu dữ liệu đầu vào/đầu ra (Pydantic Models)
│   ├── crud.py           # Các thao tác đọc/ghi Cơ sở dữ liệu
│   ├── nltk_utils.py     # Tiền xử lý văn bản tiếng Việt (Tokenize, Stemming, BoW)
│   ├── model.py          # Kiến trúc mạng nơ-ron tuần tự (NeuralNet)
│   ├── train.py          # Huấn luyện mô hình Router & Specialized Bots
│   └── security.py       # Mã hóa mật khẩu người dùng
```

---

## 🚀 Hướng dẫn cài đặt và chạy dự án trên Windows

### 1. Di chuyển vào thư mục dự án
Mở terminal (PowerShell hoặc Command Prompt) và truy cập vào thư mục chứa chatbot:
```powershell
cd e:\Project\Nhom\chatbot
```

### 2. Kích hoạt môi trường ảo (Virtual Environment)
*   **Dành cho PowerShell:**
    ```powershell
    .venv\Scripts\Activate.ps1
    ```
*   **Dành cho Command Prompt (cmd):**
    ```cmd
    .venv\Scripts\activate.bat
    ```
*(Nếu chưa có sẵn môi trường ảo, bạn khởi tạo bằng cách chạy lệnh `python -m venv .venv` trước).*

### 3. Cài đặt các thư viện phụ thuộc
Cài đặt toàn bộ dependencies có trong `requirements.txt`:
```bash
pip install -r requirements.txt
```

### 4. Cấu hình biến môi trường (`.env`)
Tệp `.env` đã được định nghĩa ở thư mục gốc. Bạn có thể thay đổi đường dẫn kết nối MySQL tại biến `DATABASE_URL` nếu cần:
```env
DATABASE_URL=mysql+pymysql://root:123456@localhost:3306/chatbot_db
```
> *Lưu ý: Nếu không có MySQL hoặc kết nối lỗi, hệ thống sẽ tự tạo và sử dụng cơ sở dữ liệu SQLite cục bộ (`chatbot.db`) ở thư mục gốc.*

### 5. Tiền xử lý kịch bản dữ liệu (Migration)
Để phân chia tệp kịch bản gộp `intents.json` thành các nhóm chủ đề cụ thể trong thư mục `data/intents/`, chạy lệnh:
```bash
python migrate_intents.py
```

### 6. Huấn luyện mô hình AI (Training)
Để huấn luyện mô hình phân loại Router Classifier và các mô hình chuyên biệt, đồng thời đồng bộ câu trả lời mẫu vào database, chạy lệnh:
```bash
python src/train.py
```
*Hệ thống sẽ tự động tải các gói tài nguyên tiếng Việt cần thiết từ NLTK, chạy huấn luyện qua 1000 epoch và xuất các file mô hình `.pth` tương ứng.*

### 7. Khởi chạy Backend Server
Sử dụng Uvicorn để khởi chạy máy chủ FastAPI:
```bash
uvicorn src.main:app --reload
```

---

## ⚡ Kiểm tra và Tương tác với API

Sau khi máy chủ khởi động thành công, bạn mở trình duyệt và truy cập các liên kết:

*   **Tài liệu hướng dẫn trực quan (Swagger UI):** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
*   **Kiểm tra trạng thái máy chủ:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)

### Một số API Endpoints cốt lõi:
1.  **Authentication (Xác thực):**
    *   `POST /api/auth/register` : Đăng ký người dùng mới.
    *   `POST /api/auth/login` : Đăng nhập nhận `session_token` trong DB.
    *   `POST /api/auth/logout` : Đăng xuất, hủy phiên làm việc.
2.  **Chat (Trò chuyện):**
    *   `POST /api/chat` : Gửi tin nhắn lên chatbot (truyền kèm `session_id` tùy chọn). Trả về câu trả lời tự động, thẻ phân loại ý định `intent` và độ tin cậy dự đoán `confidence`.
3.  **History (Lịch sử):**
    *   `GET /api/sessions` : Xem các phiên trò chuyện của tài khoản hiện tại.
    *   `GET /api/sessions/{session_id}` : Chi tiết nội dung các cuộc trao đổi trong phiên.
    *   `DELETE /api/sessions/{session_id}` : Xóa phiên hội thoại.
