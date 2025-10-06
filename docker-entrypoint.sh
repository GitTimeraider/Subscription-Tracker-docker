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

# Function to check if running with read-only filesystem or restricted user management
is_readonly_fs() {
    # Check if root filesystem is read-only
    if mount | grep -q 'on / .*ro,'; then
        return 0  # Read-only
    fi
    
    # Check if we can write to /tmp (basic filesystem test)
    if ! touch /tmp/.write-test 2>/dev/null; then
        return 0  # Read-only
    fi
    rm -f /tmp/.write-test 2>/dev/null
    
    # Check if /etc/passwd and /etc/group are writable (critical for user management)
    if [ ! -w /etc/passwd ] || [ ! -w /etc/group ]; then
        return 0  # User management not possible
    fi
    
    return 1  # Writable
}

# Function to detect if container was started with --user directive
is_user_directive() {
    # If we're not running as root, we were likely started with --user
    if [ "$(id -u)" != "0" ]; then
        return 0  # User directive used
    fi
    
    # Additional check: if PUID/GUID are set but we can't modify users, likely user directive
    if [ -n "$PUID" ] && [ -n "$GUID" ] && is_readonly_fs; then
        return 0  # Likely user directive scenario
    fi
    
    return 1  # Not user directive
}

# Function to handle PUID/GUID configuration with read-only and user directive support
setup_user_mapping() {
    echo "🔧 Setting up user mapping..."
    echo "Current user: $(id)"
    echo "PUID=${PUID:-not set}, GUID=${GUID:-not set}"
    echo "APP_USER=${APP_USER}, APP_GROUP=${APP_GROUP}"
    
    # Detect deployment scenario
    local readonly_detected=false
    local user_directive_detected=false
    
    if is_readonly_fs; then
        readonly_detected=true
        echo "🔒 Read-only filesystem or restricted user management detected"
    fi
    
    if is_user_directive; then
        user_directive_detected=true
        echo "👤 Container started with user directive (--user flag)"
    fi
    
    # Handle different scenarios
    if [ "$user_directive_detected" = "true" ]; then
        echo "📋 User directive mode: Running as $(id -u):$(id -g)"
        echo "ℹ️ PUID/GUID variables ignored in user directive mode"
        echo "✅ Using container's current user for all operations"
        # Don't try to change users or use gosu
        APP_USER="$(id -u)"
        APP_GROUP="$(id -g)"
        
    elif [ "$readonly_detected" = "true" ]; then
        echo "🔒 Read-only filesystem mode"
        if [ "$(id -u)" = "0" ]; then
            echo "⚠️ Running as root but cannot create users in read-only filesystem"
            echo "💡 For PUID/GUID support in read-only mode, use:"
            echo "   docker run --user $PUID:$GUID --read-only ..."
            echo "✅ Will use build-time user for privilege dropping"
            # Use build-time defaults since we can't create custom users
            APP_USER="1000"
            APP_GROUP="1000"
        else
            echo "✅ Already running as non-root user in read-only mode"
            APP_USER="$(id -u)"
            APP_GROUP="$(id -g)"
        fi
        
    elif [ "$(id -u)" = "0" ] && [ -n "$PUID" ] && [ -n "$GUID" ]; then
        echo "🔧 Standard PUID/GUID mode: Setting up mapping $PUID:$GUID"
        
        # Create or modify group to match GUID
        if ! getent group "$GUID" >/dev/null 2>&1; then
            if groupadd -g "$GUID" "$APP_GROUP" 2>/dev/null; then
                echo "✅ Created group $APP_GROUP with GID $GUID"
            else
                echo "⚠️ Could not create group, will use existing"
            fi
        else
            echo "ℹ️ Group with GID $GUID already exists"
        fi
        
        # Create or modify user to match PUID
        if ! getent passwd "$PUID" >/dev/null 2>&1; then
            if useradd -u "$PUID" -g "$GUID" -d /app -s /bin/bash "$APP_USER" 2>/dev/null; then
                echo "✅ Created user $APP_USER with UID $PUID"
            else
                echo "⚠️ Could not create user, will use existing"
            fi
        else
            # User exists, check if it's ours or handle gracefully
            existing_user=$(getent passwd "$PUID" | cut -d: -f1)
            if [ "$existing_user" = "$APP_USER" ]; then
                if usermod -g "$GUID" "$APP_USER" 2>/dev/null; then
                    echo "✅ Updated user $APP_USER with GID $GUID"
                else
                    echo "ℹ️ User $APP_USER already properly configured"
                fi
            else
                echo "ℹ️ UID $PUID is used by $existing_user (will use numeric ID)"
            fi
        fi
        
        # Use PUID/GUID for operations
        APP_USER="$PUID"
        APP_GROUP="$GUID"
        echo "✅ User mapping configured: $APP_USER:$APP_GROUP"
        
    elif [ "$(id -u)" = "0" ]; then
        echo "� Root mode without PUID/GUID: Using build-time defaults"
        APP_USER="1000"
        APP_GROUP="1000"
        echo "💡 To use custom IDs, set PUID and GUID environment variables"
        
    else
        echo "👤 Non-root mode: Using current user $(id -u):$(id -g)"
        APP_USER="$(id -u)"
        APP_GROUP="$(id -g)"
    fi
    
    echo "📋 Final configuration: $APP_USER:$APP_GROUP"
    echo "🎯 Deployment mode: $([ "$readonly_detected" = "true" ] && echo "READ-ONLY" || echo "STANDARD") $([ "$user_directive_detected" = "true" ] && echo "+ USER-DIRECTIVE" || echo "")"
}

