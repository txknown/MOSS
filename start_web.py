"""Launch the local MOSS web interface."""

import errno
import socket
import threading
import time
import urllib.request
import webbrowser

import uvicorn

from core.memory import Memory
from web.server import PROJECT_ROOT, app


HOST = "127.0.0.1"
PORT = 8766
HOME_URL = f"http://{HOST}:{PORT}/node/home"
HEALTH_URL = f"http://{HOST}:{PORT}/api/health"


def port_is_available():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        # A recently stopped server can leave the port in TIME_WAIT. Reusing
        # that closed socket is safe; a genuinely active listener still makes
        # bind fail and is handled below.
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind((HOST, PORT))
        except OSError as error:
            if error.errno == errno.EADDRINUSE:
                return False
            raise SystemExit(f"Cannot check MOSS web port {HOST}:{PORT}: {error}") from error
    return True


def handle_existing_server():
    # Another MOSS installation may use a different memory directory. Never
    # open it automatically just because it advertises a compatible API.
    raise SystemExit(
        f"Cannot start MOSS web: {HOST}:{PORT} is being used by another process.\n"
        "Stop that process before running python start_web.py again."
    )


def open_browser_when_ready():
    for _ in range(100):
        try:
            with urllib.request.urlopen(HEALTH_URL, timeout=0.2):
                webbrowser.open(HOME_URL)
                return
        except OSError:
            time.sleep(0.05)


def main():
    if not port_is_available():
        handle_existing_server()
    # Initialize only at explicit launch, never during imports or HTTP reads.
    # The project root comes from this copy, independent of the working directory.
    Memory(project_root=PROJECT_ROOT)
    print(f"MOSS web interface: {HOME_URL}", flush=True)
    threading.Thread(target=open_browser_when_ready, daemon=True).start()
    uvicorn.run(app, host=HOST, port=PORT)


if __name__ == "__main__":
    main()
