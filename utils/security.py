from datetime import datetime, timedelta, timezone
import jwt
import bcrypt
from fastapi import HTTPException, status
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from config.settings import settings

SALT_VERIFY = "email-verification"
SALT_RESET = "password-reset"

_serializer = URLSafeTimedSerializer(settings.SECRET_KEY)

def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except ValueError:
        return False

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def generate_email_token(email: str, salt: str) -> str:
    return _serializer.dumps(email, salt=salt)

def verify_email_token(token: str, salt: str, max_age: int = 86400) -> str:
    try:
        return _serializer.loads(token, salt=salt, max_age=max_age)
    except SignatureExpired:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Link has expired. Please request a new one.",
            headers={"X-Error-Code": "TOKEN_EXPIRED"},
        )
    except BadSignature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token.",
            headers={"X-Error-Code": "TOKEN_INVALID"},
        )
