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

    # Groq NLP
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama3-70b-8192"
    
    # Big Data / Scheduling
    MONGODB_URL: str
    REDIS_URL: str
    SCRAPE_INTERVAL_MINUTES: int

    class Config:
        env_file = os.path.join(APP_ROOT, ".env")
        extra = "ignore"

settings = Settings()
