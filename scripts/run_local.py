#!/usr/bin/env python3
"""
Run both frontend and backend locally for development.
This script starts the NextJS frontend and FastAPI backend in parallel.
"""

import os
import sys
import subprocess
import signal
import time
import shutil
import platform
from pathlib import Path


def npm_command() -> str:
    """Resolve npm executable (npm.cmd on Windows when invoked from Python)."""
    for name in ("npm", "npm.cmd"):
        path = shutil.which(name)
        if path:
            return path
    return "npm.cmd" if platform.system() == "Windows" else "npm"

# Track subprocesses for cleanup
processes = []

def cleanup(signum=None, frame=None):
    """Clean up all subprocess on exit"""
    print("\n Shutting down services...")
    for proc in processes:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except:
            proc.kill()
    sys.exit(0)

# Register cleanup handlers
signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)

def check_requirements():
    """Check if required tools are installed"""
    checks = []

    # Check Node.js
    try:
        result = subprocess.run(["node", "--version"], capture_output=True, text=True)
        node_version = result.stdout.strip()
        checks.append(f" Node.js: {node_version}")
    except FileNotFoundError:
        checks.append(" Node.js not found - please install Node.js")

    # Check npm
    try:
        result = subprocess.run([npm_command(), "--version"], capture_output=True, text=True)
        npm_version = result.stdout.strip()
        checks.append(f" npm: {npm_version}")
    except FileNotFoundError:
        checks.append(" npm not found - please install npm")

    # Check uv (which manages Python for us)
    try:
        result = subprocess.run(["uv", "--version"], capture_output=True, text=True)
        uv_version = result.stdout.strip()
        checks.append(f" uv: {uv_version}")
    except FileNotFoundError:
        checks.append(" uv not found - please install uv")

    print("\n Prerequisites Check:")
    for check in checks:
        print(f"  {check}")

    # Exit if any critical tools are missing
    if any("not found" in check.lower() for check in checks):
        print("\n  Please install missing dependencies and try again.")
        sys.exit(1)

def check_env_files():
    """Check if environment files exist"""
    project_root = Path(__file__).parent.parent

    root_env = project_root / ".env"
    frontend_env = project_root / "frontend" / ".env.local"

    missing = []

    if not root_env.exists():
        missing.append(".env (root project file)")
    if not frontend_env.exists():
        missing.append("frontend/.env.local")

    if missing:
        print("\n  Missing environment files:")
        for file in missing:
            print(f"  - {file}")
        print("\nPlease create these files with the required configuration.")
        print("Copy .env.example to .env and frontend/.env.local with the required values.")
        sys.exit(1)

    print(" Environment files found")

def start_backend():
    """Start the FastAPI backend"""
    backend_dir = Path(__file__).parent.parent / "backend" / "api"

    print("\n Starting FastAPI backend...")

    # Check if dependencies are installed
    if not (backend_dir / ".venv").exists() and not (backend_dir / "uv.lock").exists():
        print("  Installing backend dependencies...")
        subprocess.run(["uv", "sync"], cwd=backend_dir, check=True)

    # Start the backend (log to file so 500 errors are visible)
    log_path = backend_dir / "api.log"
    log_file = open(log_path, "w", encoding="utf-8")
    print(f"  Backend logs: {log_path}")
    proc = subprocess.Popen(
        ["uv", "run", "main.py"],
        cwd=backend_dir,
        stdout=log_file,
        stderr=subprocess.STDOUT,
    )
    processes.append(proc)

    # Wait for backend to start
    print("  Waiting for backend to start...")
    for _ in range(30):  # 30 second timeout
        try:
            import httpx
            response = httpx.get("http://localhost:8000/health")
            if response.status_code == 200:
                print("   Backend running at http://localhost:8000")
                print("     API docs: http://localhost:8000/docs")
                return proc
        except:
            time.sleep(1)

    print("   Backend failed to start")
    cleanup()

def start_frontend():
    """Start the NextJS frontend"""
    frontend_dir = Path(__file__).parent.parent / "frontend"

    print("\n Starting NextJS frontend...")

    # Check if dependencies are installed
    if not (frontend_dir / "node_modules").exists():
        print("  Installing frontend dependencies...")
        subprocess.run([npm_command(), "install"], cwd=frontend_dir, check=True)

    # Start the frontend
    # DEVNULL avoids pipe backpressure; npm.cmd may exit while Node keeps serving on Windows
    proc = subprocess.Popen(
        [npm_command(), "run", "dev"],
        cwd=frontend_dir,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    processes.append(proc)

    # Wait for frontend to start (HTTP poll only; select() does not work on Windows pipes)
    print("  Waiting for frontend to start...")
    import httpx

    for _ in range(90):  # Next.js first compile can take a while
        try:
            httpx.get("http://localhost:3000", timeout=1)
            print("   Frontend running at http://localhost:3000")
            return proc
        except httpx.ConnectError:
            pass  # Server not ready yet
        except Exception:
            # Any non-connection error usually means the server is responding
            print("   Frontend running at http://localhost:3000")
            return proc

        time.sleep(1)

    print("   Frontend failed to start")
    cleanup()

def services_healthy() -> bool:
    """Check both dev servers respond (reliable on Windows; npm.cmd parent may exit early)."""
    import httpx

    try:
        backend = httpx.get("http://localhost:8000/health", timeout=2)
        if backend.status_code != 200:
            return False
    except Exception:
        return False

    try:
        httpx.get("http://localhost:3000", timeout=2)
        return True
    except httpx.ConnectError:
        return False
    except Exception:
        return True  # any HTTP response means the dev server is up


def monitor_processes():
    """Keep running until Ctrl+C or a service stops responding."""
    print("\n" + "="*60)
    print("Alex Financial Advisor - Local Development")
    print("="*60)
    print("\nServices:")
    print("  Frontend: http://localhost:3000")
    print("  Backend:  http://localhost:8000")
    print("  API Docs: http://localhost:8000/docs")
    print("\nPress Ctrl+C to stop.\n")
    print("="*60 + "\n")

    while True:
        if not services_healthy():
            print("\nA service stopped responding (backend or frontend). Shutting down...")
            cleanup()
        time.sleep(2)

def main():
    """Main entry point"""
    print("\n Alex Financial Advisor - Local Development Setup")
    print("="*50)

    # Check prerequisites
    check_requirements()
    check_env_files()

    # Install httpx if needed
    try:
        import httpx
    except ImportError:
        print("\n Installing httpx for health checks...")
        subprocess.run(["uv", "add", "httpx"], check=True)

    # Start services
    backend_proc = start_backend()
    frontend_proc = start_frontend()

    # Monitor processes
    try:
        monitor_processes()
    except KeyboardInterrupt:
        cleanup()

if __name__ == "__main__":
    main()