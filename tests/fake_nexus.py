import base64
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlsplit

BUILTIN_PRIVILEGE_PREFIX = "nx-"


class FakeNexus:
    def __init__(self, user="admin", password="secret"):
        self.user = user
        self.password = password
        self.selectors = {}
        self.privileges = {}
        self.roles = {}
        self.users = {
            "admin": {"userId": "admin", "firstName": "Administrator", "lastName": "User",
                      "emailAddress": "admin@example.org", "source": "default", "status": "active", "roles": ["nx-admin"]},
            "anonymous": {"userId": "anonymous", "firstName": "Anonymous", "lastName": "User",
                          "emailAddress": "anon@example.org", "source": "default", "status": "active", "roles": ["nx-anonymous"]},
        }
        self.passwords = {}
        self.repositories = [
            {"name": "docker-all", "format": "docker", "type": "group"},
            {"name": "docker-hosted", "format": "docker", "type": "hosted"},
            {"name": "pypi-all", "format": "pypi", "type": "group"},
        ]
        self.realms = ["NexusAuthenticatingRealm", "NexusAuthorizingRealm", "DockerToken"]
        self.requests = []
        self.server = None

    def start(self):
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def _send(self, status, payload=None):
                body = b""
                if payload is not None:
                    body = json.dumps(payload).encode() if not isinstance(payload, str) else payload.encode()
                self.send_response(status)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def _body(self):
                length = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(length).decode() if length else ""
                if self.headers.get("Content-Type", "").startswith("text/plain"):
                    return raw
                return json.loads(raw) if raw else None

            def _handle(self, method):
                auth = self.headers.get("Authorization", "")
                expected = "Basic " + base64.b64encode(("%s:%s" % (fake.user, fake.password)).encode()).decode()
                if auth != expected:
                    return self._send(401, "unauthorized")
                parts = urlsplit(self.path)
                path = parts.path
                query = parse_qs(parts.query)
                prefix = "/service/rest/v1"
                if not path.startswith(prefix):
                    return self._send(404, "not found")
                path = path[len(prefix):]
                body = self._body() if method in ("POST", "PUT") else None
                fake.requests.append((method, path))
                status, payload = fake.route(method, path, query, body)
                self._send(status, payload)

            def do_GET(self):
                self._handle("GET")

            def do_POST(self):
                self._handle("POST")

            def do_PUT(self):
                self._handle("PUT")

            def do_DELETE(self):
                self._handle("DELETE")

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        return "http://127.0.0.1:%d" % self.server.server_address[1]

    def stop(self):
        self.server.shutdown()
        self.server.server_close()

    def _privilege_known(self, name):
        return name in self.privileges or name.startswith(BUILTIN_PRIVILEGE_PREFIX)

    def _roles_known(self, roles):
        return all(r in self.roles or r.startswith("nx-") for r in roles)

    def route(self, method, path, query, body):
        segments = [unquote(s) for s in path.strip("/").split("/")]

        if path == "/status":
            return 200, None
        if path == "/repositories" and method == "GET":
            return 200, self.repositories
        if path == "/security/realms/active" and method == "GET":
            return 200, self.realms

        if segments[:2] == ["security", "content-selectors"]:
            if len(segments) == 2 and method == "GET":
                return 200, list(self.selectors.values())
            if len(segments) == 2 and method == "POST":
                if body["name"] in self.selectors:
                    return 400, "exists"
                self.selectors[body["name"]] = body
                return 204, None
            if len(segments) == 3 and method == "DELETE":
                return (204, None) if self.selectors.pop(segments[2], None) else (404, "missing")

        if segments[:2] == ["security", "privileges"]:
            if len(segments) == 2 and method == "GET":
                return 200, list(self.privileges.values())
            if segments[2:] == ["repository-content-selector"] and method == "POST":
                if body["name"] in self.privileges:
                    return 400, "exists"
                if body["contentSelector"] not in self.selectors:
                    return 400, "unknown selector"
                if not set(body["actions"]) <= {"BROWSE", "READ", "EDIT", "ADD", "DELETE"}:
                    return 400, "bad action"
                self.privileges[body["name"]] = body
                return 201, None
            if len(segments) == 3 and method == "DELETE":
                return (204, None) if self.privileges.pop(segments[2], None) else (404, "missing")

        if segments[:2] == ["security", "roles"]:
            if len(segments) == 2 and method == "GET":
                return 200, list(self.roles.values())
            if len(segments) == 2 and method == "POST":
                if body["id"] in self.roles:
                    return 400, "exists"
                if not all(self._privilege_known(p) for p in body["privileges"]):
                    return 400, "unknown privilege"
                self.roles[body["id"]] = body
                return 200, body
            if len(segments) == 3 and method == "PUT":
                if segments[2] not in self.roles:
                    return 404, "missing"
                if not all(self._privilege_known(p) for p in body["privileges"]):
                    return 400, "unknown privilege"
                self.roles[segments[2]] = body
                return 204, None
            if len(segments) == 3 and method == "DELETE":
                return (204, None) if self.roles.pop(segments[2], None) else (404, "missing")

        if segments[:2] == ["security", "users"]:
            if len(segments) == 2 and method == "GET":
                return 200, list(self.users.values())
            if len(segments) == 2 and method == "POST":
                if body["userId"] in self.users:
                    return 400, "exists"
                if not self._roles_known(body["roles"]):
                    return 400, "unknown role"
                if len(body["password"]) < 8:
                    return 400, "weak password"
                self.passwords[body["userId"]] = body["password"]
                stored = {k: v for k, v in body.items() if k != "password"}
                stored["source"] = "default"
                self.users[body["userId"]] = stored
                return 200, stored
            if len(segments) == 3 and method == "PUT":
                if segments[2] not in self.users:
                    return 404, "missing"
                if not self._roles_known(body["roles"]):
                    return 400, "unknown role"
                self.users[segments[2]].update({k: v for k, v in body.items() if k != "password"})
                return 204, None
            if len(segments) == 3 and method == "DELETE":
                return (204, None) if self.users.pop(segments[2], None) else (404, "missing")
            if len(segments) == 4 and segments[3] == "change-password" and method == "PUT":
                if segments[2] not in self.users:
                    return 404, "missing"
                self.passwords[segments[2]] = body
                return 204, None
        return 404, "not found: %s %s" % (method, path)
