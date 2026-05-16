#!/bin/sh
set -eu

runtime_dirs="${DATA_DIR:-/opt/supabase-provisioner/data} ${PROJECTS_DIR:-/opt/supabase-provisioner/projects} ${SUPABASE_CACHE_DIR:-/opt/supabase-provisioner/supabase-cache}"

for dir in $runtime_dirs; do
    mkdir -p "$dir"
done

if [ -S /var/run/docker.sock ]; then
    socket_gid="$(stat -c '%g' /var/run/docker.sock 2>/dev/null || true)"
    if [ -n "$socket_gid" ]; then
        if ! getent group "$socket_gid" >/dev/null 2>&1; then
            groupadd --gid "$socket_gid" docker-host
        fi
        socket_group="$(getent group "$socket_gid" | cut -d: -f1 | head -n 1)"
        usermod -aG "$socket_group" app
    fi
fi

for dir in $runtime_dirs; do
    chown -R app:app "$dir" 2>/dev/null || true
done

exec gosu app "$@"
