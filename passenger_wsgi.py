# import importlib.machinery
# import importlib.util
# import os
# import sys


# sys.path.insert(0, os.path.dirname(__file__))

# def load_source(modname, filename):
#     loader = importlib.machinery.SourceFileLoader(modname, filename)
#     spec = importlib.util.spec_from_file_location(modname, filename, loader=loader)
#     module = importlib.util.module_from_spec(spec)
#     loader.exec_module(module)
#     return module

# wsgi = load_source('wsgi', 'passenger_wsgi.py')
# application = wsgi.application


import os
import sys

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, APP_ROOT)

from a2wsgi import ASGIMiddleware
from main import app

application = ASGIMiddleware(app)