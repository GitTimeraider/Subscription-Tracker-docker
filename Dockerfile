# Build stage
FROM python:3.13-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update \
	&& apt-get install -y --no-install-recommends \
		build-essential \
		default-libmysqlclient-dev \
		libpq-dev \
		pkg-config \
		gcc \
		python3-dev \
	&& rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Runtime stage
FROM python:3.13-slim

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update \
	&& apt-get install -y --no-install-recommends \
		gosu \
		default-mysql-client \
		libpq5 \
		curl \
	&& rm -rf /var/lib/apt/lists/*

# Create application user and group at build time for security hardening
# This supports read-only filesystems and user: directives
RUN groupadd -r -g 1000 appgroup \
	&& useradd -r -u 1000 -g appgroup -m -s /bin/bash appuser \
	&& mkdir -p /app/instance \
	&& chown -R appuser:appgroup /app

# Copy installed packages from builder stage
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application files and set ownership
COPY --chown=appuser:appgroup . .

# Make entrypoint executable
RUN chmod +x /app/docker-entrypoint.sh

# Create writable directories for read-only filesystem compatibility
RUN mkdir -p /tmp/app-runtime /var/tmp/app \
	&& chown -R appuser:appgroup /tmp/app-runtime /var/tmp/app \
	&& chmod 755 /tmp/app-runtime /var/tmp/app

ENV FLASK_APP=run.py \
	USER=appuser \
	GROUP=appgroup \
	UID=1000 \
	GID=1000

# Health check configuration
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
	CMD curl -f http://localhost:5000/health || exit 1

EXPOSE 5000

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["gunicorn", "-c", "gunicorn.conf.py", "run:app"]
