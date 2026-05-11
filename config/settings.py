import os
from pydantic_settings import BaseSettings

APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class Settings(BaseSettings):
    PROJECT_NAME: str = "Quizzin API"
    
    # Database
    DATABASE_URL: str
    
    # JWT
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    
    # Google OAuth
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    GOOGLE_MOBILE_CLIENT_ID: str
    
    # Local/App
    URL_BASE: str
    
    # SMTP Configuration
    RESEND_API_KEY: str
    RESEND_SENDER_EMAIL: str
    RESEND_SENDER_NAME: str

    # Cloudinary
    CLOUDINARY_CLOUD_NAME: str
    CLOUDINARY_API_KEY: str
    CLOUDINARY_API_SECRET: str

    # App environment
    APP_ENV: str = "development"
    
    class Config:
        env_file = os.path.join(APP_ROOT, ".env")
        extra = "ignore"

settings = Settings()
