from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Supabase Provisioner"
    data_dir: Path = Path("./data")
    projects_dir: Path = Path("./projects")
    supabase_cache_dir: Path = Path("./supabase-cache")
    supabase_repo_url: str = "https://github.com/supabase/supabase.git"
    supabase_git_ref: str = "master"
    base_domain: str = "supabase.internal"
    public_scheme: str = "https"
    bind_address: str = "127.0.0.1"
    initial_port: int = 18000
    docker_bin: str = "docker"
    git_bin: str = "git"
    control_plane_username: str = "admin"
    control_plane_password: str = Field(default="change-this-password", repr=False)
    session_secret: str = Field(default="local-dev-session-secret-change-me", repr=False)

    npm_url: str = ""
    npm_email: str = ""
    npm_password: str = Field(default="", repr=False)
    npm_scheme: str = "http"
    npm_forward_host: str = "127.0.0.1"
    npm_ssl_forced: bool = True
    gotrue_image_override: str = ""

    @property
    def db_path(self) -> Path:
        return self.data_dir / "control-plane.sqlite3"

    @property
    def npm_enabled(self) -> bool:
        return bool(self.npm_url and self.npm_email and self.npm_password)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.data_dir = settings.data_dir.expanduser().resolve()
    settings.projects_dir = settings.projects_dir.expanduser().resolve()
    settings.supabase_cache_dir = settings.supabase_cache_dir.expanduser().resolve()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.projects_dir.mkdir(parents=True, exist_ok=True)
    settings.supabase_cache_dir.mkdir(parents=True, exist_ok=True)
    return settings
