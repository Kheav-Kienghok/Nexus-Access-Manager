from __future__ import annotations

import base64
import http.client
import json
import socket
import ssl
from urllib.parse import quote

from .errors import NexusError

API = "/service/rest/v1"


class _HTTPS(http.client.HTTPSConnection):
    def __init__(self, host, port, resolve, ctx, timeout):
        super().__init__(host, port, timeout=timeout, context=ctx)
        self._resolve = resolve
        self._ctx = ctx

    def connect(self):
        sock = socket.create_connection((self._resolve or self.host, self.port), self.timeout)
        self.sock = self._ctx.wrap_socket(sock, server_hostname=self.host)


class _HTTP(http.client.HTTPConnection):
    def __init__(self, host, port, resolve, timeout):
        super().__init__(host, port, timeout=timeout)
        self._resolve = resolve

    def connect(self):
        self.sock = socket.create_connection((self._resolve or self.host, self.port), self.timeout)


def _tls_context(cfg):
    if cfg.insecure:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx
    if cfg.cacert:
        return ssl.create_default_context(cafile=cfg.cacert)
    return ssl.create_default_context()


def _q(value):
    return quote(value, safe="")


class NexusClient:
    def __init__(self, cfg, timeout=30):
        cfg.validate()
        self.cfg = cfg
        self.timeout = timeout
        token = "%s:%s" % (cfg.admin_user, cfg.admin_password or "")
        self._auth = "Basic " + base64.b64encode(token.encode()).decode()

    def _connect(self):
        cfg = self.cfg
        if cfg.scheme == "https":
            return _HTTPS(cfg.host, cfg.port, cfg.resolve, _tls_context(cfg), self.timeout)
        return _HTTP(cfg.host, cfg.port, cfg.resolve, self.timeout)

    def request(self, method, path, body=None):
        headers = {"Authorization": self._auth, "Accept": "application/json"}
        data = None
        if isinstance(body, str):
            data = body.encode()
            headers["Content-Type"] = "text/plain"
        elif body is not None:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        url = self.cfg.base_path + API + path
        conn = self._connect()
        try:
            conn.request(method, url, body=data, headers=headers)
            resp = conn.getresponse()
            raw = resp.read().decode("utf-8", "replace")
        finally:
            conn.close()
        if resp.status >= 400:
            raise NexusError(resp.status, raw.strip()[:300], path)
        if not raw.strip():
            return None
        try:
            return json.loads(raw)
        except ValueError:
            return raw

    def status(self):
        return self.request("GET", "/status")

    def repositories(self):
        return self.request("GET", "/repositories") or []

    def realms(self):
        return self.request("GET", "/security/realms/active") or []

    def selectors(self):
        return self.request("GET", "/security/content-selectors") or []

    def create_selector(self, body):
        self.request("POST", "/security/content-selectors", body)

    def delete_selector(self, name):
        self.request("DELETE", "/security/content-selectors/" + _q(name))

    def privileges(self):
        return self.request("GET", "/security/privileges") or []

    def create_privilege(self, body):
        self.request("POST", "/security/privileges/repository-content-selector", body)

    def delete_privilege(self, name):
        self.request("DELETE", "/security/privileges/" + _q(name))

    def roles(self):
        return self.request("GET", "/security/roles") or []

    def create_role(self, body):
        self.request("POST", "/security/roles", body)

    def update_role(self, role_id, body):
        self.request("PUT", "/security/roles/" + _q(role_id), body)

    def delete_role(self, role_id):
        self.request("DELETE", "/security/roles/" + _q(role_id))

    def users(self):
        return self.request("GET", "/security/users?source=default") or []

    def create_user(self, body):
        self.request("POST", "/security/users", body)

    def update_user(self, user_id, body):
        self.request("PUT", "/security/users/" + _q(user_id), body)

    def delete_user(self, user_id):
        self.request("DELETE", "/security/users/" + _q(user_id))

    def change_password(self, user_id, password):
        self.request("PUT", "/security/users/%s/change-password" % _q(user_id), password)


def user_update_body(raw, roles):
    return {
        "userId": raw["userId"],
        "firstName": raw.get("firstName", ""),
        "lastName": raw.get("lastName", ""),
        "emailAddress": raw.get("emailAddress", ""),
        "source": raw.get("source", "default"),
        "status": raw.get("status", "active"),
        "roles": list(roles),
    }
