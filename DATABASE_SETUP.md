# Database Setup and Health Monitoring Guide

This application supports multiple database backends with automatic driver detection, optimization, and comprehensive health monitoring.

## Supported Databases

### SQLite (Default)
```bash
# Default - no configuration needed
DATABASE_URL=sqlite:///subscriptions.db
```

### PostgreSQL (with psycopg3)
```bash
# Standard PostgreSQL URL - automatically converted to use psycopg3
DATABASE_URL=postgresql://username:password@hostname:port/database_name
DATABASE_URL=postgres://username:password@hostname:port/database_name

# Explicit psycopg3 driver (also supported)
DATABASE_URL=postgresql+psycopg://username:password@hostname:port/database_name
```

### MySQL/MariaDB
```bash
DATABASE_URL=mysql+pymysql://username:password@hostname:port/database_name
DATABASE_URL=mariadb+pymysql://username:password@hostname:port/database_name
```

## PostgreSQL with psycopg3 Features

The application automatically:
- Converts `postgresql://` and `postgres://` URLs to use psycopg3 driver
- Optimizes connection pooling for psycopg3
- Sets appropriate timeouts and connection limits
- Enables connection health checks (`pool_pre_ping`)

## Connection Pool Settings

### PostgreSQL (psycopg3)
- **Pool Size**: 10 connections
- **Max Overflow**: 20 additional connections
- **Pool Timeout**: 30 seconds
- **Connection Timeout**: 10 seconds
- **Pool Recycle**: 1 hour (prevents stale connections)

### MySQL/MariaDB
- **Pool Size**: 10 connections
- **Max Overflow**: 20 additional connections
- **Charset**: utf8mb4 (full Unicode support)

### SQLite
- **Pool Timeout**: 10 seconds
- **Connection Timeout**: 20 seconds
- **Thread Safety**: Enabled (`check_same_thread=False`)

## Health Monitoring

### Docker Health Checks

The application includes comprehensive Docker health checks:

#### Built-in Health Endpoint
- **URL**: `http://localhost:5000/health`
- **Returns**: JSON with database connectivity and service status
- **Timeout**: 10 seconds
- **Retry**: 3 attempts

#### Docker Health Check Configuration
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1
```

#### Docker Compose Health Checks
```yaml
services:
  web:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    restart: unless-stopped
  
  postgres: # If using PostgreSQL
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user -d database"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s
  
  mariadb: # If using MariaDB
    healthcheck:
      test: ["CMD", "/usr/local/bin/healthcheck.sh", "--connect", "--innodb_initialized"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s
```

### Advanced Health Check Script

Use the included `health-check.sh` script for detailed monitoring:

```bash
# Basic health check
./health-check.sh

# Detailed health check with JSON output
./health-check.sh --detailed --json

# Custom timeout and URL
./health-check.sh --timeout=60 --url=http://your-domain.com

# Help
./health-check.sh --help
```

### Health Check Response Format

**Healthy Response** (200 OK):
```json
{
    "status": "healthy",
    "database": "ok",
    "currency_rates": "ok",
    "timestamp": "2025-10-06T10:30:00.000000"
}
```

**Unhealthy Response** (500 Internal Server Error):
```json
{
    "status": "unhealthy",
    "error": "Health check failed",
    "timestamp": "2025-10-06T10:30:00.000000"
}
```

### Monitoring Integration

The health checks work with:
- **Docker Swarm**: Service health monitoring
- **Kubernetes**: Liveness and readiness probes
- **Load Balancers**: Health check endpoints
- **Monitoring Tools**: Prometheus, Grafana, etc.

### Health Check Status Meanings

- **healthy**: All systems operational
- **unhealthy**: Critical failure (database connectivity issues)
- **degraded**: Some features may be limited (e.g., currency conversion)

## Troubleshooting

### "No module named 'psycopg2'" Error
This application uses **psycopg3** (modern PostgreSQL driver), not psycopg2. The error occurs when:
1. Using a plain `postgresql://` URL without driver specification
2. Solution: The app automatically converts URLs to use psycopg3

### Connection Issues
1. Verify database server is running and accessible
2. Check firewall settings for database port
3. Ensure database user has proper permissions
4. Review Docker logs for detailed error messages
5. Use health check endpoint to diagnose issues

### Health Check Failures
```bash
# Check container health status
docker ps

# View health check logs
docker inspect container_name | grep -A 10 Health

# Manual health check
curl -f http://localhost:5000/health
```

## Docker Environment Variables

```yaml
# docker-compose.yml example
environment:
  - DATABASE_URL=postgresql://myuser:mypass@db:5432/subscriptions
  - SECRET_KEY=your-secret-key-here
```

## Database Migration

The application automatically:
- Creates tables on first run
- Applies schema migrations for new features
- Creates default admin user (username: `admin`, password: `changeme`)

**Important**: Change the default admin password immediately after first login!