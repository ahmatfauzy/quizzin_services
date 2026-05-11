from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from database.database import engine, Base
from config.settings import settings
from routes import auth, document


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Quizzin API",
    lifespan=lifespan,
    docs_url=None if settings.APP_ENV == "production" else "/docs",
    redoc_url=None if settings.APP_ENV == "production" else "/redoc",
)

# Middleware Session dibutuhkan untuk authlib OAuth Web flow
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

app.include_router(auth.router)
app.include_router(document.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to Quizzin API"}