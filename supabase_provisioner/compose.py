import os
import shutil
import subprocess
from pathlib import Path

from .config import Settings
from .security import random_base64, random_hex, random_password, random_urlsafe


class CommandError(RuntimeError):
    def __init__(self, command: list[str], cwd: Path, output: str):
        super().__init__(f"Command failed in {cwd}: {' '.join(command)}\n{output}")
        self.command = command
        self.cwd = cwd
        self.output = output


def run(command: list[str], cwd: Path, env: dict[str, str] | None = None, timeout: int = 600) -> str:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    proc = subprocess.run(
        command,
        cwd=cwd,
        env=merged_env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
        check=False,
    )
    if proc.returncode != 0:
        raise CommandError(command, cwd, proc.stdout)
    return proc.stdout


def ensure_supabase_source(settings: Settings) -> Path:
    repo_dir = settings.supabase_cache_dir / "supabase"
    if not repo_dir.exists():
        run(
            [
                settings.git_bin,
                "clone",
                "--depth",
                "1",
                "--filter=blob:none",
                "--sparse",
                "--branch",
                settings.supabase_git_ref,
                settings.supabase_repo_url,
                str(repo_dir),
            ],
            settings.supabase_cache_dir,
            timeout=1200,
        )
        run([settings.git_bin, "sparse-checkout", "set", "docker"], repo_dir, timeout=600)
    else:
        lock_files = list((repo_dir / ".git").glob("*.lock"))
        if lock_files:
            raise RuntimeError(f"Supabase source cache is locked by another git process: {', '.join(str(path) for path in lock_files)}")
        run([settings.git_bin, "fetch", "--depth", "1", "--filter=blob:none", "origin", settings.supabase_git_ref], repo_dir, timeout=1200)
        run([settings.git_bin, "checkout", "FETCH_HEAD"], repo_dir)
        run([settings.git_bin, "sparse-checkout", "set", "docker"], repo_dir, timeout=600)
    docker_dir = repo_dir / "docker"
    if not (docker_dir / "docker-compose.yml").exists():
        raise FileNotFoundError(f"Supabase docker-compose.yml not found in {docker_dir}")
    return docker_dir


def copy_supabase_template(settings: Settings, target_dir: Path) -> None:
    source = ensure_supabase_source(settings)
    if target_dir.exists():
        raise FileExistsError(f"Project directory already exists: {target_dir}")
    shutil.copytree(source, target_dir)
    example = target_dir / ".env.example"
    env_file = target_dir / ".env"
    if example.exists() and not env_file.exists():
        shutil.copy2(example, env_file)


def generate_project_secrets() -> dict[str, str]:
    return {
        "postgres_password": random_password(40),
        "jwt_secret": random_urlsafe(64),
        "dashboard_username": "supabase-admin",
        "dashboard_password": random_password(28),
        "secret_key_base": random_hex(64),
        "vault_enc_key": random_base64(32)[:32],
        "pooler_tenant_id": random_urlsafe(16).replace("-", "").replace("_", "")[:16],
    }


