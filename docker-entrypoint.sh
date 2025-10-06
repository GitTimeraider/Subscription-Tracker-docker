#!/usr/bin/env bash
set -e

# Security-hardened entrypoint with PUID/GUID support
# Supports both build-time users and runtime PUID/GUID configuration

# PUID/GUID support (legacy compatibility)
PUID=${PUID:-1000}
GUID=${GUID:-1000}

# Build-time user/group names (for security hardening)
APP_USER=${USER:-appuser}
APP_GROUP=${GROUP:-appgroup}

# Function to check if running with read-only filesystem
is_readonly_fs() {
    # Try to create a test file in /tmp to check if filesystem is writable
    touch /tmp/.write-test 2>/dev/null && rm -f /tmp/.write-test 2>/dev/null
    return $?
}

# Function to handle PUID/GUID configuration
setup_user_mapping() {
    # If we're running as root and PUID/GUID are specified, handle user mapping
    if [ "$(id -u)" = "0" ] && [ -n "$PUID" ] && [ -n "$GUID" ]; then
        
        # Check if we can modify /etc/passwd (not read-only filesystem)
        if ! is_readonly_fs && [ -w /etc/passwd ]; then
            echo "Setting up PUID/GUID mapping: $PUID:$GUID"
            
            # Create or modify user/group to match PUID/GUID
            if ! getent group "$GUID" >/dev/null 2>&1; then
                groupadd -g "$GUID" "$APP_GROUP" 2>/dev/null || true
            fi
            
            if ! getent passwd "$PUID" >/dev/null 2>&1; then
                useradd -u "$PUID" -g "$GUID" -d /app -s /bin/bash "$APP_USER" 2>/dev/null || true
            else
                # User exists, modify it
                usermod -u "$PUID" -g "$GUID" "$APP_USER" 2>/dev/null || true
            fi
            
            # Set APP_USER and APP_GROUP to the PUID/GUID values for gosu
            APP_USER="$PUID"
            APP_GROUP="$GUID"
        else
            echo "WARNING: Cannot modify users in read-only filesystem. Using build-time user."
            echo "To use custom PUID/GUID, either:"
            echo "  1. Use --user $PUID:$GUID with Docker"
            echo "  2. Mount writable /etc/passwd and /etc/group"
        fi
    fi
}

# Ensure writable directories exist for application data
# These should be mounted as volumes in production
ensure_writable_dirs() {
    # Only attempt directory creation if we can write
    if is_readonly_fs; then
        # For read-only filesystem, only check that required dirs exist
        if [ ! -d "/app/instance" ]; then
            echo "ERROR: /app/instance directory does not exist. Please mount it as a volume."
            exit 1
        fi
    else
        # For writable filesystem, create directories if needed
        mkdir -p /app/instance
        # Only attempt chown if we're running as root
        if [ "$(id -u)" = "0" ]; then
            # Use PUID:GUID if available, otherwise use build-time user
            local owner="${PUID:-$APP_USER}"
            local group="${GUID:-$APP_GROUP}"
            chown "$owner:$group" /app/instance 2>/dev/null || true
        fi
    fi
    
    # Ensure proper permissions on instance directory
    chmod 755 /app/instance 2>/dev/null || true
    
    # If SQLite database exists, ensure it has proper permissions
    if [ -f "/app/instance/subscriptions.db" ]; then
        chmod 664 /app/instance/subscriptions.db 2>/dev/null || true
        if [ "$(id -u)" = "0" ]; then
            local owner="${PUID:-$APP_USER}"
            local group="${GUID:-$APP_GROUP}"
            chown "$owner:$group" /app/instance/subscriptions.db 2>/dev/null || true
        fi
    fi
}

# Set up temporary directories for application runtime
setup_temp_dirs() {
    # Use /tmp for temporary files (usually writable even with read-only root)
    export TMPDIR="/tmp/app-runtime"
    export TEMP="/tmp/app-runtime"
    export TMP="/tmp/app-runtime"
    
    # Create temp directories if they don't exist and filesystem is writable
    if ! is_readonly_fs; then
        mkdir -p "$TMPDIR" 2>/dev/null || true
        if [ "$(id -u)" = "0" ]; then
            # Use PUID:GUID if available, otherwise use build-time user
            local owner="${PUID:-$APP_USER}"
            local group="${GUID:-$APP_GROUP}"
            chown "$owner:$group" "$TMPDIR" 2>/dev/null || true
        fi
    fi
}

# Check if we need to drop privileges
should_drop_privileges() {
    # Only drop privileges if we're running as root
    [ "$(id -u)" = "0" ]
}

# Initialize database with proper permissions
init_database() {
    # Only run database initialization if we're starting the main application
    if [[ "$1" == *"python"* ]] || [[ "$1" == *"gunicorn"* ]] || [[ "$1" == *"run.py"* ]]; then
        echo "Initializing database..."
        
        # Create database directory if it doesn't exist
        mkdir -p /app/instance
        
        # Set proper permissions for database operations
        if [ "$(id -u)" = "0" ]; then
            local owner="${PUID:-$APP_USER}"
            local group="${GUID:-$APP_GROUP}"
            chown "$owner:$group" /app/instance
            chmod 755 /app/instance
            
            # If database file exists, fix its permissions
            if [ -f "/app/instance/subscriptions.db" ]; then
                chown "$owner:$group" /app/instance/subscriptions.db
                chmod 664 /app/instance/subscriptions.db
            fi
        else
            # Running as non-root, ensure we can write to the directory
            if [ ! -w "/app/instance" ]; then
                echo "WARNING: /app/instance is not writable by current user $(id -u):$(id -g)"
                echo "Please ensure the mounted volume has proper permissions:"
                echo "  sudo chown -R $(id -u):$(id -g) ./data"
            fi
        fi
    fi
}

# Main execution
main() {
    echo "Starting Subscription Tracker..."
    echo "Running as user: $(id -u):$(id -g)"
    
    # Handle PUID/GUID mapping first
    setup_user_mapping
    
    # Set up required directories and environment
    ensure_writable_dirs
    setup_temp_dirs
    
    # Initialize database with proper permissions
    init_database "$@"
    
    # Drop privileges if running as root, otherwise run directly
    if should_drop_privileges; then
        echo "Dropping privileges to ${APP_USER}:${APP_GROUP}"
        exec gosu ${APP_USER}:${APP_GROUP} "$@"
    else
        echo "Running with current user privileges"
        exec "$@"
    fi
}

# Run main function
main "$@"
