import os
import shutil
import ssl
import subprocess
import tempfile
import unittest

from .helpers import NexusCase


@unittest.skipUnless(shutil.which("openssl"), "openssl not installed")
class TlsTests(NexusCase):
    def setUp(self):
        super().setUp()
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        self.cert = os.path.join(tmp, "cert.pem")
        key = os.path.join(tmp, "key.pem")
        subprocess.run(
            ["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "2",
             "-subj", "/CN=nexus.example.invalid", "-addext", "subjectAltName=DNS:nexus.example.invalid",
             "-keyout", key, "-out", self.cert],
            check=True, capture_output=True,
        )
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(self.cert, key)
        self.fake.server.socket = ctx.wrap_socket(self.fake.server.socket, server_side=True)
        port = self.url.rsplit(":", 1)[1]
        self.env["NEXUS_URL"] = "https://nexus.example.invalid:%s" % port
        self.env["NEXUS_RESOLVE"] = "127.0.0.1"

    def test_untrusted_certificate_is_refused(self):
        code, _, err = self.run_cli("check")
        self.assertEqual(code, 1)
        self.assertIn("TLS failed", err)

    def test_insecure_flag_connects(self):
        code, out, _ = self.run_cli("check", "--insecure")
        self.assertEqual(code, 0, out)

    def test_cacert_verifies_the_name_even_with_resolve(self):
        code, out, _ = self.run_cli("check", "--cacert", self.cert)
        self.assertEqual(code, 0, out)

    def test_cacert_with_wrong_name_fails(self):
        self.env["NEXUS_URL"] = self.env["NEXUS_URL"].replace("nexus.example.invalid", "other.example.invalid")
        code, _, err = self.run_cli("check", "--cacert", self.cert)
        self.assertEqual(code, 1)
        self.assertIn("TLS failed", err)


if __name__ == "__main__":
    unittest.main()
