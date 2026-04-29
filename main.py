from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from routes import auth
from database.database import engine, Base
from config.settings import settings

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Smart Tutor API")

# Middleware Session dibutuhkan untuk authlib OAuth Web flow
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

app.include_router(auth.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to Smart Tutor API"}