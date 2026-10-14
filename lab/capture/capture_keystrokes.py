#!/usr/bin/env python3
"""capture_keystrokes.py -- target-side keystroke capture hook (contract #1).

Runs on the target machine (macOS or Windows) and appends one JSONL event
per keydown/keyup:

    {"ts_ms":123456,"event":"keydown","keycode":65,"source":"human",
     "device":"capture-host","session":"sess-017"}

ts_ms = time.monotonic_ns() // 1e6 (host-local monotonic ms; clocks are
per-device, P4 aligns sessions by onset, not by wall time). keycode is the
USB HID usage id where a mapping is known (0 otherwise, logged to stderr).

Global keyboard capture requires **pynput** -- the single non-stdlib
dependency -- and its import is guarded. Use --demo N to emit N synthetic
events with no pynput, no permissions and no real keyboard: this is the
pipeline smoke path.

AUTHORIZATION: lab-only research tooling. Run this only on machines you own
or have written authorization to instrument. It records everything typed on
the machine, including passwords -- use a dedicated lab VM, never a daily
driver.

Examples:
  python3 capture_keystrokes.py --demo 10 --session sess-smoke
  python3 capture_keystrokes.py --session sess-017 --source human
  python3 capture_keystrokes.py --session sess-018 --source scanner \
      --device "Honeywell 1470g" --duration 300
"""

import argparse
import json
import sys
import time

# pynput is the single non-stdlib dependency (guarded import).
try:
    from pynput import keyboard
except ImportError:
    keyboard = None

# ---------------------------------------------------------------------------
# USB HID usage-id tables (must match lab/rig/rig_replay/rig_replay.ino)

U_LCTRL, U_LSHIFT, U_LALT, U_LGUI = 0xE0, 0xE1, 0xE2, 0xE3
U_RCTRL, U_RSHIFT, U_RALT, U_RGUI = 0xE4, 0xE5, 0xE6, 0xE7
U_ENTER, U_ESC, U_BKSP, U_TAB, U_SPACE = 0x28, 0x29, 0x2A, 0x2B, 0x2C

ASCII_USAGE = {}
for _i, _c in enumerate("abcdefghijklmnopqrstuvwxyz"):
    ASCII_USAGE[_c] = 0x04 + _i
for _i, _c in enumerate("123456789"):
    ASCII_USAGE[_c] = 0x1E + _i
ASCII_USAGE["0"] = 0x27
ASCII_USAGE.update({
    " ": U_SPACE, "\n": U_ENTER, "\t": U_TAB,
    "-": 0x2D, "=": 0x2E, "[": 0x2F, "]": 0x30, "\\": 0x31,
    ";": 0x33, "'": 0x34, "`": 0x35, ",": 0x36, ".": 0x37, "/": 0x38,
})
SHIFTED_ASCII_USAGE = {}
for _i, _c in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
    SHIFTED_ASCII_USAGE[_c] = 0x04 + _i
SHIFTED_ASCII_USAGE.update({
    "_": 0x2D, "+": 0x2E, "{": 0x2F, "}": 0x30, "|": 0x31,
    ":": 0x33, '"': 0x34, "~": 0x35, "<": 0x36, ">": 0x37, "?": 0x38,
    "!": 0x1E, "@": 0x1F, "#": 0x20, "$": 0x21, "%": 0x22,
    "^": 0x23, "&": 0x24, "*": 0x25, "(": 0x26, ")": 0x27,
})

SPECIAL_KEY_USAGE = {
    "enter": U_ENTER, "return": U_ENTER, "esc": U_ESC, "escape": U_ESC,
    "backspace": U_BKSP, "tab": U_TAB, "space": U_SPACE,
    "shift": U_LSHIFT, "shift_r": U_RSHIFT,
    "ctrl": U_LCTRL, "ctrl_r": U_RCTRL,
    "alt": U_LALT, "alt_r": U_RALT, "alt_gr": U_RALT,
    "cmd": U_LGUI, "cmd_l": U_LGUI, "windows": U_LGUI,
    "cmd_r": U_RGUI, "caps_lock": 0x39,
    "f1": 0x3A, "f2": 0x3B, "f3": 0x3C, "f4": 0x3D, "f5": 0x3E,
    "f6": 0x3F, "f7": 0x40, "f8": 0x41, "f9": 0x42, "f10": 0x43,
    "f11": 0x44, "f12": 0x45,
    "insert": 0x49, "home": 0x4A, "page_up": 0x4B,
    "delete": 0x4C, "end": 0x4D, "page_down": 0x4E,
    "right": 0x4F, "left": 0x50, "down": 0x51, "up": 0x52,
}

