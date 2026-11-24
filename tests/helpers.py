import io as _io
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from nexusctl import flows
from nexusctl.cli import main
from nexusctl.config import Config
from nexusctl.util import IO

from .fake_nexus import FakeNexus


class Scripted:
    def __init__(self, answers):
        self.answers = list(answers)
        self.prompts = []

    def ask(self, prompt):
        self.prompts.append(prompt)
        if not self.answers:
            raise EOFError
        return self.answers.pop(0)


class NexusCase(unittest.TestCase):
    def setUp(self):
        self.fake = FakeNexus()
        self.url = self.fake.start()
        self.addCleanup(self.fake.stop)
        self.env = {"NEXUS_URL": self.url, "NEXUS_ADMIN_PASSWORD": "secret"}

    def cfg(self):
        return Config(url=self.url, admin_password="secret", pull_port=5000, push_port=5002)

    def ctx(self, answers=None, assume_yes=False):
        script = Scripted(answers) if answers is not None else None
        out, err = _io.StringIO(), _io.StringIO()
        io = IO(stdout=out, stderr=err, ask_fn=script.ask if script else None,
                secret_fn=(lambda prompt: "pw-from-prompt") if script else None)
        ctx = flows.build_context(self.cfg(), io, assume_yes=assume_yes)
        ctx.script, ctx.out, ctx.err = script, out, err
        return ctx

    def run_cli(self, *argv, stdin=None, answers=None):
        out, err = _io.StringIO(), _io.StringIO()
        script = Scripted(answers) if answers is not None else None
        io = IO(stdin=_io.StringIO(stdin or ""), stdout=out, stderr=err,
                ask_fn=script.ask if script else None,
                secret_fn=(lambda prompt: "pw-from-prompt") if script else None)
        old = {k: os.environ.get(k) for k in self.env}
        os.environ.update(self.env)
        try:
            code = main(list(argv), io=io)
        finally:
            for k, v in old.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
        return code, out.getvalue(), err.getvalue()
