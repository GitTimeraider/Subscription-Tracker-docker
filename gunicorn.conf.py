# Gunicorn configuration file

# Server socket
bind = "0.0.0.0:5000"
backlog = 2048

# Worker processes
workers = 2
worker_class = "sync"
worker_connections = 1000
timeout = 60  # Increased from default 30s to 60s
keepalive = 2

# Restart workers after this many requests, to help prevent memory leaks
max_requests = 1000
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

# SSL
keyfile = None
certfile = None

# Worker timeout
graceful_timeout = 30
worker_tmp_dir = "/dev/shm"

# Environment
raw_env = [
    'FLASK_ENV=production',
]

# Limits
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190
