from pathlib import Path
from shutil import rmtree
from secrets import compare_digest
from threading import Lock
from urllib.parse import urlparse, urlunparse

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from .compose import (
    CommandError,
    backup_project,
    configure_supabase_project,
    copy_supabase_template,
    project_status,
    pull_project,
    restore_project,
    start_project,
    stop_project,
    generate_project_secrets,
    parse_env_file,
)
from .config import Settings, get_settings
from .db import ControlDB
from .proxy import configure_proxy
from .security import compose_project_name, validate_slug


app = FastAPI(title="Supabase Proxmox Provisioner")
app.add_middleware(SessionMiddleware, secret_key=get_settings().session_secret, same_site="lax")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")
provision_lock = Lock()


def settings_dep() -> Settings:
    return get_settings()


def db_dep(settings: Settings = Depends(settings_dep)) -> ControlDB:
    db = ControlDB(settings.db_path)
    db.migrate()
    return db


def require_auth(request: Request) -> str:
    username = request.session.get("username")
    if not username:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    return username


def project_public_url(slug: str, kong_http_port: int, settings: Settings) -> str:
    if settings.npm_enabled:
        return f"{settings.public_scheme}://{slug}.{settings.base_domain}"
    host = "127.0.0.1" if settings.bind_address in {"0.0.0.0", "::"} else settings.bind_address
    return f"http://{host}:{kong_http_port}"


def studio_browser_url(project: dict) -> str:
    """Build the top-level Studio URL after the control-plane project login succeeds."""
    parsed = urlparse(project["studio_url"])
    return urlunparse((parsed.scheme, parsed.netloc, "/project/default", "", "", ""))


def studio_credentials(project: dict) -> tuple[str, str]:
    env_values = parse_env_file(Path(project["base_dir"]) / ".env")
    username = env_values.get("DASHBOARD_USERNAME") or project["secrets"].get("dashboard_username", "")
    password = env_values.get("DASHBOARD_PASSWORD") or project["secrets"].get("dashboard_password", "")
    return username, password


def with_live_studio_credentials(project: dict) -> dict:
    username, password = studio_credentials(project)
    project["secrets"]["dashboard_username"] = username
    project["secrets"]["dashboard_password"] = password
    return project


def flash(request: Request, level: str, message: str) -> None:
    request.session["_flash"] = {"level": level, "message": message}


def pop_flash(request: Request) -> dict | None:
    return request.session.pop("_flash", None)


@app.get("/login", response_class=HTMLResponse)
def login_form(request: Request, settings: Settings = Depends(settings_dep)):
    if request.session.get("username"):
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "settings": settings, "error": None},
    )


@app.post("/login", response_class=HTMLResponse)
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    settings: Settings = Depends(settings_dep),
):
    valid_username = compare_digest(username, settings.control_plane_username)
    valid_password = compare_digest(password, settings.control_plane_password)
    if not (valid_username and valid_password):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "settings": settings, "error": "Invalid username or password."},
            status_code=401,
        )
    request.session["username"] = username
    return RedirectResponse("/", status_code=303)


@app.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


@app.get("/", response_class=HTMLResponse)
def index(request: Request, db: ControlDB = Depends(db_dep), settings: Settings = Depends(settings_dep)):
    if not request.session.get("username"):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "settings": settings, "error": None},
        )
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "projects": db.list_projects(), "settings": settings, "flash": pop_flash(request)},
    )


