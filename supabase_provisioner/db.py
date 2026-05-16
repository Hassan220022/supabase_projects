import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class ControlDB:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def migrate(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    slug TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    compose_project TEXT NOT NULL UNIQUE,
                    base_dir TEXT NOT NULL,
                    api_url TEXT NOT NULL,
                    studio_url TEXT NOT NULL,
                    kong_http_port INTEGER NOT NULL UNIQUE,
                    kong_https_port INTEGER NOT NULL UNIQUE,
                    pooler_session_port INTEGER NOT NULL UNIQUE,
                    pooler_transaction_port INTEGER NOT NULL UNIQUE,
                    secrets_json TEXT NOT NULL,
                    proxy_json TEXT NOT NULL DEFAULT '{}',
                    last_error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS operation_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_slug TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    status TEXT NOT NULL,
                    message TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(project_slug) REFERENCES projects(slug) ON DELETE CASCADE
                );
                """
            )

    def next_port_block(self, initial_port: int) -> tuple[int, int, int, int]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT kong_http_port, kong_https_port, pooler_session_port, pooler_transaction_port FROM projects"
            ).fetchall()
        used = {port for row in rows for port in row}
        port = initial_port
        while True:
            block = (port, port + 1, port + 2, port + 3)
            if not any(candidate in used for candidate in block):
                return block
            port += 10

    def create_project(self, project: dict[str, Any]) -> None:
        now = utcnow()
        values = {
            **project,
            "secrets_json": json.dumps(project["secrets"], sort_keys=True),
            "proxy_json": json.dumps(project.get("proxy", {}), sort_keys=True),
            "created_at": now,
            "updated_at": now,
        }
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO projects (
                    slug, name, status, compose_project, base_dir, api_url, studio_url,
                    kong_http_port, kong_https_port, pooler_session_port, pooler_transaction_port,
                    secrets_json, proxy_json, created_at, updated_at
                ) VALUES (
                    :slug, :name, :status, :compose_project, :base_dir, :api_url, :studio_url,
                    :kong_http_port, :kong_https_port, :pooler_session_port, :pooler_transaction_port,
                    :secrets_json, :proxy_json, :created_at, :updated_at
                )
                """,
                values,
            )

    def update_project(self, slug: str, **fields: Any) -> None:
        if not fields:
            return
        fields["updated_at"] = utcnow()
        if "secrets" in fields:
            fields["secrets_json"] = json.dumps(fields.pop("secrets"), sort_keys=True)
        if "proxy" in fields:
            fields["proxy_json"] = json.dumps(fields.pop("proxy"), sort_keys=True)
        assignments = ", ".join(f"{key} = :{key}" for key in fields)
        fields["slug"] = slug
        with self.connect() as conn:
            conn.execute(f"UPDATE projects SET {assignments} WHERE slug = :slug", fields)

    def get_project(self, slug: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM projects WHERE slug = ?", (slug,)).fetchone()
        return self._decode(row) if row else None

    def list_projects(self) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM projects ORDER BY created_at DESC").fetchall()
        return [self._decode(row) for row in rows]

    def delete_project_record(self, slug: str) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM projects WHERE slug = ?", (slug,))

    def log(self, slug: str, operation: str, status: str, message: str) -> None:
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO operation_logs (project_slug, operation, status, message, created_at) VALUES (?, ?, ?, ?, ?)",
                (slug, operation, status, message[-8000:], utcnow()),
            )

    def logs(self, slug: str, limit: int = 100) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM operation_logs WHERE project_slug = ? ORDER BY id DESC LIMIT ?",
                (slug, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def _decode(row: sqlite3.Row) -> dict[str, Any]:
        data = dict(row)
        data["secrets"] = json.loads(data.pop("secrets_json"))
        data["proxy"] = json.loads(data.pop("proxy_json"))
        return data
