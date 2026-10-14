"""qr-ducky CLI — contract #2 of COORDINATION.md (frozen surface):

    qr-ducky encode --payload <file|-> --mode alnum|hex|b64 [--layout US|DE|FR]
    qr-ducky sheet  --payload <file> --out <pdf> [--module 4mm] [--ec M]
    qr-ducky bench  --target <vm-name> [--repeat N]

Exit codes: 0 = success; nonzero = failure with a structured JSON log line on
stderr ({"ts": ..., "level": ..., "cmd": ..., "msg": ...}). Specifically:
0 success, 1 runtime failure, 2 usage/config failure, 3 documented
not-implemented boundary (bench live mode without rig/pyserial).

Additive, non-breaking extensions (documented in contract-amendments.md):
`--json` on encode; `--mode` / `--layout` / `--png` / `--beacon-id` /
`--engage-target` on sheet; `--payload` / `--dry-run` on bench; global
`--config` on every subcommand.
"""

import argparse
import json
import sys
import time

from . import __version__, encoder, sheet as sheet_mod
from .bench import BenchError, BenchNotImplemented, bench_stats, run_bench
from .config import ConfigError, load_config
from .engagement import EngagementError, apply_engagement

def _log(level: str, cmd: str, msg: str, **extra) -> None:
    rec = {"ts": int(time.time() * 1000), "level": level, "cmd": cmd,
           "msg": msg}
    rec.update(extra)
    print(json.dumps(rec), file=sys.stderr)

class PayloadError(Exception):
    """Runtime payload read failure (exit 1)."""

class UsageError(Exception):
    """Usage/argument pairing failure (exit 2)."""

def _read_payload(path: str) -> bytes:
    try:
        if path == "-":
            return sys.stdin.buffer.read()
        with open(path, "rb") as f:
            return f.read()
    except OSError as e:
        raise PayloadError(f"cannot read payload {path!r}: {e}") from e

def _maybe_engage(text, beacon_id, engage_target, cmd, cfg):
    if not beacon_id and not engage_target:
        return text
    if beacon_id and not engage_target:
        raise UsageError("--beacon-id requires --engage-target "
                         "(explicit target declaration, GX.2)")
    if engage_target and not beacon_id:
        raise UsageError("--engage-target requires --beacon-id")
    return apply_engagement(text, beacon_id, engage_target, cfg).text

# ---------------------------------------------------------------------------
def cmd_encode(args, cfg) -> int:
    try:
        data = _read_payload(args.payload)
    except PayloadError as e:
        _log("error", "encode", str(e))
        return 1
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        _log("error", "encode",
             "payload is not valid UTF-8; engagement requires text payloads")
        return 1
    try:
        text = _maybe_engage(text, args.beacon_id, args.engage_target,
                             "encode", cfg)
        result = encoder.encode(text.encode("utf-8"), args.mode, args.layout)
    except UsageError as e:
        _log("error", "encode", str(e))
        return 2
    except (encoder.EncodeError, EngagementError, ConfigError) as e:
        _log("error", "encode", str(e))
        return 1
    for w in result.warnings:
        _log("warn", "encode", w, mode=result.mode, layout=result.layout)

    if args.json:
        print(json.dumps({
            "mode": result.mode,
            "layout": result.layout,
            "text": result.text,
            "chars": len(result.text),
            "portable": result.portable,
            "keystrokes": [{"usage": k.usage, "shift": k.shift,
                            "altgr": k.altgr} for k in result.keystrokes],
            "decoder_hint": result.decoder_hint,
            "warnings": result.warnings,
        }))
    else:
        print(result.text)
    return 0

# ---------------------------------------------------------------------------
def cmd_sheet(args, cfg) -> int:
    try:
        data = _read_payload(args.payload)
    except PayloadError as e:
        _log("error", "sheet", str(e))
        return 1
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        _log("error", "sheet", "payload is not valid UTF-8")
        return 1
    try:
        text = _maybe_engage(text, args.beacon_id, args.engage_target,
                             "sheet", cfg)
        if args.mode:
            enc = encoder.encode(text.encode("utf-8"), args.mode, args.layout)
            text = enc.text
            for w in enc.warnings:
                _log("warn", "sheet", w, mode=enc.mode, layout=enc.layout)
        label = (f"qr-ducky  ec={args.ec.upper()}  module={args.module}mm  "
                 f"chars={len(text)}")
        result = sheet_mod.build_sheet(
            text, args.out, module_mm=args.module, ec=args.ec, label=label)
    except UsageError as e:
        _log("error", "sheet", str(e))
        return 2
    except (sheet_mod.SheetError, encoder.EncodeError, EngagementError,
            ConfigError) as e:
        _log("error", "sheet", str(e))
        return 1
    for w in result.warnings:
        _log("warn", "sheet", w, path=result.path)
    _log("info", "sheet",
         f"wrote {result.path} (v{result.version}-{result.ec}, "
         f"{result.module_count} modules, {result.block_mm:.1f}mm block, "
         f"{result.chars} chars)")
    if args.png and result.fmt == "pdf":
        png_path = str(args.out)
        for ext in (".pdf", ".PDF"):
            if png_path.endswith(ext):
                png_path = png_path[: -len(ext)] + ".png"
                break
        try:
            png = sheet_mod.build_sheet(text, png_path, module_mm=args.module,
                                        ec=args.ec)
        except sheet_mod.SheetError as e:
            _log("error", "sheet", str(e))
            return 1
        for w in png.warnings:
            _log("warn", "sheet", w, path=png.path)
        _log("info", "sheet", f"wrote {png.path} (300dpi raster)")
    return 0

