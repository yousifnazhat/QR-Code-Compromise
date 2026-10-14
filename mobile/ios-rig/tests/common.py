"""Shared helpers for the P6 iOS rig test suite.

AUTHORIZATION — LAB ONLY (docs/governance/policy.md §1/§7). Stdlib-only test
infrastructure: green-able tests (L0 guard, L4 listener) run on any machine;
sim-path tests skip with an explicit reason until the Xcode physical slot is
filled. See mobile/ios-rig/ARCHITECTURE.md §6.
"""

import shutil
import subprocess
from pathlib import Path

# repo root = mobile/ios-rig/tests/ -> up three
REPO_ROOT = Path(__file__).resolve().parents[3]
IOS_RIG = REPO_ROOT / "mobile" / "ios-rig"
HARNESS = IOS_RIG / "harness"
LISTENER = REPO_ROOT / "mobile" / "rig" / "harness" / "listener_stub.py"

HARNESS_SCRIPTS = [
    "sim_list.sh",
    "sim_boot.sh",
    "open_url.sh",
    "capture_logs.sh",
]

INSTALL_INSTRUCTION_MARKERS = [
    "xcode-select --switch /Applications/Xcode.app/Contents/Developer",
    "xcodebuild -runFirstLaunch",
    "developer.apple.com/xcode",
]


def has_simctl() -> bool:
    """True iff xcrun simctl is usable (i.e., Xcode is installed)."""
    try:
        r = subprocess.run(
            ["xcrun", "simctl", "help"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
        return r.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def run_script(name: str, *args, timeout: int = 60):
    """Run a harness script; return CompletedProcess."""
    return subprocess.run(
        ["bash", str(HARNESS / name), *args],
        capture_output=True, text=True, timeout=timeout)


def free_port() -> int:
    """Grab an OS-assigned free TCP port (bind(0), then close)."""
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


__all__ = [
    "REPO_ROOT", "IOS_RIG", "HARNESS", "LISTENER", "HARNESS_SCRIPTS",
    "INSTALL_INSTRUCTION_MARKERS", "has_simctl", "run_script", "free_port",
    "read", "shutil", "subprocess", "Path",
]
