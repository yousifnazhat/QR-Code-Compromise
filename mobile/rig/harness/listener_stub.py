#!/usr/bin/env python3
"""listener_stub.py — P6 rig: Kali-side session-verification listener (W6.3).

AUTHORIZATION — LAB ONLY (docs/governance/policy.md §1/§7). Binds ONLY where
the operator explicitly says (no default endpoint, policy §2) and exists to
verify the C stage of the historical chain class (the app-process callback
that, in the real historical exploits, was a reverse shell). The rig's benign
proof line is "P6RIG-SESSION device=<Build.FINGERPRINT>".

Usage:
    python3 listener_stub.py --host <your-kali-lan-ip> --port 4444 [--forever]

Stdlib only. Exit codes: 0 sessions received (or --forever interrupted);
2 usage/config error (missing --host/--port, port already in use).
"""

import argparse
import datetime
import socket
import sys

BANNER = (
    "== P6 rig session-verification listener (lab only) ==\n"
    "== Binds the explicit host:port you pass. Owned lab hosts only\n"
    "== (docs/governance/policy.md §1, §7; no default endpoints, §2)."
)


def log(msg: str) -> None:
    stamp = datetime.datetime.now().isoformat(timespec="seconds")
    print("[%s] %s" % (stamp, msg), flush=True)


def serve(host: str, port: int, forever: bool) -> int:
    srv = None
    try:
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((host, port))
        srv.listen(5)
        log("listening on %s:%d%s" % (host, port, " (forever)" if forever else " (one session)"))
    except OSError as e:
        print("FATAL: cannot bind %s:%d: %s" % (host, port, e), file=sys.stderr)
        return 2
    sessions = 0
    try:
        while True:
            try:
                conn, addr = srv.accept()
            except KeyboardInterrupt:
                raise
            sessions += 1
            log("session %d from %s:%d" % (sessions, addr[0], addr[1]))
            data = b""
            conn.settimeout(10)
            try:
                while True:
                    chunk = conn.recv(4096)
                    if not chunk:
                        break
                    data += chunk
            except socket.timeout:
                pass
            finally:
                conn.close()
            log("session %d proof: %r" % (sessions, data.decode("utf-8", "replace")))
            log("session %d VERIFIED" % sessions if data else
                "session %d empty (not verified)" % sessions)
            if not forever:
                break
    except KeyboardInterrupt:
        log("interrupted; %d session(s) received" % sessions)
    finally:
        if srv:
            srv.close()
    return 0 if sessions else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="P6 rig Kali-side session-verification listener (lab only).")
    ap.add_argument("--host", required=True,
                    help="interface IP to bind on YOUR Kali box (no default; policy §2)")
    ap.add_argument("--port", type=int, required=True,
                    help="TCP port to bind")
    ap.add_argument("--forever", action="store_true",
                    help="keep listening after the first session")
    args = ap.parse_args(argv)
    print(BANNER)
    if args.port <= 0 or args.port > 65535:
        print("FATAL: --port must be 1..65535", file=sys.stderr)
        return 2
    return serve(args.host, args.port, args.forever)


if __name__ == "__main__":
    sys.exit(main())
