from dataclasses import dataclass

import httpx

from .config import Settings


@dataclass
class ProxyResult:
    enabled: bool
    data: dict


class NginxProxyManager:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = httpx.Client(base_url=settings.npm_url.rstrip("/"), timeout=30)
        self.token: str | None = None

    def login(self) -> None:
        response = self.client.post(
            "/api/tokens",
            json={"identity": self.settings.npm_email, "secret": self.settings.npm_password},
        )
        response.raise_for_status()
        self.token = response.json()["token"]

    def headers(self) -> dict[str, str]:
        if not self.token:
            self.login()
        return {"Authorization": f"Bearer {self.token}"}

    def create_proxy_host(self, domain: str, forward_port: int) -> dict:
        payload = {
            "domain_names": [domain],
            "forward_scheme": self.settings.npm_scheme,
            "forward_host": self.settings.npm_forward_host,
            "forward_port": forward_port,
            "access_list_id": 0,
            "certificate_id": "new",
            "ssl_forced": self.settings.npm_ssl_forced,
            "caching_enabled": False,
            "block_exploits": True,
            "allow_websocket_upgrade": True,
            "http2_support": True,
            "hsts_enabled": False,
            "hsts_subdomains": False,
            "meta": {"letsencrypt_agree": True, "dns_challenge": False},
            "advanced_config": "",
            "locations": [],
        }
        response = self.client.post("/api/nginx/proxy-hosts", headers=self.headers(), json=payload)
        response.raise_for_status()
        return response.json()


def configure_proxy(project: dict, settings: Settings) -> ProxyResult:
    if not settings.npm_enabled:
        return ProxyResult(enabled=False, data={})
    npm = NginxProxyManager(settings)
    domain = project["api_url"].split("://", 1)[1]
    host = npm.create_proxy_host(domain, project["kong_http_port"])
    return ProxyResult(enabled=True, data={"api_proxy_host": host})
