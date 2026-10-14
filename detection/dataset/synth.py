"""Synthetic keystroke-timing generator (contract-#1 JSONL output).

AUTHORIZATION: lab-only research tooling. Generates synthetic timing
data for detector baselining; no real targets, hosts, or payloads.

Two behavioural classes, per the W4.1 charter:

- human: lognormal inter-arrivals (median ~85 ms, sigma 0.45, bulk
  40-200 ms), occasional thinking pauses (250-900 ms), typo
  corrections (1-3 Backspace presses), small per-key jitter.

- scanner / rig: machine bursts. A per-device fixed base delay drawn
  once from 1.0-9.5 ms with near-zero jitter (<= 0.5 ms), modelling
  the QR-wedge burst profile seen in W0.x/W1.x captures.

All events conform to contract #1. Sessions are independently
identifiable via the ``session`` field and labelled via ``source``.

CLI:
    python3 -m detection.dataset.synth --out sample.jsonl [--seed 42]
        [--human-sessions N] [--scanner-sessions N] [--rig-sessions N]
"""

import argparse
import json
import math
import random
import sys
from typing import Any, Dict, List

# Printable ASCII ranges used for human typing (letters, digits,
# space, punctuation) and payload-like alnum for wedge bursts.
_LETTERS = [c for c in range(0x41, 0x5B)]                 # A-Z
_DIGITS = [c for c in range(0x30, 0x3A)]                   # 0-9
_PUNCT = [0x20, 0x2C, 0x2E, 0x2F, 0x3A, 0x3B, 0x2D, 0x5C]  # space , . / : ; - \
_BACKSPACE = 0x08

_ALNUM = [c for c in range(0x41, 0x5B)] + [c for c in range(0x30, 0x3A)]


def _event(ts_ms: int, event: str, keycode: int, source: str, device: str,
           session: str) -> Dict[str, Any]:
    return {
        "ts_ms": int(ts_ms),
        "event": event,
        "keycode": keycode,
        "source": source,
        "device": device,
        "session": session,
    }


def gen_human_session(rng: random.Random, session: str, n_keys: int,
                      device: str = "kbd-generic-104") -> List[Dict[str, Any]]:
    """One human typing session with realistic inter-arrival structure."""
    events: List[Dict[str, Any]] = []
    ts = rng.randint(1_000_000, 9_000_000)
    remaining = n_keys
    while remaining > 0:
        # A burst of typing (4-12 keys) between micro-pauses.
        for _ in range(min(rng.randint(4, 12), remaining)):
            ia = rng.lognormvariate(math.log(85.0), 0.45)  # median 85 ms
            ia += rng.uniform(-6.0, 6.0)                  # per-key jitter
            ts += max(ia, 8.0)
            pool = _LETTERS * 8 + _DIGITS * 2 + _PUNCT * 3
            events.append(_event(ts, "keydown", rng.choice(pool), "human",
                                device, session))
            remaining -= 1
        # Typo correction: 1-3 backspaces at typing speed.
        if rng.random() < 0.18 and remaining > 3:
            for _ in range(rng.randint(1, 3)):
                ts += max(rng.lognormvariate(math.log(110.0), 0.5), 8.0)
                events.append(_event(ts, "keydown", _BACKSPACE, "human",
                                     device, session))
                remaining -= 1
        # Thinking pause before the next burst.
        ts += rng.uniform(250.0, 900.0)
    return events


def gen_burst_session(rng: random.Random, session: str, n_keys: int,
                      source: str, device: str) -> List[Dict[str, Any]]:
    """One scanner/rig burst session: fixed per-device delay, tiny jitter."""
    base = rng.uniform(1.5, 9.5)      # drawn once per device/session
    jitter = rng.uniform(0.05, 0.35) # near-zero variance (cv <= ~0.14)
    events: List[Dict[str, Any]] = []
    ts = rng.randint(1_000_000, 9_000_000)
    for _ in range(n_keys):
        ts += max(base + rng.uniform(-jitter, jitter), 0.5)
        events.append(_event(ts, "keydown", rng.choice(_ALNUM), source,
                             device, session))
    return events


def generate_dataset(seed: int, human_sessions: int, scanner_sessions: int,
                     rig_sessions: int = 0, min_keys: int = 45,
                     max_keys: int = 120) -> List[Dict[str, Any]]:
    """Generate a complete synthetic dataset (contract-#1 events)."""
    rng = random.Random(seed)
    events: List[Dict[str, Any]] = []

    for i in range(human_sessions):
        n = rng.randint(min_keys, max_keys)
        events.extend(gen_human_session(
            rng, "h-%04d" % i, n,
            device="kbd-%03d" % rng.randint(0, 3)))
    for i in range(scanner_sessions):
        n = rng.randint(min_keys, max_keys)
        events.extend(gen_burst_session(
            rng, "s-%04d" % i, n, "scanner",
            device="synth-scanner-%02d" % rng.randint(0, 5)))
    for i in range(rig_sessions):
        n = rng.randint(min_keys, max_keys)
        events.extend(gen_burst_session(
            rng, "r-%04d" % i, n, "rig",
            device="rig-usb-01"))
    events.sort(key=lambda e: e["ts_ms"])
    return events


def write_jsonl(events: List[Dict[str, Any]], path: str) -> None:
    out = sys.stdout if path == "-" else open(path, "w", encoding="utf-8")
    try:
        for event in events:
            out.write(json.dumps(event, separators=(",", ":")) + "\n")
    finally:
        if out is not sys.stdout:
            out.close()


def main(argv: List[str] = None) -> int:
    ap = argparse.ArgumentParser(
        description="Synthetic contract-#1 keystroke timing generator")
    ap.add_argument("--out", required=True, help="output JSONL path ('-'=stdout)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--human-sessions", type=int, default=20)
    ap.add_argument("--scanner-sessions", type=int, default=20)
    ap.add_argument("--rig-sessions", type=int, default=0)
    ap.add_argument("--min-keys", type=int, default=45)
    ap.add_argument("--max-keys", type=int, default=120)
    args = ap.parse_args(argv)

    events = generate_dataset(
        args.seed, args.human_sessions, args.scanner_sessions,
        args.rig_sessions, args.min_keys, args.max_keys)
    write_jsonl(events, args.out)

    by_source: Dict[str, int] = {}
    for e in events:
        by_source[e["source"]] = by_source.get(e["source"], 0) + 1
    sys.stderr.write(
        "wrote %d events to %s: %s\n"
        % (len(events), args.out, ", ".join(
            "%s=%d" % kv for kv in sorted(by_source.items()))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
