# Self-hosted Supabase Proxmox Provisioner

This is a local control plane for creating isolated self-hosted Supabase projects without Supabase Cloud.

It provisions one official Supabase Docker Compose stack per project. Each project gets its own directory, Docker Compose project name, Docker network, host ports, generated secrets, `.env`, storage volume, database volume, backup folder, and optional Nginx Proxy Manager proxy hosts.

## Current Audit

Observed through Proxmox API:

- Node: `pve`
- Existing LXC 122: `supabase-database-server`
- IP: `192.168.1.43`
- Type: unprivileged Debian LXC
- Resources: 3 cores, 8192 MiB RAM, 20 GiB root disk
- Features: `keyctl=1,nesting=1`
- Purpose: PostgreSQL-only server
- Backups found: none
- Snapshots found: none listed

LXC 122 is not treated as a full Supabase project because it does not run the required Docker Compose services: Studio, Kong, Auth, PostgREST, Realtime, Storage, Edge Runtime, Logflare, Vector, Supavisor, and Postgres.

The Proxmox command policy blocked in-container shell audit commands, and direct SSH from this workspace failed host-key verification. Fix SSH before attempting in-place migration or detailed DB inspection.

## Architecture

Recommended deployment:

- Keep LXC 122 untouched until it is backed up and intentionally migrated.
- Create a separate Docker host for Supabase stacks, preferably a VM or a privileged/nested Docker LXC with enough disk.
- Run this control plane on that Docker host or another trusted internal host with Docker access.
- Put Nginx Proxy Manager in front of browser-facing endpoints.
- Do not publish raw Postgres ports publicly. Use Supavisor internally or via VPN only when needed.

Per project:

- Directory: `${PROJECTS_DIR}/{slug}`
- Compose project: `sb_{slug}`
- Official Supabase Docker files copied from a pinned Supabase git ref
- Generated `.env`
- Generated `docker-compose.override.yml` with project-specific ports
- Backup directory: `${PROJECTS_DIR}/{slug}/backups`
- API URL: `https://{slug}.{BASE_DOMAIN}`
- Studio URL: same gateway URL by default, protected by Supabase Studio basic auth and optionally by NPM access lists

## Quick Start

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[test]"
cp .env.example .env
uvicorn supabase_provisioner.main:app --host 0.0.0.0 --port 8080
```

Open `http://<control-plane-host>:8080`.

For local testing, leave `Start now` unchecked when creating projects. This generates isolated Supabase project directories, secrets, `.env` files, Compose overrides, metadata, and ports without pulling/running the full Docker stack. Use the project detail page's `Start` action when you want to run a stack.

## Docker Quick Start

The container includes Python dependencies, Git, Docker CLI, and the Docker Compose v2 plugin. It controls sibling Supabase stacks through the host Docker socket.

```bash
cp .env.example .env
sudo mkdir -p /opt/supabase-provisioner/{data,projects,supabase-cache}
docker compose up -d --build
```

Open `http://<control-plane-host>:8080`.

Before creating real projects, edit `.env` and change at least `CONTROL_PLANE_PASSWORD`, `SESSION_SECRET`, `BASE_DOMAIN`, and `BIND_ADDRESS`. If you do not want to use `/opt/supabase-provisioner`, set `DATA_DIR`, `PROJECTS_DIR`, and `SUPABASE_CACHE_DIR` to absolute host paths and keep the same values inside the container. This is required because generated Supabase stacks use bind mounts through the host Docker daemon.

Useful Docker commands:

```bash
docker compose logs -f provisioner
docker compose exec provisioner docker version
docker compose down
```

## Required Host Tools

The host running this service must have:

- Docker Engine
- Access to `/var/run/docker.sock` from the provisioner container
- Enough disk for every project's Postgres and storage volumes

## Nginx Proxy Manager

Set these in `.env` if you want automatic proxy host creation:

```dotenv
NPM_URL=http://192.168.1.x:81
NPM_EMAIL=admin@example.com
NPM_PASSWORD=change-me
NPM_SCHEME=http
NPM_FORWARD_HOST=192.168.1.x
NPM_SSL_FORCED=true
```

If NPM runs in a different LXC than the Docker host, set `BIND_ADDRESS=0.0.0.0` or the Docker host LAN IP and restrict access with firewall rules so only NPM can reach the generated project ports.

## Security Notes

- The service generates unique JWT secrets, database passwords, Studio credentials, and key material per project.
- `service_role` / secret keys are shown only in the project details view and should never be placed in frontend code.
- Deletes require typing the project slug.
- Upgrades should always run after a backup.
- Use HTTPS for every browser-facing proxy host.
