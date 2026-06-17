import os
import sys
import time
import socket
import subprocess
import urllib.request
import urllib.error
import signal

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, APP_ROOT)

PORT = int(os.environ.get("PASSENGER_PORT", "18000"))
UVICORN_URL = f"http://127.0.0.1:{PORT}"
PID_FILE = os.path.join(APP_ROOT, "tmp", "uvicorn.pid")

def kill_old_uvicorn():
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r") as f:
                pid = int(f.read().strip())
            os.kill(pid, signal.SIGTERM)
            time.sleep(1) # wait for it to die
        except Exception:
            pass
        finally:
            try:
                os.remove(PID_FILE)
            except Exception:
                pass

def _uvicorn_running():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.settimeout(1)
        s.connect(("127.0.0.1", PORT))
        s.close()
        return True
    except Exception:
        return False

# Always kill old instance when passenger_wsgi is loaded (which happens on app restart)
kill_old_uvicorn()

if not _uvicorn_running():
    p = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn", "main:app",
            "--host", "127.0.0.1", f"--port={PORT}",
        ],
        cwd=APP_ROOT,
        env=os.environ.copy(),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    # Save PID
    os.makedirs(os.path.join(APP_ROOT, "tmp"), exist_ok=True)
    with open(PID_FILE, "w") as f:
        f.write(str(p.pid))
        
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
        resp = urllib.request.urlopen(req, timeout=120)
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
