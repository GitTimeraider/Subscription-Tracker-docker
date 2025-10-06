# Read-Only Filesystem and Security Hardening Guide

The Subscription Tracker Docker container now fully supports **read-only filesystems** and **user directives** for maximum security compliance.

## ✅ **Enhanced Security Support**

### **Read-Only Filesystem Compatibility**
```bash
# Full read-only support with tmpfs for temporary files
docker run -d \
  --read-only \
  --tmpfs /tmp:size=100M,mode=1777 \
  --tmpfs /var/tmp:size=10M,mode=1777 \
  -v ./data:/app/instance:rw \
  subscription-tracker
```

### **User Directive Support**
```bash
# Run as specific user without privilege escalation
docker run -d \
  --user 1000:1000 \
  --read-only \
  --cap-drop ALL \
  --cap-add NET_BIND_SERVICE \
  --security-opt no-new-privileges:true \
  -v ./data:/app/instance:rw \
  subscription-tracker
```

### **Docker Compose Security Example**
```yaml
version: '3.8'
services:
  web:
    build: .
    user: "1000:1000"
    read_only: true
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
    security_opt:
      - no-new-privileges:true
    tmpfs:
      - /tmp:size=100M,mode=1777
      - /var/tmp:size=10M,mode=1777
    volumes:
      - ./data:/app/instance:rw
    ports:
      - "5000:5000"
```

## 🔧 **How Enhanced Security Works**

### **Automatic Detection**
The container automatically detects and adapts to:

1. **🔒 Read-Only Filesystems** - Detects when `/` is mounted read-only
2. **👤 User Directives** - Detects when started with `--user` flag
3. **📁 Restricted Permissions** - Handles when `/etc/passwd` is not writable
4. **🛡️ Security Contexts** - Works with Kubernetes security policies

### **Deployment Modes**

#### **Standard Mode (Default)**
```bash
# Full PUID/GUID support with user creation
PUID=1000 GUID=1000 docker-compose up
```
**Features:**
- ✅ Creates custom users/groups
- ✅ Full PUID/GUID functionality
- ✅ Automatic permission fixing
- ✅ Database ownership management

#### **Read-Only Mode**
```bash
# Security-hardened with read-only filesystem
docker run --read-only --user 1000:1000 subscription-tracker
```
**Features:**
- ✅ No user creation attempts
- ✅ Works with existing user ID
- ✅ Database permissions via mount ownership
- ✅ Compatible with security scanners

#### **User Directive Mode**
```bash
# Kubernetes-compatible with security context
docker run --user 1000:1000 subscription-tracker
```
**Features:**
- ✅ Runs as specified user from start
- ✅ No privilege escalation
- ✅ Compatible with security policies
- ✅ Works in restricted environments

## 🎯 **Expected Behavior by Mode**

### **Standard Mode Output:**
```
🔧 Setting up user mapping...
🔧 Standard PUID/GUID mode: Setting up mapping 1000:1000
✅ Created group appgroup with GID 1000
✅ Created user appuser with UID 1000
✅ User mapping configured: 1000:1000
🎯 Deployment mode: STANDARD
🔑 Running as root - fixing ownership and permissions
✅ Set /app/instance ownership to 1000:1000 with 755 permissions
🔽 Dropping privileges to 1000:1000
```

### **Read-Only Mode Output:**
```
🔧 Setting up user mapping...
🔒 Read-only filesystem or restricted user management detected
🔒 Read-only filesystem mode
⚠️ Running as root but cannot create users in read-only filesystem
💡 For PUID/GUID support in read-only mode, use:
   docker run --user 1000:1000 --read-only ...
🎯 Deployment mode: READ-ONLY
ℹ️ Directory permissions unchanged (read-only filesystem)
```

### **User Directive Mode Output:**
```
🔧 Setting up user mapping...
👤 Container started with user directive (--user flag)
📋 User directive mode: Running as 1000:1000
ℹ️ PUID/GUID variables ignored in user directive mode
✅ Using container's current user for all operations
🎯 Deployment mode: STANDARD + USER-DIRECTIVE
👤 User directive mode: Running directly as 1000:1000
```

## 🛡️ **Security Features**

### **No Privilege Escalation**
- Container can run entirely as non-root
- No `sudo` or `setuid` operations required
- Compatible with `no-new-privileges:true`

### **Read-Only Root Filesystem**
- Application data isolated to mounted volumes
- No writes to container filesystem
- Prevents runtime tampering

### **Capability Dropping**
- Minimal capabilities required
- Only `NET_BIND_SERVICE` needed for port binding
- All other capabilities can be dropped

### **User Namespace Compatibility**
- Works with Docker user namespace remapping
- Compatible with rootless Docker
- Supports Kubernetes security contexts

## 🚨 **Migration from Previous Versions**

### **If You Currently Use PUID/GUID:**
Your existing setup continues to work:
```yaml
# This still works exactly the same
environment:
  - PUID=1000
  - GUID=1000
```

### **To Enable Maximum Security:**
Add security hardening:
```yaml
# Enhanced security version
user: "1000:1000"
read_only: true
cap_drop: [ALL]
cap_add: [NET_BIND_SERVICE]
security_opt: [no-new-privileges:true]
tmpfs:
  - /tmp:size=100M,mode=1777
  - /var/tmp:size=10M,mode=1777
```

## 🔍 **Troubleshooting Security Issues**

### **"groupadd: Permission denied" Error**
**This error no longer occurs!** The container now detects read-only filesystems and avoids user creation attempts.

### **"cannot lock /etc/group" Error**
**Fixed!** Container detects when `/etc/group` is not writable and uses alternative approaches.

### **User Directive Not Working**
Ensure data directory has correct ownership:
```bash
# Set ownership to match --user directive
sudo chown -R 1000:1000 ./data
docker run --user 1000:1000 subscription-tracker
```

### **Database Permission Issues in Read-Only Mode**
Ensure volume mount has correct ownership:
```bash
# Fix volume ownership before mounting
sudo chown -R 1000:1000 ./data
chmod 755 ./data
```

## 📊 **Security Compliance Matrix**

| Security Feature | Standard Mode | Read-Only Mode | User Directive |
|------------------|---------------|----------------|----------------|
| Read-Only Root FS | ⚠️ Optional | ✅ Required | ✅ Compatible |
| No Privilege Escalation | ⚠️ Uses gosu | ✅ Native | ✅ Native |
| User Creation | ✅ Dynamic | ❌ None | ❌ None |
| PUID/GUID Support | ✅ Full | ⚠️ Via --user | ⚠️ Via --user |
| Security Scanners | ⚠️ May flag | ✅ Clean | ✅ Clean |
| Kubernetes Ready | ⚠️ Needs config | ✅ Ready | ✅ Ready |
| Container Hardening | ⚠️ Manual | ✅ Built-in | ✅ Built-in |

## 🎉 **Benefits of Enhanced Security**

- **✅ Zero Security Violations** - No more permission denied errors
- **✅ Scanner Compatibility** - Passes security scanning tools
- **✅ Kubernetes Ready** - Works with security policies out of the box
- **✅ Backward Compatible** - Existing setups continue to work
- **✅ Future Proof** - Ready for evolving security requirements
- **✅ Compliance Ready** - Meets enterprise security standards

The container now supports **every** security scenario while maintaining full functionality! 🔒🚀