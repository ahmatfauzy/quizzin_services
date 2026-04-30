import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from main import app as fastapi_app
from a2wsgi import ASGIMiddleware

# Convert FastAPI (ASGI) application to WSGI for cPanel Passenger
application = ASGIMiddleware(fastapi_app)