# ---------------------------------------------------------------------------
def cmd_bench(args, cfg) -> int:
    try:
        result = run_bench(cfg, args.target, args.repeat,
                           payload_arg=args.payload,
                           dry_run=args.dry_run)
    except BenchNotImplemented as e:
        _log("error", "bench", str(e), status="not_implemented",
             boundary="live serial needs serial_port config + "
                      "qrducky[bench] (pyserial); use --dry-run")
        return 3
    except (ConfigError, BenchError) as e:
        _log("error", "bench", str(e))
        return 2
    print(json.dumps(bench_stats(result)))
    transcript = result.conversation if result.dry_run else \
        result.conversation[:8]
    for line in transcript:
        _log("info", "bench", line)
    _log("info", "bench",
         f"calibration {'dry-run' if result.dry_run else 'live'} complete "
         f"for {args.target}: {result.repeat} repeat(s)")
    return 0

# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="qr-ducky",
        description="QR keystroke-injection tooling for authorized lab "
                    "research (see README — authorization required).")
    p.add_argument("--version", action="version",
                   version=f"qr-ducky {__version__}")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--config", help="path to qrducky.toml")
    sub = p.add_subparsers(dest="command", required=True)

    pe = sub.add_parser("encode", parents=[common],
                        help="layout-safe payload encoding (W2.2)")
    pe.add_argument("--payload", required=True,
                    help="payload file, or - for stdin")
    pe.add_argument("--mode", choices=encoder.MODES, default="alnum")
    pe.add_argument("--layout", choices=("US", "DE", "FR"), default="US",
                    help="active keyboard layout of the target (default US)")
    pe.add_argument("--json", action="store_true",
                    help="emit full structured result instead of bare text")
    pe.add_argument("--beacon-id", help="engagement variant id (W2.3)")
    pe.add_argument("--engage-target",
                    help="explicit engagement target from qrducky.toml")
    pe.set_defaults(func=cmd_encode)

    ps = sub.add_parser("sheet", parents=[common],
                        help="printable QR sheet (W2.1)")
    ps.add_argument("--payload", required=True, help="payload file")
    ps.add_argument("--out", required=True, help="output path (.pdf or .png)")
    ps.add_argument("--module", type=float, default=None,
                    help="module size in mm (default 4.0, from qrducky.toml)")
    ps.add_argument("--ec", default=None, choices=("L", "M", "Q", "H"),
                    help="QR error correction level (default M)")
    ps.add_argument("--mode", choices=encoder.MODES,
                    help="route payload through the encoder first")
    ps.add_argument("--layout", choices=("US", "DE", "FR"), default="US",
                    help="target layout for --mode encoding")
    ps.add_argument("--png", action="store_true",
                    help="with a .pdf --out, also write a 300dpi .png")
    ps.add_argument("--beacon-id", help="engagement variant id (W2.3)")
    ps.add_argument("--engage-target",
                    help="explicit engagement target from qrducky.toml")
    ps.set_defaults(func=cmd_sheet)

    pb = sub.add_parser("bench", parents=[common],
                        help="calibration harness (W2.4)")
    pb.add_argument("--target", required=True,
                    help="target VM name declared in [bench.targets]")
    pb.add_argument("--repeat", type=int, default=None,
                    help="calibration repeats (default 5, from qrducky.toml)")
    pb.add_argument("--payload", default=None,
                    help="payload file to calibrate with (or set "
                         "payload = \"<path>\" in [bench.targets.<t>])")
    pb.add_argument("--dry-run", action="store_true",
                    help="emit the rig protocol conversation without a port")
    pb.set_defaults(func=cmd_bench)
    return p

def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        cfg = load_config(args.config)
    except ConfigError as e:
        _log("error", args.command, f"config error: {e}")
        return 2
    if args.command == "sheet":
        if args.module is None:
            args.module = float(cfg.sheet.get("module_mm", 4.0))
        if args.ec is None:
            args.ec = str(cfg.sheet.get("ec", "M")).upper()
    return args.func(args, cfg)

if __name__ == "__main__":
    sys.exit(main())