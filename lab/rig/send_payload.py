#!/usr/bin/env python3
"""send_payload.py -- host-side driver for the rig_replay HID replay rig.

Streams a text payload to the rig over serial using the chunked
BEGIN/END protocol (see lab/rig/README.md) and tees the rig's contract-#1
JSONL keystroke events to a file and/or stdout.

The ONLY non-stdlib dependency is pyserial (`pip install pyserial`),
required for live operation (--port). Use --dry-run to exercise the
protocol logic with no port and no rig attached.

AUTHORIZATION: lab-only research tooling. Use only against systems you own
or have written authorization to test. The rig is a keystroke injector.

Usage:
  python3 send_payload.py --dry-run --payload payload.txt --session sess-001
  python3 send_payload.py --port /dev/ttyACM0 --payload payload.txt \
      --prefix "GUI r" --suffix ENTER --cps 20 --jitter 15 \
      --session sess-001 --out rig-events.jsonl
"""

import argparse
import sys
import time

CHUNK_MAX = 47          # rig firmware fragment limit (CHUNK_MAX - 1)
READ_TIMEOUT = 120.0    # generous: ACK waits while the rig types at low cps


class RigError(Exception):
    pass


class SerialPort:
    """Thin wrapper: real pyserial when available, echo mode when dry-run."""

    def __init__(self, port, baud, dry_run=False):
        self.dry_run = dry_run
        self.events = []
        if dry_run:
            self._log("DRY-RUN: no serial port opened")
            return
        try:
            import serial  # pyserial (the single non-stdlib dependency)
        except ImportError:
            sys.exit("error: pyserial is required for live operation "
                     "(pip install pyserial), or pass --dry-run")
        self.ser = serial.Serial(port, baud, timeout=1.0)
        # Pro Micro CDC needs a moment after open before it is responsive.
        time.sleep(2.0)

    def _log(self, msg):
        print(msg, file=sys.stderr)

    def read_line(self, expected, timeout=READ_TIMEOUT):
        """Read lines until one starts with `expected`; JSONL event lines
        (starting with '{') are captured and echoed; other lines are shown."""
        if self.dry_run:
            return "DRY <" + expected
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            raw = self.ser.readline()
            if not raw:
                continue
            line = raw.decode("utf-8", "replace").rstrip("\r\n")
            if line.startswith("{"):
                self.events.append(line)
                print(line)
            elif line.startswith("ERR"):
                raise RigError(line)
            elif line.startswith(expected):
                return line
            else:
                self._log("rig: " + line)
        raise RigError("timeout waiting for %r" % expected)

    def send(self, data):
        if self.dry_run:
            self._log("DRY > " + repr(data))
            return
        self.ser.write(data.encode("utf-8"))
        self.ser.flush()


def iter_fragments(payload):
    """Yield <=47-byte fragments; never yield a fragment equal to 'END'
    (that literal is the streaming terminator)."""
    i = 0
    while i < len(payload):
        frag = payload[i:i + CHUNK_MAX]
        if frag == "END":
            frag = payload[i:i + 2]     # split "END" across two fragments
            if len(frag) < 2:            # degenerate tail
                frag = "E" + payload[i + 1:i + 2]
        yield frag
        i += len(frag)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", help="serial device, e.g. /dev/ttyACM0 or COM3")
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--payload", help="payload file, or '-' for stdin")
    ap.add_argument("--prefix", default="GUI r",
                    help="pre-payload key tokens (default: 'GUI r')")
    ap.add_argument("--suffix", default="ENTER",
                    help="post-payload key tokens (default: 'ENTER')")
    ap.add_argument("--cps", type=int, default=20, help="chars/sec 1..200")
    ap.add_argument("--jitter", type=int, default=15, help="0..250 ms")
    ap.add_argument("--session", default="sess-000",
                    help="contract-#1 session label emitted by the rig")
    ap.add_argument("--out", help="tee rig JSONL events to this file")
    ap.add_argument("--dry-run", action="store_true",
                    help="no port; print the protocol conversation")
    args = ap.parse_args()

    if not args.dry_run and not args.port:
        ap.error("--port is required (or use --dry-run)")
    if args.payload is None and not args.dry_run:
        ap.error("--payload is required (or use --dry-run)")

    payload = ""
    if args.payload:
        stream = sys.stdin if args.payload == "-" else open(args.payload, "r")
        payload = stream.read()
        if "\r" in payload:
            payload = payload.replace("\r\n", "\n").replace("\r", "")
            print("warning: stripped CR characters (rig cannot type them)",
                  file=sys.stderr)

    rig = SerialPort(args.port, args.baud, dry_run=args.dry_run)
    try:
        rig.read_line("RIG READY")
        for cmd in ("SESSION %s" % args.session,
                    "PREFIX %s" % args.prefix,
                    "SUFFIX %s" % args.suffix,
                    "CPS %d" % args.cps,
                    "JITTER %d" % args.jitter):
            rig.send(cmd + "\n")
            rig.read_line("OK")
        rig.send("BEGIN\n")
        rig.read_line("OK STREAMING")
        for frag in iter_fragments(payload):
            rig.send(frag + "\n")
            rig.read_line("ACK")
        rig.send("END\n")
        rig.read_line("OK DONE")
    except RigError as exc:
        rig.send("ABORT\n")  # best-effort safety stop (dry-run: logged only)
        sys.exit("rig error: %s" % exc)

    if args.out:
        with open(args.out, "a") as fh:
            for line in rig.events:
                fh.write(line + "\n")
        print("wrote %d events to %s" % (len(rig.events), args.out),
              file=sys.stderr)
    print("replay complete: %d events" % len(rig.events), file=sys.stderr)


if __name__ == "__main__":
    main()
