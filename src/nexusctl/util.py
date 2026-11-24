from __future__ import annotations

import getpass
import re
import secrets
import sys

from .errors import Cancelled, UsageError

PROJECT_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")
USER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{1,63}$")
RESERVED_PROJECTS = {"library"}


def validate_project(name):
    if not PROJECT_RE.match(name or ""):
        raise UsageError(
            "project name %r: use lowercase letters, digits and dashes (max 40, start with a letter or digit)" % name
        )
    if name in RESERVED_PROJECTS:
        raise UsageError("project name %r is reserved (it is the Docker Hub official namespace)" % name)
    return name


def validate_username(name):
    if not USER_RE.match(name or ""):
        raise UsageError(
            "username %r: use letters, digits, dot, dash and underscore (2 to 64 characters)" % name
        )
    return name


def generate_password(kind="user"):
    return secrets.token_urlsafe(24 if kind == "robot" else 18)


class IO:
    def __init__(self, stdin=None, stdout=None, stderr=None, ask_fn=None, secret_fn=None):
        self.stdin = stdin or sys.stdin
        self.out = stdout or sys.stdout
        self.err = stderr or sys.stderr
        self._ask = ask_fn
        self._secret = secret_fn

    @property
    def interactive(self):
        if self._ask is not None:
            return True
        try:
            return self.stdin.isatty()
        except (AttributeError, ValueError):
            return False

    def say(self, text=""):
        print(text, file=self.out)

    def error(self, text):
        print(text, file=self.err)

    def ask(self, prompt, default=None):
        suffix = " [%s]" % default if default not in (None, "") else ""
        text = "%s%s: " % (prompt, suffix)
        try:
            value = self._ask(text) if self._ask else input(text)
        except EOFError:
            raise Cancelled("input closed")
        value = (value or "").strip()
        return value or (default or "")

    def secret(self, prompt):
        text = "%s: " % prompt
        try:
            return self._secret(text) if self._secret else getpass.getpass(text)
        except EOFError:
            raise Cancelled("input closed")

    def confirm(self, prompt, default=True):
        hint = "Y/n" if default else "y/N"
        while True:
            answer = self.ask("%s (%s)" % (prompt, hint)).lower()
            if not answer:
                return default
            if answer in ("y", "yes"):
                return True
            if answer in ("n", "no"):
                return False
            self.say("Please answer y or n.")


def table(headers, rows):
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(str(cell)))
    lines = ["  ".join(h.ljust(widths[i]) for i, h in enumerate(headers)).rstrip()]
    lines.append("  ".join("-" * w for w in widths))
    for row in rows:
        lines.append("  ".join(str(c).ljust(widths[i]) for i, c in enumerate(row)).rstrip())
    return "\n".join(lines)
