"""L1–L3 sim-path tests — DEFINED NOW, honestly skipped until Xcode exists.

AUTHORIZATION — LAB ONLY (docs/governance/policy.md §1/§7).

These tests are the DEFINITION OF DONE for the Xcode-later physical slot
(ARCHITECTURE.md §6): once Xcode is installed on this Mac, they run unmodified
and the rig is done when they are green. Until then every test skips with the
reason `requires Xcode + simulator runtime (physical slot)` — it does NOT
pass, pretend, or silently vanish.
"""

import re
import subprocess
import time
import unittest

from common import HARNESS, has_simctl, run_script

HAS_SIMCTL = has_simctl()
SIM_SKIP = "requires Xcode + simulator runtime (physical slot)"

EXAMPLE_URL = "http://192.0.2.10:8000/payload.html"  # RFC 5737 doc space
SCHEME_URL = "p6rigdemo://demo?url=http%3A%2F%2F192.0.2.10%3A8000%2Fpayload.html"
MARKER_TIMEOUT_S = 30


def simctl(*args, timeout=60):
    return subprocess.run(["xcrun", "simctl", *args],
                           capture_output=True, text=True, timeout=timeout)


def log_query(dev: str, predicate: str, last: str = "5m") -> str:
    """Snapshot (not stream) of the device unified log."""
    r = subprocess.run(
        ["xcrun", "simctl", "spawn", dev, "log", "show", f"--last", last,
         "--predicate", predicate],
        capture_output=True, text=True, timeout=120)
    return r.stdout or ""


@unittest.skipUnless(HAS_SIMCTL, SIM_SKIP)
class TestSimLifecycle(unittest.TestCase):
    """L1 — list, boot."""

    def test_sim_list_exits_zero(self):
        proc = run_script("sim_list.sh")
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_sim_list_lists_devices_or_reports_none(self):
        proc = run_script("sim_list.sh")
        self.assertTrue(re.search(r"(iPhone|No devices)", proc.stdout),
                        "sim_list must list devices or say none")

    def test_sim_boot_default_and_status(self):
        proc = run_script("sim_boot.sh", timeout=300)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("booted", simctl("list", "devices", "booted").stdout.lower())


@unittest.skipUnless(HAS_SIMCTL, SIM_SKIP)
class TestURLDelivery(unittest.TestCase):
    """L2 — openurl: http control arm + scheme dispatch arm."""

    def test_openurl_http_control_arm(self):
        proc = run_script("open_url.sh", EXAMPLE_URL, timeout=120)
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_openurl_scheme_dispatch_arm(self):
        proc = run_script("open_url.sh", SCHEME_URL, timeout=120)
        self.assertEqual(proc.returncode, 0, proc.stderr)


@unittest.skipUnless(HAS_SIMCTL, SIM_SKIP)
class TestMarkerFlow(unittest.TestCase):
    """L3 — the U→E→C marker timeline on the booted simulator.

    DEFINITION OF DONE for the human's Xcode run: demo app built+installed
    (demo-app/README.md), staging payload served on the lab host, then the
    scheme arm opened. Expected markers (run_manifest.json grammar) must
    appear in order in the device unified log.
    """

    def test_scheme_arm_marker_flow(self):
        self.assertEqual(run_script("open_url.sh", SCHEME_URL,
                                    timeout=120).returncode, 0)
        deadline = time.time() + MARKER_TIMEOUT_S
        log = ""
        while time.time() < deadline:
            time.sleep(5)
            log = log_query("booted", 'eventMessage CONTAINS "P6RIG"')
            if "BRIDGE_CALLBACK sent" in log:
                break
        for marker in ("U stage: loading url=",
                       "BRIDGE_REACHED op=mark tag=stage-e-bridge-reached",
                       "BRIDGE_EXEC done",
                       "BRIDGE_CALLBACK sent"):
            self.assertIn(marker, log, f"marker missing: {marker!r}")

    def test_http_control_arm_is_marker_silent(self):
        self.assertEqual(run_script("open_url.sh", EXAMPLE_URL,
                                    timeout=120).returncode, 0)
        time.sleep(10)
        log = log_query("booted", 'eventMessage CONTAINS "P6RIG"', last="2m")
        self.assertNotIn("BRIDGE_REACHED", log,
                         "control arm (Safari) must not emit bridge markers")


if __name__ == "__main__":
    unittest.main()
