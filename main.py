from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from database.database import engine, Base
from config.settings import settings
from routes import auth, document, chapter, quiz, analytics, profile, dashboard, notifications

from models.user import User
from models.document import Document
from models.chapter import Chapter
from models.question import Question
from models.quiz_attempt import QuizAttempt
from models.chapter_mastery import ChapterMastery
from models.notification import Notification

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Quizzin API",
    docs_url=None if settings.APP_ENV == "production" else "/docs",
    redoc_url=None if settings.APP_ENV == "production" else "/redoc",
)

app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(dashboard.router)
app.include_router(document.router)
app.include_router(chapter.router)
app.include_router(quiz.router)
app.include_router(analytics.router)
app.include_router(notifications.router)


@app.get("/")
def read_root():
    return {"message": "Welcome to Quizzin API"}