@app.post("/projects")
def create_project(
    request: Request,
    name: str = Form(...),
    slug: str = Form(...),
    start_now: bool = Form(False),
    _: str = Depends(require_auth),
    db: ControlDB = Depends(db_dep),
    settings: Settings = Depends(settings_dep),
):
    if not provision_lock.acquire(blocking=False):
        flash(request, "error", "Another project is currently provisioning. Try again after it finishes.")
        return RedirectResponse("/", status_code=303)
    try:
        slug = validate_slug(slug)
        if db.get_project(slug):
            raise ValueError("A project with this slug already exists.")
        project_dir = settings.projects_dir / slug
        kong_http, kong_https, pooler_session, pooler_transaction = db.next_port_block(settings.initial_port)
        api_url = project_public_url(slug, kong_http, settings)
        project = {
            "slug": slug,
            "name": name.strip() or slug,
            "status": "provisioning",
            "compose_project": compose_project_name(slug),
            "base_dir": str(project_dir),
            "api_url": api_url,
            "studio_url": api_url,
            "kong_http_port": kong_http,
            "kong_https_port": kong_https,
            "pooler_session_port": pooler_session,
            "pooler_transaction_port": pooler_transaction,
            "secrets": generate_project_secrets(),
            "proxy": {},
        }
        db.create_project(project)
        db.log(slug, "provision", "running", "Copying official Supabase Docker template.")
        copy_supabase_template(settings, project_dir)
        db.log(slug, "provision", "running", "Writing project .env and compose override.")
        configure_supabase_project(project, settings)
        db.update_project(slug, secrets=project["secrets"])
        db.log(slug, "provision", "running", "Creating reverse proxy host if configured.")
        proxy = configure_proxy(project, settings)
        if proxy.enabled:
            db.update_project(slug, proxy=proxy.data)
        if start_now:
            db.log(slug, "provision", "running", "Starting Docker Compose stack.")
            output = start_project(project, settings)
            db.update_project(slug, status="running", last_error=None)
            db.log(slug, "provision", "ok", output or "Project started.")
        else:
            db.update_project(slug, status="created", last_error=None)
            db.log(slug, "provision", "ok", "Project generated. Start it when you are ready.")
    except (ValueError, FileExistsError, FileNotFoundError, CommandError) as exc:
        if "slug" in locals() and db.get_project(slug):
            db.update_project(slug, status="error", last_error=str(exc))
            db.log(slug, "provision", "error", str(exc))
        flash(request, "error", str(exc))
        return RedirectResponse("/", status_code=303)
    finally:
        provision_lock.release()
    return RedirectResponse(f"/projects/{slug}", status_code=303)


@app.get("/projects/{slug}", response_class=HTMLResponse)
def detail(request: Request, slug: str, _: str = Depends(require_auth), db: ControlDB = Depends(db_dep)):
    project = db.get_project(slug)
    if not project:
        raise HTTPException(404)
    project = with_live_studio_credentials(project)
    backup_dir = Path(project["base_dir"]) / "backups"
    backups = sorted([path.name for path in backup_dir.glob("*")], reverse=True) if backup_dir.exists() else []
    return templates.TemplateResponse(
        "detail.html",
        {"request": request, "project": project, "logs": db.logs(slug), "backups": backups, "flash": pop_flash(request)},
    )


@app.get("/projects/{slug}/studio-login", response_class=HTMLResponse)
def studio_login_form(request: Request, slug: str, _: str = Depends(require_auth), db: ControlDB = Depends(db_dep)):
    project = db.get_project(slug)
    if not project:
        raise HTTPException(404)
    project = with_live_studio_credentials(project)
    return templates.TemplateResponse(
        "studio_login.html",
        {"request": request, "project": project, "error": None},
    )


@app.post("/projects/{slug}/studio-login", response_class=HTMLResponse)
def studio_login(
    request: Request,
    slug: str,
    username: str = Form(...),
    password: str = Form(...),
    _: str = Depends(require_auth),
    db: ControlDB = Depends(db_dep),
):
    project = db.get_project(slug)
    if not project:
        raise HTTPException(404)
    project = with_live_studio_credentials(project)
    expected_username = project["secrets"].get("dashboard_username", "")
    expected_password = project["secrets"].get("dashboard_password", "")
    valid_username = compare_digest(username, expected_username)
    valid_password = compare_digest(password, expected_password)
    if not (valid_username and valid_password):
        return templates.TemplateResponse(
            "studio_login.html",
            {"request": request, "project": project, "error": "Invalid Studio username or password."},
            status_code=401,
        )
    request.session[f"studio:{slug}"] = True
    return RedirectResponse(studio_browser_url(project), status_code=303)


