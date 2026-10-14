"""L4 listener tests — OS-agnostic, GREEN on any machine.

AUTHORIZATION — LAB ONLY (docs/governance/policy.md §1/§7). Exercises the
REUSED Android-rig stub (mobile/rig/harness/listener_stub.py) against real
local TCP sessions: explicit-binding rule, proof-line verification, usage
errors. No default endpoints anywhere (policy §2).
"""

import os
import select
import socket
import subprocess
import sys
import time
import unittest

from common import LISTENER, free_port

PROOF = "P6RIG-SESSION ios=test-host\n"


class ListenerProcess:
    """Context manager: start listener_stub.py, drain its stdout, stop it."""

    def __init__(self, *args):
        self.port = free_port()
        self.args = list(args)
        self.proc = None
        self._buf = ""

    def __enter__(self):
        self.proc = subprocess.Popen(
            [sys.executable, str(LISTENER), "--host", "127.0.0.1",
             "--port", str(self.port), *self.args],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        deadline = time.time() + 10
        while time.time() < deadline:
            self._drain()
            if "listening on" in self._buf:
                break
            if self.proc.poll() is not None:
                break  # exited early; output() shows why
            time.sleep(0.1)
        return self

    def _drain(self):
        while select.select([self.proc.stdout], [], [], 0)[0]:
            chunk = os.read(self.proc.stdout.fileno(), 65536)
            if not chunk:
                break
            self._buf += chunk.decode("utf-8", "replace")

    def output(self) -> str:
        self._drain()
        return self._buf

    def __exit__(self, *exc):
        if self.proc:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
            self.proc.stdout.close()
        return False


class TestListener(unittest.TestCase):

    def test_usage_error_without_host_port(self):
        r = subprocess.run([sys.executable, str(LISTENER)],
                            capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 2, "missing --host/--port must exit 2")

    def test_invalid_port_exits_two(self):
        r = subprocess.run([sys.executable, str(LISTENER), "--host", "127.0.0.1",
                            "--port", "99999"],
                           capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 2)

    def test_session_proof_is_verified(self):
        with ListenerProcess() as lp:
            s = socket.create_connection(("127.0.0.1", lp.port), timeout=5)
            s.sendall(PROOF.encode())
            s.close()
            deadline = time.time() + 10
            out = ""
            while time.time() < deadline:
                out = lp.output()
                if "VERIFIED" in out:
                    break
                time.sleep(0.2)
            self.assertIn("listening on 127.0.0.1:%d" % lp.port, out)
            self.assertIn(PROOF.strip(), out)
            self.assertIn("VERIFIED", out)

    def test_empty_session_not_verified(self):
        with ListenerProcess() as lp:
            s = socket.create_connection(("127.0.0.1", lp.port), timeout=5)
            s.close()
            deadline = time.time() + 15
            out = ""
            while time.time() < deadline:
                out = lp.output()
                if "not verified" in out:
                    break
                time.sleep(0.2)
            self.assertIn("not verified", out)

    def test_listener_carries_lab_only_banner(self):
        src = LISTENER.read_text(encoding="utf-8")
        self.assertIn("LAB ONLY", src)


if __name__ == "__main__":
    unittest.main()
