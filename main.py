from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from database.database import engine, Base
from config.settings import settings
from routes import auth, document
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Quizzin API")

# Middleware Session dibutuhkan untuk authlib OAuth Web flow
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

app.include_router(auth.router)
app.include_router(document.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to Quizzin API"}