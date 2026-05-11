import os
import sys

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(APP_ROOT)
sys.path.insert(0, APP_ROOT)

from main import app as fastapi_app
from a2wsgi import ASGIMiddleware

application = ASGIMiddleware(fastapi_app)