# Ensure writable directories exist for application data with comprehensive self-fixing
ensure_writable_dirs() {
    echo "🔧 Setting up application directories and permissions..."
    
    # Determine target user/group (PUID/GUID takes precedence)
    local target_uid="${PUID:-1000}"
    local target_gid="${GUID:-1000}"
    local target_user="${APP_USER}"
    local target_group="${APP_GROUP}"
    
    echo "Target ownership: $target_uid:$target_gid ($target_user:$target_group)"
    
    # Only attempt directory creation if we can write
    if is_readonly_fs; then
        echo "⚠️ Read-only filesystem detected"
        # For read-only filesystem, only check that required dirs exist
        if [ ! -d "/app/instance" ]; then
            echo "❌ ERROR: /app/instance directory does not exist. Please mount it as a volume."
            exit 1
        fi
        echo "✅ Instance directory exists on read-only filesystem"
    else
        # Create directories if needed
        mkdir -p /app/instance
        echo "📁 Created /app/instance directory"
        
        # Fix ownership and permissions
        if [ "$(id -u)" = "0" ] && ! is_user_directive; then
            echo "🔑 Running as root - fixing ownership and permissions"
            
            # Set directory ownership and permissions (with error handling for read-only)
            if chown "$target_uid:$target_gid" /app/instance 2>/dev/null; then
                chmod 755 /app/instance
                echo "✅ Set /app/instance ownership to $target_uid:$target_gid with 755 permissions"
            else
                echo "⚠️ Could not change ownership (possibly read-only filesystem)"
                if chmod 755 /app/instance 2>/dev/null; then
                    echo "✅ Set directory permissions to 755"
                else
                    echo "ℹ️ Directory permissions unchanged (read-only filesystem)"
                fi
            fi
            
            # Handle existing database file
            if [ -f "/app/instance/subscriptions.db" ]; then
                echo "🗄️ Database file exists - fixing permissions"
                chown "$target_uid:$target_gid" /app/instance/subscriptions.db
                chmod 664 /app/instance/subscriptions.db
                
                # Test database write capability
                if command -v sqlite3 >/dev/null 2>&1; then
                    if ! sudo -u "#$target_uid" sqlite3 /app/instance/subscriptions.db "CREATE TABLE IF NOT EXISTS permission_test (id INTEGER); DROP TABLE IF EXISTS permission_test;" 2>/dev/null; then
                        echo "⚠️ Database write test failed - attempting repair"
                        # Try to fix any corruption or permission issues
                        chown "$target_uid:$target_gid" /app/instance/subscriptions.db*
                        chmod 664 /app/instance/subscriptions.db*
                    else
                        echo "✅ Database write test passed"
                    fi
                else
                    echo "ℹ️ sqlite3 not available for testing, will test in Python"
                fi
                
                # Fix WAL and SHM files if they exist
                for ext in wal shm; do
                    if [ -f "/app/instance/subscriptions.db-$ext" ]; then
                        chown "$target_uid:$target_gid" "/app/instance/subscriptions.db-$ext"
                        chmod 664 "/app/instance/subscriptions.db-$ext"
                        echo "✅ Fixed permissions for subscriptions.db-$ext"
                    fi
                done
            else
                echo "📝 Database file doesn't exist yet - will be created with proper permissions"
            fi
        else
            echo "👤 Running as non-root user: $(id)"
            
            # Test write capability
            if [ ! -w "/app/instance" ]; then
                echo "❌ ERROR: /app/instance is not writable by current user $(id -u):$(id -g)"
                echo "Current directory permissions:"
                ls -la /app/instance 2>/dev/null || ls -la /app/
                echo ""
                echo "🔧 To fix this issue, run on the host:"
                echo "   sudo chown -R $(id -u):$(id -g) ./data"
                echo "   chmod 755 ./data"
                echo "   docker-compose restart"
                exit 1
            fi
            
            # Test actual write capability
            if ! touch "/app/instance/write_test" 2>/dev/null; then
                echo "❌ ERROR: Cannot write to /app/instance directory"
                exit 1
            else
                rm -f "/app/instance/write_test"
                echo "✅ Write test passed for /app/instance"
            fi
            
            # Check database file permissions if it exists
            if [ -f "/app/instance/subscriptions.db" ]; then
                if [ ! -w "/app/instance/subscriptions.db" ]; then
                    echo "❌ ERROR: Database file exists but is not writable"
                    ls -la /app/instance/subscriptions.db
                    echo ""
                    echo "🔧 To fix this issue, run on the host:"
                    echo "   sudo chown $(id -u):$(id -g) ./data/subscriptions.db"
                    echo "   chmod 664 ./data/subscriptions.db"
                    echo "   docker-compose restart"
                    exit 1
                else
                    echo "✅ Database file is writable"
                fi
            fi
        fi
    fi
    
    echo "✅ Directory setup completed successfully"
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

# Initialize database with proper permissions and comprehensive self-fixing
init_database() {
    # Only run database initialization if we're starting the main application
    if [[ "$1" == *"python"* ]] || [[ "$1" == *"gunicorn"* ]] || [[ "$1" == *"run.py"* ]]; then
        echo "🗄️ Initializing database with self-fixing capabilities..."
        
        # Use PUID/GUID if provided, otherwise use build-time defaults
        local target_uid="${PUID:-1000}"
        local target_gid="${GUID:-1000}"
        
        # Create database directory if it doesn't exist
        mkdir -p /app/instance
        
        # Set proper permissions for database operations
        if [ "$(id -u)" = "0" ]; then
            echo "🔧 Root privileges available - performing comprehensive database setup"
            
            # Set directory ownership using PUID/GUID
            chown "$target_uid:$target_gid" /app/instance
            chmod 755 /app/instance
            echo "✅ Set /app/instance ownership to $target_uid:$target_gid"
            
            # Handle database file creation and permissions
            local db_file="/app/instance/subscriptions.db"
            
            if [ -f "$db_file" ]; then
                echo "📝 Existing database found - fixing permissions"
                
                # Fix ownership and permissions
                chown "$target_uid:$target_gid" "$db_file"
                chmod 664 "$db_file"
                
                # Comprehensive database repair and test
                echo "🔍 Testing database integrity and write capability..."
                
                # Test as the target user
                if sudo -u "#$target_uid" python3 -c "
import sqlite3
import sys
try:
    conn = sqlite3.connect('$db_file')
    conn.execute('CREATE TABLE IF NOT EXISTS permission_test (id INTEGER PRIMARY KEY)')
    conn.execute('INSERT INTO permission_test DEFAULT VALUES')
    conn.execute('DELETE FROM permission_test')
    conn.execute('DROP TABLE permission_test')
    conn.commit()
    conn.close()
    print('✅ Database write test PASSED')
except Exception as e:
    print(f'❌ Database write test FAILED: {e}')
    sys.exit(1)
" 2>/dev/null; then
                    echo "✅ Database is fully functional"
                else
                    echo "⚠️ Database write test failed - attempting repair"
                    
                    # Try to fix any WAL mode issues
                    sudo -u "#$target_uid" python3 -c "
import sqlite3
try:
    conn = sqlite3.connect('$db_file')
    conn.execute('PRAGMA journal_mode=DELETE')
    conn.execute('VACUUM')
    conn.close()
    print('🔧 Database repair attempted')
except Exception as e:
    print(f'⚠️ Database repair failed: {e}')
" 2>/dev/null || true
                    
                    # Final permission fix
                    chown "$target_uid:$target_gid" "$db_file"*
                    chmod 664 "$db_file"*
                fi
            else
                echo "📝 No existing database - will be created with proper permissions"
                
                # Pre-create database with correct ownership
                sudo -u "#$target_uid" python3 -c "
import sqlite3
import os
db_path = '$db_file'
if not os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    conn.execute('CREATE TABLE IF NOT EXISTS init_test (id INTEGER)')
    conn.execute('DROP TABLE init_test')
    conn.commit()
    conn.close()
    os.chmod(db_path, 0o664)
    print('📝 Database pre-created with proper permissions')
" 2>/dev/null || echo "ℹ️ Database will be created by application"
            fi
            
            # Handle WAL and SHM files
            for ext in wal shm; do
                local aux_file="${db_file}-${ext}"
                if [ -f "$aux_file" ]; then
                    chown "$target_uid:$target_gid" "$aux_file"
                    chmod 664 "$aux_file"
                    echo "✅ Fixed permissions for $(basename "$aux_file")"
                fi
            done
            
        else
            # Running as non-root - perform thorough validation
            echo "👤 Non-root mode - validating permissions for user $(id)"
            
            if [ ! -w "/app/instance" ]; then
                echo "❌ CRITICAL ERROR: /app/instance is not writable"
                echo "Current permissions:"
                ls -la /app/instance 2>/dev/null || ls -la /app/
                echo ""
                echo "🔧 SOLUTION: Run these commands on your host:"
                echo "   docker-compose down"
                echo "   sudo chown -R $(id -u):$(id -g) ./data"
                echo "   chmod 755 ./data"
                echo "   docker-compose up -d"
                exit 1
            fi
            
            # Test write capability thoroughly
            local test_file="/app/instance/write_test_$(date +%s)"
            if ! touch "$test_file" 2>/dev/null; then
                echo "❌ CRITICAL ERROR: Cannot create files in /app/instance"
                exit 1
            else
                rm -f "$test_file"
                echo "✅ Directory write test passed"
            fi
            
            # Validate database file if it exists
            if [ -f "/app/instance/subscriptions.db" ]; then
                if [ ! -w "/app/instance/subscriptions.db" ]; then
                    echo "❌ CRITICAL ERROR: Database file is not writable"
                    ls -la /app/instance/subscriptions.db
                    echo ""
                    echo "🔧 SOLUTION: Run these commands on your host:"
                    echo "   sudo chown $(id -u):$(id -g) ./data/subscriptions.db"
                    echo "   chmod 664 ./data/subscriptions.db"
                    exit 1
                else
                    echo "✅ Database file is writable"
                    
                    # Test database operations
                    python3 -c "
import sqlite3
import sys
try:
    conn = sqlite3.connect('/app/instance/subscriptions.db')
    conn.execute('CREATE TABLE IF NOT EXISTS permission_test (id INTEGER)')
    conn.execute('DROP TABLE permission_test')
    conn.commit()
    conn.close()
    print('✅ Database functionality test PASSED')
except Exception as e:
    print(f'❌ Database functionality test FAILED: {e}')
    sys.exit(1)
" || exit 1
                fi
            else
                echo "📝 Database will be created by the application"
            fi
        fi
        
        echo "✅ Database initialization completed successfully"
    fi
}

# Validate database file after application starts
validate_database() {
    if [[ "$1" == *"python"* ]] || [[ "$1" == *"gunicorn"* ]] || [[ "$1" == *"run.py"* ]]; then
        # Give the application a moment to start and potentially create the database
        sleep 3
        
        echo "🔍 Post-startup database validation..."
        
        if [ -f "/app/instance/subscriptions.db" ]; then
            if [ -w "/app/instance/subscriptions.db" ]; then
                echo "✅ Database file exists and is writable"
                
                # Quick functionality test
                if python3 -c "
import sqlite3
import sys
try:
    conn = sqlite3.connect('/app/instance/subscriptions.db')
    conn.execute('SELECT name FROM sqlite_master WHERE type=\"table\" LIMIT 1')
    conn.close()
    print('✅ Database is functional')
except Exception as e:
    print(f'⚠️ Database issue: {e}')
" 2>/dev/null; then
                    echo "🎉 Database validation passed!"
                else
                    echo "⚠️ Database may have issues, but continuing..."
                fi
            else
                echo "❌ Database file exists but is not writable!"
                ls -la /app/instance/subscriptions.db
                echo "💡 This may cause 'read-only database' errors"
            fi
        else
            echo "ℹ️ Database file not yet created (normal for first run)"
        fi
    fi
}

# Main execution
main() {
    echo "🚀 Starting Subscription Tracker..."
    echo "Initial user: $(id -u):$(id -g)"
    
    # Handle PUID/GUID mapping first
    setup_user_mapping
    
    # Set up required directories and environment
    ensure_writable_dirs
    setup_temp_dirs
    
    # Initialize database with proper permissions
    init_database "$@"
    
    # Determine execution method based on current state
    if is_user_directive; then
        echo "👤 User directive mode: Running directly as $(id -u):$(id -g)"
        # Start validation in background
        (sleep 5 && validate_database "$@") &
        exec "$@"
        
    elif should_drop_privileges; then
        echo "🔽 Dropping privileges to ${APP_USER}:${APP_GROUP}"
        # Start validation in background
        (sleep 5 && validate_database "$@") &
        exec gosu ${APP_USER}:${APP_GROUP} "$@"
        
    else
        echo "▶️ Running with current user privileges $(id -u):$(id -g)"
        # Start validation in background
        (sleep 5 && validate_database "$@") &
        exec "$@"
    fi
}

# Run main function
main "$@"