_unmapped_warned = False


def keycode_for(key):
    """Map a pynput key to a USB HID usage id (0 if unknown)."""
    global _unmapped_warned
    if isinstance(key, keyboard.KeyCode):  # only reachable when pynput loaded
        if key.char:
            if key.char in ASCII_USAGE:
                return ASCII_USAGE[key.char]
            if key.char in SHIFTED_ASCII_USAGE:
                return SHIFTED_ASCII_USAGE[key.char]
        return 0
    name = getattr(key, "name", None)
    if name and name in SPECIAL_KEY_USAGE:
        return SPECIAL_KEY_USAGE[name]
    if not _unmapped_warned:
        _unmapped_warned = True
        print("warning: unmapped key (%r) logged with keycode 0" % (key,),
              file=sys.stderr)
    return 0


class JsonlWriter:
    def __init__(self, path, source, device, session):
        self.path = path
        self.labels = {"source": source, "device": device, "session": session}
        self.fh = open(path, "a", encoding="utf-8")

    def write(self, event, keycode):
        rec = {"ts_ms": int(time.monotonic_ns() // 1_000_000),
               "event": event, "keycode": keycode}
        rec.update(self.labels)
        self.fh.write(json.dumps(rec, separators=(",", ":")) + "\n")
        self.fh.flush()

    def close(self):
        self.fh.close()


def run_demo(writer, count):
    """Synthetic events, no pynput: 'GUI r' + " hello" keystroke pairs."""
    seq = [U_LGUI, 0x15, U_SPACE, 0x07, 0x08, 0x11, 0x11, 0x12]
    events, key_idx = 0, 0
    while events < count:
        usage = seq[key_idx % len(seq)]
        key_idx += 1
        writer.write("keydown", usage)
        events += 1
        if events < count:            # odd count leaves one key "held down"
            writer.write("keyup", usage)
            events += 1
        time.sleep(0.002)


def run_live(writer, duration):
    if keyboard is None:
        sys.exit("error: live capture requires pynput -- the single "
                 "non-stdlib dependency. Install with: pip install pynput. "
                 "(Or use --demo N for synthetic events.)")

    def on_press(key):
        writer.write("keydown", keycode_for(key))

    def on_release(key):
        writer.write("keyup", keycode_for(key))

    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.start()
    print("capturing... Ctrl+C to stop", file=sys.stderr)
    try:
        if duration:
            time.sleep(duration)
            listener.stop()
        else:
            listener.join()
    except KeyboardInterrupt:
        listener.stop()
    print("stopped", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", help="JSONL output file (append mode)")
    ap.add_argument("--session", help="contract-#1 session label "
                    "(default: sess-<timestamp>)")
    ap.add_argument("--source", default="human",
                    choices=["human", "scanner", "rig"],
                    help="source hint for this run (default: human)")
    ap.add_argument("--device", default="capture-host",
                    help="device/model label (default: capture-host)")
    ap.add_argument("--demo", type=int, metavar="N",
                    help="emit N synthetic events and exit (no pynput)")
    ap.add_argument("--duration", type=float,
                    help="stop after N seconds (default: until Ctrl+C)")
    args = ap.parse_args()

    session = args.session or time.strftime("sess-%Y%m%d-%H%M%S")
    out = args.out or "keystrokes-%s.jsonl" % session
    writer = JsonlWriter(out, args.source, args.device, session)
    print("session=%s source=%s device=%s out=%s"
          % (session, args.source, args.device, out), file=sys.stderr)

    if args.demo is not None:
        run_demo(writer, args.demo)
    else:
        run_live(writer, args.duration)
    writer.close()


if __name__ == "__main__":
    main()
