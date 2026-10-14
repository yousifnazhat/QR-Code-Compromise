"""L0 guard-path tests — GREEN on a machine WITHOUT Xcode.

AUTHORIZATION — LAB ONLY (docs/governance/policy.md §1/§7).

Every simctl-based harness script, run on a machine without Xcode, must
exit 2 and print the exact install instructions (ARCHITECTURE.md §L0). This
Mac (CommandLineTools only, verified: no simctl) is the red-machine proof, so
these tests RUN and pass here. On a machine WITH Xcode the guard is not
observable, so they skip with an explicit reason (portable by design).

Static-contract tests (syntax, banners, manifest grammar) run everywhere.
"""

import json
import subprocess
import unittest

from common import (HARNESS, HARNESS_SCRIPTS, INSTALL_INSTRUCTION_MARKERS,
                   IOS_RIG, has_simctl, read, run_script)

NO_XCODE = not has_simctl()
GUARD_SKIP = "guard path only observable without Xcode (this test IS the no-Xcode machine)"
EXAMPLE_URL = "http://192.0.2.10:8000/payload.html"  # RFC 5737 doc space (policy §2)


@unittest.skipUnless(NO_XCODE, GUARD_SKIP)
class TestGuardPaths(unittest.TestCase):
    """(a) acceptance criteria: every script exits 2 with install instructions."""

    def _assert_guard(self, proc, name):
        self.assertEqual(proc.returncode, 2,
                         f"{name}: expected exit 2, got {proc.returncode}")
        blob = proc.stderr + proc.stdout
        for marker in INSTALL_INSTRUCTION_MARKERS:
            self.assertIn(marker, blob, f"{name}: missing instruction {marker!r}")

    def test_sim_list_guard(self):
        self._assert_guard(run_script("sim_list.sh"), "sim_list.sh")

    def test_sim_boot_guard(self):
        self._assert_guard(run_script("sim_boot.sh"), "sim_boot.sh")

    def test_open_url_guard(self):
        self._assert_guard(run_script("open_url.sh", EXAMPLE_URL), "open_url.sh")

    def test_capture_logs_guard(self):
        self._assert_guard(run_script("capture_logs.sh"), "capture_logs.sh")

    def test_open_url_usage_error(self):
        proc = run_script("open_url.sh")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("usage:", proc.stderr)


class TestStaticContracts(unittest.TestCase):
    """Contracts that hold on ANY machine (green now, stay green)."""

    def test_scripts_pass_bash_n(self):
        for name in HARNESS_SCRIPTS:
            r = subprocess.run(["bash", "-n", str(HARNESS / name)],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, f"{name}: bash -n failed: {r.stderr}")

    def test_scripts_carry_lab_only_banner(self):
        for name in HARNESS_SCRIPTS:
            self.assertIn("LAB ONLY", read(HARNESS / name), f"{name}: banner missing")

    def test_run_manifest_is_valid_json(self):
        data = json.loads(read(HARNESS / "run_manifest.json"))
        for key in ("chain", "steps", "expected_log_markers",
                    "control_arm_expected", "listener", "policy"):
            self.assertIn(key, data)

    def test_marker_grammar_consistent_across_manifest_app_and_page(self):
        """The marker grammar must be identical in manifest, demo app, page."""
        manifest = read(HARNESS / "run_manifest.json")
        vc = read(IOS_RIG / "demo-app" / "P6RigDemo" / "ViewController.swift")
        page = read(IOS_RIG / "staging" / "payload.example.html")
        for core in ("U stage: loading url=",
                     "BRIDGE_REACHED op=mark tag=",
                     "BRIDGE_EXEC cmd=",
                     "BRIDGE_EXEC done",
                     "BRIDGE_CALLBACK target=",
                     "BRIDGE_CALLBACK sent"):
            self.assertIn(core, vc, f"ViewController missing marker core {core!r}")
            self.assertIn(core, manifest, f"manifest missing marker core {core!r}")
        # the page posts exactly the ops the handler implements
        for op in ('op: "mark"', 'op: "exec"', 'op: "callback"'):
            self.assertIn(op, page)

    def test_listener_reuse_not_duplicated(self):
        """L4 must REUSE the OS-agnostic stub, not fork a second listener."""
        self.assertTrue(
            (IOS_RIG / ".." / "rig" / "harness" / "listener_stub.py").exists())
        ios_py = [p.name for p in IOS_RIG.rglob("*.py") if "tests" not in p.parts]
        self.assertNotIn("listener_stub.py", ios_py,
                         "iOS rig must not duplicate listener_stub.py")


if __name__ == "__main__":
    unittest.main()
