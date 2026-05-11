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
import time
import socket
import subprocess
import urllib.error
import urllib.request

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, APP_ROOT)

PORT = int(os.environ.get("PASSENGER_PORT", "18000"))
UVICORN_URL = f"http://127.0.0.1:{PORT}"


def _uvicorn_running():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.settimeout(1)
        s.connect(("127.0.0.1", PORT))
        s.close()
        return True
    except Exception:
        return False


if not _uvicorn_running():
    subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn", "main:app",
            "--host", "127.0.0.1", f"--port={PORT}",
        ],
        cwd=APP_ROOT,
        env=os.environ.copy(),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(10):
        time.sleep(1)
        if _uvicorn_running():
            break


def application(environ, start_response):
    path = environ.get("PATH_INFO", "/")
    qs = environ.get("QUERY_STRING", "")
    url = f"{UVICORN_URL}{path}"
    if qs:
        url += f"?{qs}"

    method = environ["REQUEST_METHOD"]
    body = environ.get("wsgi.input")
    cl = environ.get("CONTENT_LENGTH")
    data = body.read(int(cl)) if body and cl else None

    req = urllib.request.Request(url, data=data, method=method)
    for key, value in environ.items():
        if key.startswith("HTTP_"):
            header = key[5:].replace("_", "-").title()
            req.add_header(header, value)

    content_type = environ.get("CONTENT_TYPE")
    if content_type:
        req.add_header("Content-Type", content_type)

    try:
        resp = urllib.request.urlopen(req, timeout=60)
        status = f"{resp.status} {resp.reason}"
        headers = [(k.lower(), v) for k, v in resp.getheaders()]
        start_response(status, headers)
        return [resp.read()]
    except urllib.error.HTTPError as e:
        headers = [(k.lower(), v) for k, v in e.headers.items()]
        start_response(f"{e.code} {e.reason}", headers)
        return [e.read()]
    except Exception:
        start_response("500 Internal Server Error", [("content-type", "text/plain")])
        return [b"Internal Server Error"]