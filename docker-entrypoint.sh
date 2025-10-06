#!/usr/bin/env bash
set -e

# Environment variables: PUID, PGID
PUID=${PUID:-1000}
PGID=${PGID:-1000}
APP_USER=appuser
APP_GROUP=appgroup

# Create group if it does not exist or adjust gid
if getent group ${APP_GROUP} >/dev/null 2>&1; then
    EXISTING_GID=$(getent group ${APP_GROUP} | cut -d: -f3)
    if [ "$EXISTING_GID" != "$PGID" ]; then
        groupmod -o -g "$PGID" "$APP_GROUP" || true
    fi
else
    groupadd -o -g "$PGID" "$APP_GROUP"
fi

# Create user if it does not exist or adjust uid
if id -u ${APP_USER} >/dev/null 2>&1; then
    EXISTING_UID=$(id -u ${APP_USER})
    if [ "$EXISTING_UID" != "$PUID" ]; then
        usermod -o -u "$PUID" ${APP_USER} 2>/dev/null || true
    fi
else
    useradd -o -m -u "$PUID" -g "$PGID" -s /bin/bash ${APP_USER} 2>/dev/null || true
fi

# Ensure instance and other writable dirs exist & permissions
mkdir -p /app/instance
chown -R ${APP_USER}:${APP_GROUP} /app/instance

# Drop privileges and execute
exec gosu ${APP_USER}:${APP_GROUP} "$@"