def parse_env_file(env_path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not env_path.exists():
        return values
    for raw in env_path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value.strip().strip('"').strip("'")
    return values


def upsert_env_file(env_path: Path, values: dict[str, str]) -> None:
    existing: dict[str, str] = {}
    order: list[str] = []
    if env_path.exists():
        for raw in env_path.read_text().splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            existing[key] = value
            order.append(key)
    existing.update(values)
    seen: set[str] = set()
    lines: list[str] = []
    for key in order + list(values.keys()):
        if key in seen:
            continue
        seen.add(key)
        if key in existing:
            lines.append(f"{key}={existing[key]}")
    env_path.write_text("\n".join(lines) + "\n")


SUPABASE_SERVICES = [
    "studio",
    "kong",
    "auth",
    "rest",
    "realtime",
    "storage",
    "imgproxy",
    "meta",
    "functions",
    "analytics",
    "db",
    "vector",
    "supavisor",
]


def write_override(
    project_dir: Path,
    slug: str,
    gotrue_image_override: str = "",
) -> None:
    lines = ["services:"]
    for service in SUPABASE_SERVICES:
        lines.extend(
            [
                f"  {service}:",
                f"    container_name: sb-{slug}-{service}",
            ]
        )
        if service == "auth" and gotrue_image_override:
            lines.append(f"    image: {gotrue_image_override}")
        if service == "supavisor":
            lines.extend(
                [
                    "    ports: !override",
                    "      - ${POOLER_PROXY_PORT_TRANSACTION}:6543",
                ]
            )
    lines.extend(
        [
            "",
        ]
    )
    content = "\n".join(lines)
    (project_dir / "docker-compose.override.yml").write_text(content)


def write_local_ports_env(project_dir: Path, ports: tuple[int, int, int, int]) -> None:
    kong_http, kong_https, _pooler_session, pooler_transaction = ports
    upsert_env_file(
        project_dir / ".env",
        {
            "KONG_HTTP_PORT": str(kong_http),
            "KONG_HTTPS_PORT": str(kong_https),
            "POOLER_PROXY_PORT_TRANSACTION": str(pooler_transaction),
        },
    )


def disable_kong_dashboard_basic_auth(project_dir: Path) -> None:
    kong_config = project_dir / "volumes" / "api" / "kong.yml"
    if not kong_config.exists():
        return
    text = kong_config.read_text()
    text = text.replace(
        """    plugins:
      - name: cors
      - name: basic-auth
        config:
          hide_credentials: true
""",
        """    plugins:
      - name: cors
""",
        1,
    )
    kong_config.write_text(text)


def configure_supabase_project(project: dict, settings: Settings) -> None:
    project_dir = Path(project["base_dir"])
    secrets = project["secrets"]
    env_values = {
        "POSTGRES_PASSWORD": secrets["postgres_password"],
        "JWT_SECRET": secrets["jwt_secret"],
        "DASHBOARD_USERNAME": secrets["dashboard_username"],
        "DASHBOARD_PASSWORD": secrets["dashboard_password"],
        "SECRET_KEY_BASE": secrets["secret_key_base"],
        "VAULT_ENC_KEY": secrets["vault_enc_key"],
        "POOLER_TENANT_ID": secrets["pooler_tenant_id"],
        "SUPABASE_PUBLIC_URL": project["api_url"],
        "API_EXTERNAL_URL": project["api_url"],
        "SITE_URL": project["api_url"],
        "ENABLE_EMAIL_AUTOCONFIRM": "true",
        "STUDIO_DEFAULT_ORGANIZATION": "Self Hosted",
        "STUDIO_DEFAULT_PROJECT": project["name"],
        "DOCKER_SOCKET_LOCATION": "/var/run/docker.sock",
    }
    upsert_env_file(project_dir / ".env", env_values)
    write_local_ports_env(
        project_dir,
        (
            project["kong_http_port"],
            project["kong_https_port"],
            project["pooler_session_port"],
            project["pooler_transaction_port"],
        ),
    )
    disable_kong_dashboard_basic_auth(project_dir)
    write_override(
        project_dir,
        project["slug"],
        settings.gotrue_image_override,
    )
    utils = project_dir / "utils"
    generate = utils / "generate-keys.sh"
    add_new = utils / "add-new-auth-keys.sh"
    if generate.exists():
        run(["sh", str(generate), "--update-env"], project_dir)
    if add_new.exists():
        run(["sh", str(add_new), "--update-env"], project_dir)
    env_after = parse_env_file(project_dir / ".env")
    for env_key, secret_key in {
        "POSTGRES_PASSWORD": "postgres_password",
        "JWT_SECRET": "jwt_secret",
        "DASHBOARD_USERNAME": "dashboard_username",
        "DASHBOARD_PASSWORD": "dashboard_password",
        "SECRET_KEY_BASE": "secret_key_base",
        "VAULT_ENC_KEY": "vault_enc_key",
        "POOLER_TENANT_ID": "pooler_tenant_id",
    }.items():
        if env_after.get(env_key):
            project["secrets"][secret_key] = env_after[env_key]
    for env_key, secret_key in {
        "ANON_KEY": "anon_key",
        "SERVICE_ROLE_KEY": "service_role_key",
        "SUPABASE_PUBLISHABLE_KEY": "supabase_publishable_key",
        "SUPABASE_SECRET_KEY": "supabase_secret_key",
    }.items():
        if env_after.get(env_key):
            project["secrets"][secret_key] = env_after[env_key]


def compose(project: dict, settings: Settings, args: list[str], timeout: int = 900) -> str:
    env = {"COMPOSE_PROJECT_NAME": project["compose_project"]}
    return run([settings.docker_bin, "compose", *args], Path(project["base_dir"]), env=env, timeout=timeout)


def start_project(project: dict, settings: Settings) -> str:
    return compose(project, settings, ["up", "-d"], timeout=1200)


def stop_project(project: dict, settings: Settings) -> str:
    return compose(project, settings, ["down"], timeout=900)


def project_status(project: dict, settings: Settings) -> str:
    return compose(project, settings, ["ps"], timeout=120)


def pull_project(project: dict, settings: Settings) -> str:
    return compose(project, settings, ["pull"], timeout=1800)


def backup_project(project: dict, settings: Settings) -> Path:
    project_dir = Path(project["base_dir"])
    backup_dir = project_dir / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = __import__("datetime").datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    sql_path = backup_dir / f"{project['slug']}-{stamp}-pg_dump.sql"
    storage_path = backup_dir / f"{project['slug']}-{stamp}-storage.tar.gz"
    sql = compose(
        project,
        settings,
        ["exec", "-T", "db", "pg_dump", "--clean", "--if-exists", "--no-owner", "--no-acl", "-U", "supabase_admin", "-d", "postgres"],
        timeout=1800,
    )
    sql_path.write_text(sql)
    storage_dir = project_dir / "volumes" / "storage"
    if storage_dir.exists():
        run(["tar", "-czf", str(storage_path), "-C", str(storage_dir), "."], project_dir, timeout=1800)
    return backup_dir


def restore_project(project: dict, settings: Settings, sql_backup: Path, storage_backup: Path | None = None) -> str:
    project_dir = Path(project["base_dir"])
    if not sql_backup.exists() or not sql_backup.is_file():
        raise FileNotFoundError(f"SQL backup not found: {sql_backup}")
    output = start_project(project, settings)
    sql = sql_backup.read_text()
    proc = subprocess.run(
        [settings.docker_bin, "compose", "exec", "-T", "db", "psql", "-v", "ON_ERROR_STOP=1", "-U", "supabase_admin", "-d", "postgres"],
        cwd=project_dir,
        input=sql,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env={**os.environ, "COMPOSE_PROJECT_NAME": project["compose_project"]},
        timeout=1800,
        check=False,
    )
    if proc.returncode != 0:
        raise CommandError([settings.docker_bin, "compose", "exec", "-T", "db", "psql"], project_dir, proc.stdout)
    output += proc.stdout
    if storage_backup:
        storage_dir = project_dir / "volumes" / "storage"
        storage_dir.mkdir(parents=True, exist_ok=True)
        output += run(["tar", "-xzf", str(storage_backup), "-C", str(storage_dir)], project_dir, timeout=1800)
    return output
