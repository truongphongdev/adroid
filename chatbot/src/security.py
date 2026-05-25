import bcrypt

def get_password_hash(password: str) -> str:
    """
    Băm mật khẩu sử dụng bcrypt để lưu vào database một cách an toàn.
    """
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    So sánh mật khẩu thô và mật khẩu đã băm trong database.
    """
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False
