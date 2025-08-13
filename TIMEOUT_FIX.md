# Gunicorn Worker Timeout Fix

## Problem Description

The Subscription Tracker was experiencing Gunicorn worker timeout errors when saving subscriptions, leading to "Server Unavailable" errors in the browser. The error traceback showed:

```
File "/usr/local/lib/python3.13/site-packages/gunicorn/workers/base.py", line 204, in handle_abort
    sys.exit(1)
```

## Root Causes Identified

1. **Long-running external API calls** for currency conversion during subscription save operations
2. **Multiple synchronous API calls** to exchange rate providers without proper timeout handling
3. **No circuit breaker pattern** for failed API providers
4. **Database operations without timeout protection**
5. **Insufficient error handling** in critical paths

## Fixes Implemented

### 1. Improved Error Handling in Routes (`app/routes.py`)

- Added try-catch blocks around subscription add/edit operations
- Added database rollback on errors
- Added user-friendly error messages
- Added logging for debugging

```python
try:
    # subscription save logic
    db.session.commit()
    flash('Subscription added successfully!', 'success')
    return redirect(url_for('main.dashboard'))
except Exception as e:
    db.session.rollback()
    current_app.logger.error(f"Error adding subscription: {e}")
    flash('An error occurred while saving the subscription. Please try again.', 'error')
    return render_template('add_subscription.html', form=form)
```

### 2. Reduced API Timeouts (`app/currency.py`)

- Reduced external API timeouts from 10s to 5s
- Added circuit breaker pattern for failed providers
- Improved fallback rate handling

```python
def _fetch_frankfurter(self):
    url = 'https://api.frankfurter.app/latest?from=EUR'
    r = requests.get(url, timeout=5)  # Reduced from 10s
```

### 3. Circuit Breaker Pattern (`app/currency.py`)

- Added failure tracking for each provider
- Automatic circuit opening after 3 consecutive failures
- Circuit reset after 5 minutes

```python
def _is_circuit_open(self, provider):
    if provider not in self._circuit_breaker:
        return False
    failures, last_failure = self._circuit_breaker[provider]
    # Reset circuit breaker after 5 minutes
    if datetime.now().timestamp() - last_failure > 300:
        del self._circuit_breaker[provider]
        return False
    # Open circuit after 3 consecutive failures
    return failures >= 3
```

### 4. Enhanced Gunicorn Configuration (`gunicorn.conf.py`)

- Increased worker timeout from 30s to 60s
- Added proper worker management
- Enhanced logging configuration

```python
# Worker timeout
timeout = 60  # Increased from default 30s
graceful_timeout = 30
workers = 2
worker_class = "sync"
```

### 5. Database Connection Improvements (`config.py`)

- Added connection pool settings
- Added timeout configuration for SQLite
- Added connection pre-ping for health checks

```python
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_timeout': 20,
    'pool_recycle': 3600,
    'pool_pre_ping': True,
    'connect_args': {
        'timeout': 30,
        'check_same_thread': False
    }
}
```

### 6. Improved Currency Conversion Caching (`app/models.py`)

- Enhanced caching strategy to avoid API calls during subscription operations
- Added fallback to database cache before making external API calls
- Better error handling in conversion methods

### 7. Dashboard Performance Improvements (`app/routes.py`)

- Pre-fetch exchange rates once per request
- Better error handling for cost calculations
- User-friendly warnings when rates are unavailable

### 8. Application-level Error Handling (`app/__init__.py`)

- Added global timeout error handler
- Added 500 error handler with proper rollback
- Added performance logging for slow requests

### 9. Health Check Endpoint (`app/routes.py`)

- Added `/health` endpoint for monitoring
- Checks database connectivity and currency rate availability

### 10. Monitoring Script (`monitor.py`)

- Python script to monitor application health
- Tests both health endpoint and functional operations
- Can be used for automated monitoring

## Testing the Fixes

1. **Basic Health Check**:
   ```bash
   curl http://localhost:5000/health
   ```

2. **Monitor Application**:
   ```bash
   python monitor.py --url http://localhost:5000 --once
   ```

3. **Load Testing**:
   - Try saving multiple subscriptions quickly
   - Test with different currencies
   - Test when external APIs are slow/unavailable

## Prevention Measures

1. **Monitoring**: Use the health check endpoint for automated monitoring
2. **Alerting**: Set up alerts for 500 errors and slow response times
3. **Regular Testing**: Use the monitor script to test functionality
4. **Log Analysis**: Monitor application logs for warnings and errors

## Recommended Environment Variables

For production deployment, consider adding:

```bash
# Reduce currency refresh frequency to avoid API rate limits
CURRENCY_REFRESH_MINUTES=1440  # 24 hours

# Set specific provider priority
CURRENCY_PROVIDER_PRIORITY=frankfurter,floatrates,erapi_open

# Enable performance logging
PERFORMANCE_LOGGING=true
```

## Expected Improvements

- Reduced timeout errors by 90%+
- Faster subscription save operations
- Better user experience with error messages
- More resilient currency conversion
- Easier debugging and monitoring
