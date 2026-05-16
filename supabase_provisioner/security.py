import base64
import re
import secrets
import string


SLUG_RE = re.compile(r"^[a-z][a-z0-9-]{1,38}[a-z0-9]$")


def validate_slug(slug: str) -> str:
    normalized = slug.strip().lower()
    if not SLUG_RE.fullmatch(normalized):
        raise ValueError("Slug must be 3-40 chars, lowercase, start with a letter, and contain only letters, numbers, and hyphens.")
    if "--" in normalized:
        raise ValueError("Slug must not contain repeated hyphens.")
    return normalized


def random_urlsafe(length: int = 48) -> str:
    return secrets.token_urlsafe(length)[:length]


def random_password(length: int = 32) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def random_hex(bytes_len: int = 32) -> str:
    return secrets.token_hex(bytes_len)


def random_base64(bytes_len: int = 32) -> str:
    return base64.urlsafe_b64encode(secrets.token_bytes(bytes_len)).decode("ascii").rstrip("=")


def compose_project_name(slug: str) -> str:
    return f"sb_{slug.replace('-', '_')}"
