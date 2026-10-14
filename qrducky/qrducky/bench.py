"""Calibration harness (W2.4) — `qr-ducky bench`.

Orchestrates the P0 replay rig (lab/rig/, phase/p0-foundations) over serial to
measure, per target VM: replay duration, effective CPS and keystroke-event
counts for calibration sweeps. The serial protocol is **P0's published rig
protocol** (lab/rig/README.md): 115200 baud, LF-terminated lines, SESSION /
PREFIX / SUFFIX / CPS / JITTER setup, then BEGIN → ≤47-byte fragments with
stop-and-wait `ACK` flow control → `END`. The framing logic mirrors
lab/rig/send_payload.py deliberately — one protocol, no second invention.

Two operating modes:
- ``--dry-run`` (no deps, exit 0): emits the exact protocol conversation for
  every repeat — verifiable without hardware.
- live (default): requires ``serial_port`` in the target's ``[bench.targets]``
  config AND the ``qrducky[bench]`` extra (pyserial); either missing is a
  structured, documented boundary (exit 3).

Calibration capture slots the human fills in physically: attach the rig
(serial port), focus the target VM (PREFIX GUI r opens Run), then run live.
"""

import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .config import Config, ConfigError, bench_target

CHUNK_MAX = 47          # rig firmware fragment limit (lab/rig/send_payload.py)
READ_TIMEOUT = 120.0    # ACK waits while the rig types at low cps

class BenchError(ValueError):
    pass

class BenchNotImplemented(NotImplementedError):
    """Live mode boundary: rig (serial_port) or pyserial unavailable (exit 3)."""

    def __init__(self, target: str, reason: str):
        self.target = target
        self.reason = reason
        super().__init__(
            f"bench for target {target!r} reached the W2.4 live boundary: "
            f"{reason}. Live calibration needs (1) serial_port = \"<rig port>\" "
            f"in [bench.targets.{target}] with the rig attached and "
            f"(2) pip install qrducky[bench] (pyserial). Use --dry-run to "
            f"verify the rig protocol conversation without hardware.")

def iter_fragments(payload: str):
    """Yield <=47-byte fragments; never yield 'END' (streaming terminator).

    Same framing rule as lab/rig/send_payload.py — kept in sync deliberately.
    """
    i = 0
    while i < len(payload):
        frag = payload[i:i + CHUNK_MAX]
        if frag == "END":
            frag = payload[i:i + 2]      # split "END" across two fragments
            if len(frag) < 2:            # degenerate tail
                frag = "E" + payload[i + 1:i + 2]
        yield frag
        i += len(frag)

class RigChannel:
    """Serial channel mirroring lab/rig/send_payload.py's SerialPort:
    pyserial when live, protocol-conversation echo when dry-run."""

    def __init__(self, port: Optional[str], baud: int = 115200,
                 dry_run: bool = False, target: str = "target"):
        self.dry_run = dry_run
        self.conversation: List[str] = []   # protocol transcript
        self.events: List[dict] = []        # contract-#1 JSONL events (live)
        if dry_run:
            return
        if not port:
            raise BenchNotImplemented(target, "no serial_port configured")
        try:
            import serial  # pyserial — optional extra qrducky[bench]
        except ImportError as e:
            raise BenchNotImplemented(
                target,
                "pyserial not installed (pip install qrducky[bench])") from e
        self.ser = serial.Serial(port, baud, timeout=1.0)
        time.sleep(2.0)  # Pro Micro CDC needs a moment after open

    def send(self, line: str) -> None:
        self.conversation.append("> " + line)
        if not self.dry_run:
            self.ser.write((line + "\n").encode("utf-8"))
            self.ser.flush()

    def read_line(self, expected: str, timeout: float = READ_TIMEOUT) -> str:
        """Wait for a line starting with `expected`; tee JSONL events."""
        if self.dry_run:
            reply = "< DRY " + expected
            self.conversation.append(reply)
            return reply
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            raw = self.ser.readline()
            if not raw:
                continue
            line = raw.decode("utf-8", "replace").rstrip("\r\n")
            if line.startswith("{"):
                self.conversation.append("< " + line)
                try:
                    self.events.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
            elif line.startswith("ERR"):
                raise BenchError("rig error: " + line)
            elif line.startswith(expected):
                self.conversation.append("< " + line)
                return line
        raise BenchError(f"timeout waiting for {expected!r}")

    def close(self) -> None:
        if not self.dry_run:
            self.ser.close()

