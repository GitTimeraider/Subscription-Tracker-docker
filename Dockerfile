# Build stage
FROM python:3.13-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update \
	&& apt-get install -y --no-install-recommends \
		build-essential \
		libpq-dev \
		default-libmysqlclient-dev \
		pkg-config \
	&& rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Runtime stage
FROM python:3.13-slim

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update \
	&& apt-get install -y --no-install-recommends \
		gosu \
		libpq5 \
		default-mysql-client \
	&& rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder stage
COPY --from=builder /root/.local /root/.local

# Make sure scripts in .local are usable:
ENV PATH=/root/.local/bin:$PATH

COPY . .

# Entrypoint will create/update user/group according to PUID/PGID
RUN chmod +x /app/docker-entrypoint.sh

ENV FLASK_APP=run.py \
	PUID=1000 \
	PGID=1000

EXPOSE 5000

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["gunicorn", "-c", "gunicorn.conf.py", "run:app"]
