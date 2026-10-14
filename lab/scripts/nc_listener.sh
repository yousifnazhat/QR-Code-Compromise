#!/bin/sh
# nc_listener.sh -- reverse-shell listener for the W0.1 baseline lab chain.
#
# AUTHORIZATION — LAB ONLY: run this only on lab machines you own or have
# written authorization to test. The listener binds a local port and waits;
# it never reaches out to real infrastructure.
#
# Usage: nc_listener.sh [port]        (default 7775, per the repo README)
# Requires: netcat (nc).
set -eu
PORT="${1:-7775}"
echo "lab-only listener on 0.0.0.0:${PORT} (Ctrl+C to stop)" >&2
exec nc -lvp "$PORT"
