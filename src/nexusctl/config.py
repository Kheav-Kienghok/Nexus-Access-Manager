from __future__ import annotations

import os
import shlex
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from .errors import UsageError

EXTRA_KEYS = ("NEW_ADMIN_PASSWORD",)


def default_env_files():
    return [Path.home() / ".config" / "nexusctl" / "env", Path(".env")]


def parse_env_file(path):
    values = {}
    for raw in Path(path).read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key.startswith("export "):
            key = key[7:].strip()
        try:
            parts = shlex.split(value.strip(), comments=True)
            value = parts[0] if parts else ""
        except ValueError:
            value = value.strip()
        values[key] = value
    return values


def truthy(value):
    return str(value or "").strip().lower() in ("1", "true", "yes", "on")


def _int(values, key, default):
    raw = values.get(key)
    if raw in (None, ""):
        return default
    try:
        return int(raw)
    except ValueError:
        raise UsageError("%s must be a number, got %r" % (key, raw))


@dataclass
class Config:
    url: str = ""
    admin_user: str = "admin"
    admin_password: str | None = None
    insecure: bool = False
    cacert: str | None = None
    resolve: str | None = None
    pull_repo: str = "docker-all"
    push_repo: str = "docker-hosted"
    pypi_repo: str = "pypi-all"
    pull_port: int = 5000
    push_port: int = 5002
    email_domain: str = "example.com"

    @property
    def scheme(self):
        return urlsplit(self.url).scheme

    @property
    def host(self):
        return urlsplit(self.url).hostname or ""

    @property
    def port(self):
        explicit = urlsplit(self.url).port
        if explicit:
            return explicit
        return 443 if self.scheme == "https" else 80

    @property
    def base_path(self):
        return urlsplit(self.url).path.rstrip("/")

    def validate(self):
        if self.scheme not in ("http", "https") or not self.host:
            raise UsageError(
                "set NEXUS_URL (or --url), for example https://nexus.example.com"
            )


def load_config(env_file=None, environ=None, overrides=None):
    environ = os.environ if environ is None else environ
    merged = {}
    files = [Path(env_file)] if env_file else default_env_files()
    for path in files:
        if path.is_file():
            merged.update(parse_env_file(path))
        elif env_file:
            raise UsageError("env file not found: %s" % path)
    for key, value in environ.items():
        if key.startswith("NEXUS_") or key in EXTRA_KEYS:
            merged[key] = value

    cfg = Config(
        url=merged.get("NEXUS_URL", "").rstrip("/"),
        admin_user=merged.get("NEXUS_ADMIN_USER") or "admin",
        admin_password=merged.get("NEXUS_ADMIN_PASSWORD")
        or merged.get("NEW_ADMIN_PASSWORD")
        or None,
        insecure=truthy(merged.get("NEXUS_INSECURE")),
        cacert=merged.get("NEXUS_CACERT") or None,
        resolve=merged.get("NEXUS_RESOLVE") or None,
        pull_repo=merged.get("NEXUS_PULL_REPO") or "docker-all",
        push_repo=merged.get("NEXUS_PUSH_REPO") or "docker-hosted",
        pypi_repo=merged.get("NEXUS_PYPI_REPO") or "pypi-all",
        pull_port=_int(merged, "NEXUS_PULL_PORT", 5000),
        push_port=_int(merged, "NEXUS_PUSH_PORT", 5002),
        email_domain=merged.get("NEXUS_EMAIL_DOMAIN") or "example.com",
    )
    for key, value in (overrides or {}).items():
        if value is not None:
            setattr(cfg, key, value)
    cfg.url = cfg.url.rstrip("/")
    return cfg
