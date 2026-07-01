from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from database.database import engine, Base
from config.settings import settings
from routes import auth, document, chapter, quiz, analytics, profile, dashboard, notifications, face_auth, admin
from fastapi.middleware.cors import CORSMiddleware
from models.user import User
from models.document import Document
from models.chapter import Chapter
from models.question import Question
from models.quiz_attempt import QuizAttempt
from models.chapter_mastery import ChapterMastery
from models.notification import Notification
from models.face_data import FaceData

Base.metadata.create_all(bind=engine)

from contextlib import asynccontextmanager
from scheduler import start_scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    scheduler = start_scheduler()
    yield
    # Shutdown
    scheduler.shutdown()

app = FastAPI(
    title="Quizzin API",
    lifespan=lifespan,
    docs_url=None if settings.APP_ENV == "production" else "/docs",
    redoc_url=None if settings.APP_ENV == "production" else "/redoc",
)

app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(dashboard.router)
app.include_router(document.router)
app.include_router(chapter.router)
app.include_router(quiz.router)
app.include_router(analytics.router)
app.include_router(notifications.router)
app.include_router(face_auth.router)
app.include_router(admin.router)


@app.get("/")
def read_root():
    return {"message": "Welcome to Quizzin API"}
