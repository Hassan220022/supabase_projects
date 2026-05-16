# Proxmox Deployment Runbook

## 1. Do Not Reuse LXC 122 As The Platform Host

LXC 122 is a PostgreSQL-only server. Keep it running as-is until it has a verified backup and you decide whether to migrate its data into a newly provisioned Supabase project.

## 2. Create A Docker Host

Use a VM for the cleanest production posture. A nested Docker LXC can work, but Docker-in-LXC has more kernel, AppArmor, overlayfs, and backup edge cases.

Recommended starting resources:

- 8 vCPU
- 16-32 GiB RAM
- 200+ GiB disk on storage with snapshot/backup support
- Static LAN IP
- Docker Engine and Compose v2

If you use LXC, enable nesting and keyctl, and test Docker health before installing this provisioner.

## 3. Install The Control Plane With Docker

The Docker setup runs only this control plane in a container. The Supabase project stacks it creates run as sibling containers on the same Docker host through `/var/run/docker.sock`.

```bash
sudo mkdir -p /opt/supabase-provisioner/{data,projects,supabase-cache}
sudo chown -R root:docker /opt/supabase-provisioner
sudo chmod -R g+rwX /opt/supabase-provisioner
```

Copy this repository onto the Docker host, then:

```bash
cd /path/to/this/repository
cp .env.example .env
```

Edit `.env` before first real project creation. At minimum change `CONTROL_PLANE_PASSWORD`, `SESSION_SECRET`, `BASE_DOMAIN`, `BIND_ADDRESS`, and the Nginx Proxy Manager settings if you want automatic HTTPS proxy creation.

Then start it:

```bash
docker compose up -d --build
docker compose logs -f provisioner
```

Keep `DATA_DIR`, `PROJECTS_DIR`, and `SUPABASE_CACHE_DIR` as absolute host paths mounted at the same absolute paths in the provisioner container. The generated Supabase Compose projects use bind mounts, and the host Docker daemon must be able to see those paths.

## 4. Alternative: Install The Control Plane With Systemd

```bash
sudo useradd --system --create-home --home /opt/supabase-provisioner --shell /usr/sbin/nologin supabase-provisioner
sudo usermod -aG docker supabase-provisioner
sudo mkdir -p /opt/supabase-provisioner/{app,data,projects,supabase-cache}
sudo chown -R supabase-provisioner:supabase-provisioner /opt/supabase-provisioner
```

Copy this repository into `/opt/supabase-provisioner/app`, then:

```bash
cd /opt/supabase-provisioner/app
sudo -u supabase-provisioner python3 -m venv .venv
sudo -u supabase-provisioner .venv/bin/pip install -e ".[test]"
sudo cp .env.example /opt/supabase-provisioner/.env
sudo install -m 0644 deploy/supabase-provisioner.service /etc/systemd/system/supabase-provisioner.service
sudo systemctl daemon-reload
sudo systemctl enable --now supabase-provisioner
```

Edit `/opt/supabase-provisioner/.env` before first real project creation. At minimum change `CONTROL_PLANE_PASSWORD`, `BASE_DOMAIN`, `BIND_ADDRESS`, and the Nginx Proxy Manager settings if you want automatic HTTPS proxy creation.

## 5. Reverse Proxy

Expose only the control plane and generated Kong/API gateway ports through Nginx Proxy Manager.

Do not expose:

- Project Postgres ports
- Docker socket
- Internal control database
- Project `.env` files

When NPM is on a separate host/container, set `BIND_ADDRESS` to the Docker host LAN IP or `0.0.0.0`, then firewall the generated port range so only NPM and trusted admin networks can connect.

## 6. Backups

The provisioner creates logical Postgres backups with `pg_dumpall` and archives `volumes/storage`.

You should also configure host-level backups:

- Proxmox VM/LXC backups for the Docker host
- Off-host copy of `/opt/supabase-provisioner/data`
- Off-host copy of `/opt/supabase-provisioner/projects/*/backups`

Run a backup before every upgrade. The `Backup + Upgrade` action enforces that sequence.

## 7. LXC 122 Migration Path

After SSH access is fixed:

1. Create a Proxmox backup of LXC 122.
2. Run `pg_dumpall` from LXC 122.
3. Create a new Supabase project through this provisioner.
4. Restore the dump into that project's Postgres container.
5. Validate Auth, REST, Storage, and Realtime behavior.
6. Cut apps over to the new API URL.

Do not try to bolt Auth, Kong, Storage, Realtime, and Studio onto LXC 122 in place.
