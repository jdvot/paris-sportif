"""Gunicorn configuration for Render Standard (1 CPU, 2GB RAM).

Optimized for a single-CPU async FastAPI application.
- 2 uvicorn workers: handles worker crashes gracefully
- max_requests: prevents memory leaks over time
- preload_app: shares memory between workers via copy-on-write
"""

import multiprocessing
import os

# Bind to Render's PORT
bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"

# Workers: 2 for 1 CPU (1 active + 1 for graceful restarts/crash recovery)
workers = min(2, multiprocessing.cpu_count() + 1)
worker_class = "uvicorn.workers.UvicornWorker"

# Memory management: restart workers after N requests to prevent leaks
max_requests = 1000
max_requests_jitter = 50

# Timeouts
timeout = 120  # Allow long prediction/sync requests
graceful_timeout = 30
keepalive = 5

# Preload app to share memory between workers (copy-on-write)
preload_app = True

# Logging
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("LOG_LEVEL", "info").lower()
