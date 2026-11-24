"""Environment-only service configuration; secrets are never model fields."""

import os
from dataclasses import dataclass, field
from urllib.parse import urlsplit

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    token: str = field(repr=False)
    host: str = "127.0.0.1"
    port: int = 8001
    recipe_base_url: str = ""
    allowed_hosts: tuple[str, ...] = ()
    allowed_origins: tuple[str, ...] = ()

    def __post_init__(self):
        if len(self.token) < 32 or not self.token.isascii() or any(c.isspace() for c in self.token):
            raise ValueError("MCP_API_TOKEN must contain at least 32 non-whitespace ASCII characters")
        if self.host not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("MCP_HOST must be loopback; use an authenticated proxy or Secure MCP Tunnel")
        if not 1 <= self.port <= 65535:
            raise ValueError("MCP_PORT must be between 1 and 65535")
        if self.recipe_base_url:
            value = urlsplit(self.recipe_base_url)
            if (value.scheme not in {"http", "https"} or not value.hostname
                    or value.username is not None or value.password is not None
                    or value.query or value.fragment):
                raise ValueError("MCP_RECIPE_BASE_URL must be an HTTP(S) URL without credentials, query or fragment")
        if any("*" in value for value in (*self.allowed_hosts, *self.allowed_origins)):
            raise ValueError("MCP allowed hosts and origins must be explicit, without wildcards")

    @classmethod
    def from_env(cls):
        load_dotenv()
        def values(name):
            return tuple(v.strip() for v in os.getenv(name, "").split(",") if v.strip())
        return cls(
            token=os.getenv("MCP_API_TOKEN", ""),
            host=os.getenv("MCP_HOST", "127.0.0.1"),
            port=int(os.getenv("MCP_PORT", "8001")),
            recipe_base_url=os.getenv("MCP_RECIPE_BASE_URL", ""),
            allowed_hosts=values("MCP_ALLOWED_HOSTS"),
            allowed_origins=values("MCP_ALLOWED_ORIGINS"),
        )
