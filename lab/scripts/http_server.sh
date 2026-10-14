#!/bin/sh
# http_server.sh -- staging HTTP server for the W0.1 baseline lab chain.
# Serves the directory holding 1.txt (the encoded payload) to the lab victim
# VM, reproducing README step 4 (`python -m SimpleHTTPServer 7776`).
#
# AUTHORIZATION — LAB ONLY: bind to a lab interface only, serve only the
# staging directory, never real infrastructure.
#
# Usage: http_server.sh [port] [directory]
#        (default port 7776; default directory .)
set -eu
PORT="${1:-7776}"
DIR="${2:-.}"
echo "lab-only http server on 0.0.0.0:${PORT} serving $DIR (Ctrl+C to stop)" >&2
exec python3 -m http.server "$PORT" --directory "$DIR"
