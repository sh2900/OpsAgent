"""
Cloud Entrypoint for OpsAgent
Spawns the IT Simulator (8001), FastAPI Backend (8000), and Streamlit Dashboard (PORT).
Designed for single-container cloud hosting on platforms like Render, Railway, or Fly.io.
"""

import os
import signal
import subprocess
import sys
import time


def main():
    port = os.environ.get("PORT", "8501")
    print(f"=== Starting OpsAgent Cloud Services (Public Port: {port}) ===")

    # 1. Start Simulator on internal port 8001
    print("Starting IT Simulator on 127.0.0.1:8001...")
    sim_proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "sim_backend.main:sim",
            "--host",
            "127.0.0.1",
            "--port",
            "8001",
        ]
    )

    # 2. Start FastAPI Backend on internal port 8000
    print("Starting FastAPI Backend on 127.0.0.1:8000...")
    api_proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "backend.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
        ]
    )

    # Allow backend services a moment to bind and initialize
    time.sleep(3)

    # 3. Start Streamlit on the cloud provider's assigned PORT
    print(f"Starting Streamlit Dashboard on 0.0.0.0:{port}...")
    st_proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            "dashboard/app.py",
            "--server.port",
            str(port),
            "--server.address",
            "0.0.0.0",
            "--server.headless",
            "true",
            "--server.enableCORS",
            "false",
            "--server.enableXsrfProtection",
            "false",
        ]
    )

    def handle_exit(sig, frame):
        print("Received termination signal. Shutting down OpsAgent cloud processes...")
        for p in (st_proc, api_proc, sim_proc):
            try:
                p.terminate()
            except Exception:
                pass
        sys.exit(0)

    try:
        signal.signal(signal.SIGINT, handle_exit)
        signal.signal(signal.SIGTERM, handle_exit)
    except (ValueError, AttributeError):
        pass

    # Wait for the dashboard process
    st_proc.wait()


if __name__ == "__main__":
    main()
