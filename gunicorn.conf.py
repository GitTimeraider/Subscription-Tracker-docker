# Gunicorn configuration file
import logging


class HealthCheckFilter(logging.Filter):
    """Suppress access log entries for the /health endpoint."""
    def filter(self, record):
        return '/health' not in record.getMessage()


# Attach the filter to gunicorn's access logger on startup
def on_starting(server):
    logging.getLogger('gunicorn.access').addFilter(HealthCheckFilter())


# Server socket
bind = "0.0.0.0:5000"
backlog = 2048

# Worker processes
# NOTE: Only 1 worker is used to avoid multiple background schedulers running in parallel.
# APScheduler runs in-process threads; with multiple workers each would start its own
# scheduler causing duplicate notifications. If you need more throughput, consider an
# external task queue (e.g. Celery + Redis) and re-enable multiple workers then.
workers = 1
worker_class = "sync"
worker_connections = 1000
timeout = 120  # Increased from 60s to 120s for longer operations
keepalive = 2

# Restart workers after this many requests, to help prevent memory leaks
max_requests = 500  # Reduced from 1000 to prevent memory buildup
max_requests_jitter = 50

# Logging
loglevel = "info"
accesslog = "-"
errorlog = "-"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "subscription-tracker"

# Server mechanics
preload_app = True
daemon = False
user = None
group = None
tmp_upload_dir = None

# Control socket (gunicorn 25+)
# Default path falls back to $HOME/.gunicorn/ — user 99 (nobody) has HOME=/
# which causes a harmless but noisy permission error on every start.
control_socket_disable = True


def post_fork(server, worker):
    """Start the APScheduler notification scheduler inside the worker process.

    With preload_app=True the Flask app is loaded in the master process before
    fork(). Background threads don't survive fork(), so starting the scheduler
    here (in the worker) ensures it runs reliably on every container start
    without waiting for the first authenticated HTTP request.
    """
    try:
        from run import app
        from app.email import start_scheduler
        start_scheduler(app)
        app._scheduler_started = True
    except Exception as e:
        import logging
        logging.getLogger('gunicorn.error').warning(
            f'Could not start notification scheduler in post_fork: {e}'
        )


# SSL
keyfile = None
certfile = None

# Worker timeout
graceful_timeout = 60  # Increased from 30s to 60s
worker_tmp_dir = "/dev/shm"

# Additional timeout settings for better stability
worker_timeout = 120  # Same as timeout
worker_max_requests_jitter = 50

# Environment
raw_env = [
    'FLASK_ENV=production',
]

# Limits
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190
