# PUID/GUID Configuration Guide

This document explains how to use custom User ID (PUID) and Group ID (GUID) with the Subscription Tracker, including compatibility with security-hardened deployments.

## Overview

The Subscription Tracker supports multiple user/group configuration approaches:

1. **Build-time users** (security-hardened, read-only compatible)
2. **Runtime PUID/GUID** (traditional approach)
3. **Docker user directive** (Kubernetes/security-conscious environments)
4. **Hybrid approach** (best of both worlds)

## Configuration Methods

### Method 1: Traditional PUID/GUID (Full Compatibility)

**Standard Docker Compose:**
```yaml
version: '3.8'
services:
  subscription-tracker:
    build: .
    environment:
      - PUID=1001
      - GUID=1001
    volumes:
      - ./data:/app/instance:rw
```

**Docker Command:**
```bash
docker run -d \
  -e PUID=1001 \
  -e GUID=1001 \
  -v ./data:/app/instance:rw \
  subscription-tracker
```

**What happens:**
- Container starts as root
- Entrypoint creates/modifies user to match PUID/GUID
- Privileges are dropped to the custom user
- Full file permission control

### Method 2: Docker User Directive (Kubernetes Compatible)

**Security-Hardened Docker Compose:**
```yaml
version: '3.8'
services:
  subscription-tracker:
    build: .
    user: "1001:1001"  # PUID:GUID directly
    volumes:
      - ./data:/app/instance:rw
```

**Docker Command:**
```bash
docker run -d \
  --user 1001:1001 \
  -v ./data:/app/instance:rw \
  subscription-tracker
```

**What happens:**
- Container starts directly as specified user
- No privilege escalation needed
- Compatible with read-only filesystems
- Kubernetes/security-compliant

### Method 3: Hybrid Approach (Recommended)

**Enhanced Docker Compose:**
```yaml
version: '3.8'
services:
  subscription-tracker:
    build: .
    environment:
      - PUID=1001
      - GUID=1001
    # Fallback user directive for security environments
    user: "${PUID:-1000}:${GUID:-1000}"
    volumes:
      - ./data:/app/instance:rw
```

**What happens:**
- Tries PUID/GUID environment variables first
- Falls back to user directive if environment doesn't allow user creation
- Works in both traditional and security-hardened environments

## Read-Only Filesystem Compatibility

### Problem
With read-only filesystems, the container cannot modify `/etc/passwd` or `/etc/group` to create custom users.

### Solutions

**Option A: Pre-set User Directive**
```yaml
services:
  subscription-tracker:
    user: "1001:1001"
    read_only: true
    tmpfs:
      - /tmp:size=100M,mode=1777
      - /var/tmp:size=10M,mode=1777
```

**Option B: Mount Writable User Files**
```yaml
services:
  subscription-tracker:
    environment:
      - PUID=1001
      - GUID=1001
    read_only: true
    tmpfs:
      - /tmp:size=100M,mode=1777
      - /var/tmp:size=10M,mode=1777
      - /etc/passwd:size=1M,mode=0644
      - /etc/group:size=1M,mode=0644
```

## File Permissions

### Data Directory Ownership

**Before Starting Container:**
```bash
# Create data directory with correct ownership
mkdir -p ./data
sudo chown -R 1001:1001 ./data
chmod -R 755 ./data
```

**Docker Compose with Init:**
```yaml
services:
  subscription-tracker:
    environment:
      - PUID=1001
      - GUID=1001
    volumes:
      - ./data:/app/instance:rw
    # Fix permissions on startup
    command: >
      sh -c "
        chown -R 1001:1001 /app/instance &&
        exec python run.py
      "
```

## Troubleshooting

### Issue: Permission Denied

**Symptoms:**
```
PermissionError: [Errno 13] Permission denied: '/app/instance/app.db'
```

**Solutions:**
1. Check data directory ownership:
   ```bash
   ls -la ./data
   # Should show: drwxr-xr-x 2 1001 1001
   ```

2. Fix permissions:
   ```bash
   sudo chown -R 1001:1001 ./data
   ```

3. Verify PUID/GUID in container:
   ```bash
   docker exec -it container_name id
   # Should show: uid=1001 gid=1001
   ```

### Issue: User Creation Failed

**Symptoms:**
```
WARNING: Cannot modify users in read-only filesystem
```

**Solutions:**
1. Use user directive instead of PUID/GUID:
   ```yaml
   user: "1001:1001"
   ```

2. Mount writable user files:
   ```yaml
   tmpfs:
     - /etc/passwd:size=1M,mode=0644
     - /etc/group:size=1M,mode=0644
   ```

### Issue: Security Policy Violations

**Symptoms:**
- Container fails to start in Kubernetes
- Security scanner flags privilege escalation

**Solutions:**
1. Use security-hardened compose:
   ```bash
   docker-compose -f docker-compose.security.yml up
   ```

2. Set security context in Kubernetes:
   ```yaml
   securityContext:
     runAsUser: 1001
     runAsGroup: 1001
     runAsNonRoot: true
   ```

## Best Practices

### For Development
- Use traditional PUID/GUID environment variables
- Mount local directories with proper ownership
- Use standard docker-compose.yml

### For Production
- Use user directive or security-hardened compose
- Implement proper volume management
- Consider using named volumes with init containers

### For Kubernetes
- Always use securityContext
- Never run as root (uid 0)
- Use read-only root filesystem when possible

## Migration Guide

### From PUID/GUID to User Directive

**Old Configuration:**
```yaml
environment:
  - PUID=1001
  - GUID=1001
```

**New Configuration:**
```yaml
user: "1001:1001"
# Remove PUID/GUID environment variables
```

### From Root to Non-Root

**Old Dockerfile:**
```dockerfile
USER root
```

**New Dockerfile:**
```dockerfile
RUN groupadd -g 1000 appgroup && \
    useradd -u 1000 -g appgroup -d /app appuser
USER appuser
```

## Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `PUID` | `1000` | User ID for application |
| `GUID` | `1000` | Group ID for application |
| `USER` | `appuser` | Username (build-time) |
| `GROUP` | `appgroup` | Group name (build-time) |

## Compatibility Matrix

| Deployment Method | Read-Only FS | Kubernetes | Security Scanning | Performance |
|-------------------|-------------|------------|------------------|-------------|
| PUID/GUID Env | ❌ | ⚠️ | ❌ | ✅ |
| User Directive | ✅ | ✅ | ✅ | ✅ |
| Hybrid Approach | ✅ | ✅ | ✅ | ✅ |
| Build-time User | ✅ | ✅ | ✅ | ✅ |

**Legend:**
- ✅ Full support
- ⚠️ Partial support
- ❌ Not supported

## Quick Reference

**Standard Development:**
```bash
PUID=1001 GUID=1001 docker-compose up
```

**Security-Hardened:**
```bash
docker-compose -f docker-compose.security.yml up
```

**Custom User ID:**
```bash
docker run --user 1001:1001 -v ./data:/app/instance subscription-tracker
```

**Kubernetes:**
```yaml
securityContext:
  runAsUser: 1001
  runAsGroup: 1001
  runAsNonRoot: true
```