@dataclass
class BenchResult:
    target: str
    repeat: int
    dry_run: bool
    payload: str
    cps: int
    jitter_ms: int
    runs: List[Dict[str, Any]] = field(default_factory=list)
    conversation: List[str] = field(default_factory=list)
    events: List[dict] = field(default_factory=list)

def _resolve_payload(cfg: Config, target: str, entry: Dict[str, Any],
                     payload_arg: Optional[str]) -> str:
    """Explicit payload only — no implicit calibration payload (GX.2 posture)."""
    path = payload_arg or entry.get("payload")
    if not path:
        raise ConfigError(
            f"bench target {target!r}: no payload. Pass --payload <file> or "
            f"set payload = \"<path>\" in [bench.targets.{target}] "
            f"(no implicit payloads exist)")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except OSError as e:
        raise ConfigError(f"bench payload {path!r}: {e}") from e

def run_bench(cfg: Config, target: str, repeat: Optional[int] = None,
              payload_arg: Optional[str] = None,
              dry_run: bool = False) -> BenchResult:
    """One calibration run: repeat the rig replay and collect JSONL stats."""
    entry = bench_target(cfg, target)  # ConfigError if undeclared
    repeat = int(repeat or cfg.bench.get("default_repeat", 5))
    if repeat < 1:
        raise ConfigError("--repeat must be >= 1")
    payload = _resolve_payload(cfg, target, entry, payload_arg)
    cps = int(entry.get("cps", 20))
    jitter = int(entry.get("jitter_ms", 15))
    if not 1 <= cps <= 200:
        raise ConfigError(f"bench target {target!r}: cps must be 1..200")

    port = entry.get("serial_port")  # CAPTURE SLOT: human fills when rig attached
    rig = RigChannel(port, baud=int(entry.get("baud", 115200)),
                     dry_run=dry_run, target=target)

    result = BenchResult(target=target, repeat=repeat, dry_run=dry_run,
                         payload=payload, cps=cps, jitter_ms=jitter)
    try:
        for n in range(1, repeat + 1):
            session = f"bench-{target}-{n:03d}"
            rig.send(f"SESSION {session}")
            rig.read_line("OK")
            rig.send("PREFIX GUI r")       # Win+R engagement window
            rig.read_line("OK")
            rig.send("SUFFIX ENTER")
            rig.read_line("OK")
            rig.send(f"CPS {cps}")
            rig.read_line("OK")
            rig.send(f"JITTER {jitter}")
            rig.read_line("OK")
            rig.send("BEGIN")              # chunked streaming per P0 protocol
            rig.read_line("OK")
            frag_count = 0
            for frag in iter_fragments(payload):
                rig.send(frag)
                frag_count += 1
                rig.read_line("ACK")       # stop-and-wait flow control
            rig.send("END")
            rig.read_line("OK")
            run_events = rig.events[len(rig.events):]
            result.runs.append({
                "session": session,
                "fragments": frag_count,
                "keystroke_events": len(run_events),
            })
        result.conversation = list(rig.conversation)
        result.events = list(rig.events)
    finally:
        rig.close()
    return result

def bench_stats(result: BenchResult) -> Dict[str, Any]:
    """Summarize calibration output (meaningful once live JSONL exists)."""
    ts = [e.get("ts_ms") for e in result.events if "ts_ms" in e]
    stats: Dict[str, Any] = {
        "target": result.target,
        "repeat": result.repeat,
        "dry_run": result.dry_run,
        "cps": result.cps,
        "jitter_ms": result.jitter_ms,
        "payload_bytes": len(result.payload.encode("utf-8")),
        "total_events": len(result.events),
        "runs": result.runs,
    }
    if len(ts) >= 2:
        stats["duration_ms"] = ts[-1] - ts[0]
        stats["effective_cps"] = round(
            len(result.events) / max((ts[-1] - ts[0]) / 1000.0, 0.001), 1)
    return stats