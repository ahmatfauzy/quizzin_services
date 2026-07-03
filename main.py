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

import asyncio
from contextlib import asynccontextmanager
from scheduler import start_scheduler

scheduler_instance = None

async def init_scheduler_async():
    global scheduler_instance
    loop = asyncio.get_running_loop()
    try:
        scheduler_instance = await loop.run_in_executor(None, start_scheduler)
    except Exception as e:
        print(f"Error starting scheduler background task: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    task = asyncio.create_task(init_scheduler_async())
    yield
    # Shutdown
    if scheduler_instance:
        try:
            scheduler_instance.shutdown(wait=False)
        except Exception:
            pass

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