@app.post("/projects/{slug}/restore")
def restore(
    request: Request,
    slug: str,
    sql_backup_name: str = Form(""),
    storage_backup_name: str = Form(""),
    confirm_slug: str = Form(""),
    _: str = Depends(require_auth),
    db: ControlDB = Depends(db_dep),
    settings: Settings = Depends(settings_dep),
):
    project = db.get_project(slug)
    if not project:
        raise HTTPException(404)
    if confirm_slug != slug:
        flash(request, "error", "Restore requires exact slug confirmation.")
        return RedirectResponse(f"/projects/{slug}", status_code=303)
    if not sql_backup_name:
        flash(request, "error", "Choose a SQL backup before restoring.")
        return RedirectResponse(f"/projects/{slug}", status_code=303)
    backup_dir = Path(project["base_dir"]) / "backups"
    sql_path = (backup_dir / sql_backup_name).resolve()
    storage_path = (backup_dir / storage_backup_name).resolve() if storage_backup_name else None
    if backup_dir.resolve() not in sql_path.parents:
        flash(request, "error", "SQL backup must be inside the project backup directory.")
        return RedirectResponse(f"/projects/{slug}", status_code=303)
    if storage_path and backup_dir.resolve() not in storage_path.parents:
        flash(request, "error", "Storage backup must be inside the project backup directory.")
        return RedirectResponse(f"/projects/{slug}", status_code=303)
    try:
        out = restore_project(project, settings, sql_path, storage_path)
        db.update_project(slug, status="running", last_error=None)
        db.log(slug, "restore", "ok", out or "Restore completed.")
        flash(request, "success", "Restore completed.")
    except (CommandError, FileNotFoundError) as exc:
        db.update_project(slug, status="error", last_error=str(exc))
        db.log(slug, "restore", "error", str(exc))
        flash(request, "error", f"Restore failed. Check the project logs for details.")
        return RedirectResponse(f"/projects/{slug}", status_code=303)
    return RedirectResponse(f"/projects/{slug}", status_code=303)


@app.get("/projects/{slug}/compose-ps", response_class=PlainTextResponse)
def compose_ps(slug: str, _: str = Depends(require_auth), db: ControlDB = Depends(db_dep), settings: Settings = Depends(settings_dep)):
    project = db.get_project(slug)
    if not project:
        raise HTTPException(404)
    return project_status(project, settings)


@app.post("/projects/{slug}/delete")
def delete_project(
    request: Request,
    slug: str,
    confirm_slug: str = Form(""),
    _: str = Depends(require_auth),
    db: ControlDB = Depends(db_dep),
    settings: Settings = Depends(settings_dep),
):
    project = db.get_project(slug)
    if not project:
        raise HTTPException(404)
    if confirm_slug != slug:
        flash(request, "error", "Deletion requires exact slug confirmation.")
        return RedirectResponse(f"/projects/{slug}", status_code=303)
    try:
        stop_project(project, settings)
    except CommandError as exc:
        db.log(slug, "delete", "warning", exc.output)
    rmtree(project["base_dir"], ignore_errors=False)
    db.delete_project_record(slug)
    flash(request, "success", f"Deleted project {slug}.")
    return RedirectResponse("/", status_code=303)


@app.post("/projects/{slug}/{action}")
def action(request: Request, slug: str, action: str, _: str = Depends(require_auth), db: ControlDB = Depends(db_dep), settings: Settings = Depends(settings_dep)):
    project = db.get_project(slug)
    if not project:
        raise HTTPException(404)
    try:
        if action == "start":
            out = start_project(project, settings)
            db.update_project(slug, status="running", last_error=None)
        elif action == "stop":
            out = stop_project(project, settings)
            db.update_project(slug, status="stopped", last_error=None)
        elif action == "backup":
            out = f"Backup written to {backup_project(project, settings)}"
        elif action == "upgrade":
            backup_project(project, settings)
            out = pull_project(project, settings)
            out += "\n" + start_project(project, settings)
            db.update_project(slug, status="running", last_error=None)
        else:
            flash(request, "error", f"Unsupported action: {action}.")
            return RedirectResponse(f"/projects/{slug}", status_code=303)
        db.log(slug, action, "ok", out or action)
        flash(request, "success", f"{action.title()} completed.")
    except CommandError as exc:
        db.update_project(slug, status="error", last_error=exc.output)
        db.log(slug, action, "error", exc.output)
        flash(request, "error", f"{action.title()} failed. Check the project logs for details.")
        return RedirectResponse(f"/projects/{slug}", status_code=303)
    return RedirectResponse(f"/projects/{slug}", status_code=303)
