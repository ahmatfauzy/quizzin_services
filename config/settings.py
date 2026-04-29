from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Smart Tutor API"
    
    # Database
    DATABASE_URL: str = "postgresql://user:password@localhost/dbname"
    
    # JWT
    SECRET_KEY: str = "your-secret-key-here"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    
    # Google OAuth
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_MOBILE_CLIENT_ID: str = ""
    
    # Local/App
    URL_BASE: str = "http://127.0.0.1:8000"
    
    # SMTP Configuration
    RESEND_API_KEY: str = ""
    RESEND_SENDER_EMAIL: str = ""
    RESEND_SENDER_NAME: str = "Quizzin"
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
