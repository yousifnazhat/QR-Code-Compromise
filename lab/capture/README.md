# lab/capture — target-side keystroke capture hook (contract #1)

`capture_keystrokes.py` runs on the target machine and appends one
contract-#1 JSONL event per keydown/keyup:

```json
{"ts_ms":123456,"event":"keydown","keycode":65,"source":"human","device":"capture-host","session":"sess-017"}
```

* `ts_ms` — `time.monotonic_ns() // 1e6`: **host-local monotonic ms**.
  Clocks are per-device (the rig uses `millis()`, the capture host uses its
  own monotonic clock); P4 aligns sessions by onset/order, not wall time.
* `keycode` — USB HID usage id, decimal (matches the rig's table in
  `lab/rig/rig_replay/rig_replay.ino`). Unknown keys log `keycode: 0` with
  a one-time stderr warning.
* `source` — a per-run hint (`human|scanner|rig`). Auto-labeling per event
  is exactly the detection problem P4 works on; for clean ground truth run
  one labeled session per input source (see below).

> **AUTHORIZATION — LAB ONLY.** This hook records everything typed on the
> machine it runs on, including passwords. Run it only on lab VMs you own
> or have **written authorization** to instrument. Never on a daily driver.

## Dependency

The script is stdlib-only **except** for live keyboard capture, which needs
[`pynput`](https://pypi.org/project/pynput/) — the single non-stdlib
dependency. Its import is guarded: without pynput, `--demo` still works.

```
pip install pynput
```

## macOS

1. Install pynput (a dedicated venv keeps the lab VM clean):
   `python3 -m venv .venv && .venv/bin/pip install pynput`
2. Grant the terminal app **Input Monitoring** (System Settings → Privacy
   & Security → Input Monitoring). Accessibility may be required on older
   macOS versions. Toggle the app off/on after granting.
3. Run:

```
python3 capture_keystrokes.py --session sess-017 --source human
```

Ctrl+C stops; each line is flushed immediately, so a crash loses nothing.

## Windows

1. Install Python 3.9+ from python.org (check "Add to PATH").
2. `pip install pynput`
3. Run from a console:

```
python capture_keystrokes.py --session sess-017 --source human
```

Ctrl+C stops. Some keys (media/IME) arrive as unknown and log `keycode: 0`.
If the listener dies instantly inside RDP, run it in a local console
session (RDP local resource redirection can swallow low-level hooks).

## Options

| Flag | Meaning |
|---|---|
| `--out FILE` | JSONL output (append mode; default `keystrokes-<session>.jsonl`) |
| `--session ID` | mandatory-style label; auto `sess-<yyyymmdd-hhmmss>` if omitted |
| `--source human\|scanner\|rig` | source hint for the run (default `human`) |
| `--device STR` | device/model label, e.g. the scanner model in use |
| `--demo N` | emit N synthetic events and exit (no pynput, no permissions) |
| `--duration S` | auto-stop after S seconds |

## Labeling methodology for clean P4 datasets

One source per session is the ground-truth-friendly pattern:

1. **Human baseline:** `--source human --device capture-host`, type normally
   for a few minutes.
2. **Scanner session:** same command with `--source scanner --device
   "<scanner model>"` (from `data/scanners.csv`, P1) while scanning codes
   from the W0.2 bench.
3. **Rig session:** `--source rig --device rig-pro-micro-01` while
   `lab/rig/send_payload.py` replays a payload.

Cross-check rig sessions against the rig's own serial JSONL stream —
matching the two event sequences (target-side capture vs rig-side emit) is
the W4.1 alignment exercise.

## Smoke test (no permissions, no pynput)

```
python3 capture_keystrokes.py --demo 10 --session sess-smoke
```

emits 5 keydown/keyup pairs simulating `GUI r` + ` hello` (GUI, r, space,
h, e), flushed to the JSONL file. P0's smoke run of this exact command is
recorded in the phase report.
