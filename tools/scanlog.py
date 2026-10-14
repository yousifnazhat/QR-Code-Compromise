#!/usr/bin/env python3
"""
scanlog.py -- interactive physical-scan recorder for P1 (W1.3 symbology
reliability), appending rows to data/symbology.csv per frozen contract #3:

    symbology,ec_level,medium,module_mm,distance_cm,angle_deg,
    attempts,successes,mean_decode_s

AUTHORIZATION: lab-only measurement tool for the QR-Code-Compromise study.
It records human-observed decode results for OWNED, AUTHORIZED barcode
readers. It sends nothing anywhere and is not a payload delivery tool.

Modes
-----
    record (default)  prompt the operator for one condition, then append
                      one row. Timing: either comma-separated per-scan
                      decode times, or --stopwatch (interactive Enter-key
                      timing when stdin is a terminal).
    --validate        check data/symbology.csv against the contract #3
                      schema (header, types, ranges, cross-field rules).

Prompts are written to stderr and answers read line-by-line from stdin, so
a session can also be piped non-interactively:

    printf 'QR\\nM\\npaper\\n4.0\\n15\\n0\\n3\\n1.2,1.5,1.1\\n' \\
        | python3 tools/scanlog.py record --csv data/symbology.csv
"""

import argparse
import csv
import os
import sys
import time

DEFAULT_CSV = "data/symbology.csv"
HEADER = ["symbology", "ec_level", "medium", "module_mm", "distance_cm",
          "angle_deg", "attempts", "successes", "mean_decode_s"]
EC_LEVELS = {"L", "M", "Q", "H", "NA", ""}  # "" allowed for non-QR symbologies


class ValidationError(Exception):
    pass


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _num(value, field, lo, hi, allow_empty=False, integer=False):
    s = value.strip()
    if not s:
        if allow_empty:
            return None
        raise ValidationError("field %s is empty" % field)
    try:
        v = float(s)
    except ValueError:
        raise ValidationError("field %s=%r is not numeric" % (field, s))
    if integer and v != int(v):
        raise ValidationError("field %s=%r must be an integer" % (field, s))
    if not (lo <= v <= hi):
        raise ValidationError("field %s=%r outside range %g..%g"
                              % (field, s, lo, hi))
    return int(v) if integer else v


def validate_row(row, lineno):
    if len(row) != len(HEADER):
        raise ValidationError("expected %d fields, got %d"
                              % (len(HEADER), len(row)))
    rec = dict(zip(HEADER, row))
    if not rec["symbology"].strip():
        raise ValidationError("empty symbology")
    ec = rec["ec_level"].strip().upper()
    if ec not in EC_LEVELS:
        raise ValidationError("ec_level=%r not in {L,M,Q,H,NA}" % rec["ec_level"])
    _num(rec["module_mm"], "module_mm", 0.1, 100.0)
    _num(rec["distance_cm"], "distance_cm", 0.0, 1000.0)
    _num(rec["angle_deg"], "angle_deg", 0.0, 90.0)
    attempts = _num(rec["attempts"], "attempts", 1, 10000, integer=True)
    successes = _num(rec["successes"], "successes", 0, attempts, integer=True)
    s = rec["mean_decode_s"].strip()
    if s:
        m = _num(s, "mean_decode_s", 0.0, 3600.0)
        if successes == 0:
            raise ValidationError("mean_decode_s set but successes=0")
    elif successes > 0:
        raise ValidationError("successes>0 but mean_decode_s is empty")


def validate_csv(path):
    if not os.path.exists(path):
        print("FAIL %s: file not found" % path, file=sys.stderr)
        return 1
    errors = 0
    rows = 0
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        try:
            got_header = next(reader)
        except StopIteration:
            print("FAIL %s: empty file" % path, file=sys.stderr)
            return 1
        if got_header != HEADER:
            print("FAIL %s: header mismatch\n  expected: %s\n  got:      %s"
                  % (path, ",".join(HEADER), ",".join(got_header)),
                  file=sys.stderr)
            errors += 1
        for row in reader:
            rows += 1
            try:
                validate_row(row, rows + 1)
            except ValidationError as exc:
                print("FAIL %s line %d: %s" % (path, rows + 1, exc),
                      file=sys.stderr)
                errors += 1
    if errors:
        print("FAIL %s: %d/%d data rows invalid" % (path, errors, rows),
              file=sys.stderr)
        return 1
    print("OK %s: header + %d data rows valid against contract #3 schema"
          % (path, rows))
    return 0


# ---------------------------------------------------------------------------
# Recording
# ---------------------------------------------------------------------------


def _ask(prompt, reader, default=None):
    """Write prompt to stderr, read one line from stdin (strip newline)."""
    if default is not None:
        sys.stderr.write("%s [%s]: " % (prompt, default))
    else:
        sys.stderr.write("%s: " % prompt)
    sys.stderr.flush()
    line = sys.stdin.readline()
    if not line:
        raise EOFError("stdin closed while expecting %r" % prompt)
    ans = line.strip()
    if not ans and default is not None:
        return default
    return ans


def _ask_float(prompt, reader, lo, hi, default=None):
    while True:
        raw = _ask(prompt, reader, default)
        try:
            v = float(raw)
        except ValueError:
            sys.stderr.write("  not a number, try again\n")
            continue
        if not (lo <= v <= hi):
            sys.stderr.write("  out of range %g..%g, try again\n" % (lo, hi))
            continue
        return v


def _ask_int(prompt, reader, lo, hi):
    while True:
        raw = _ask(prompt, reader, None)
        try:
            v = int(raw)
        except ValueError:
            sys.stderr.write("  not an integer, try again\n")
            continue
        if not (lo <= v <= hi):
            sys.stderr.write("  out of range %d..%d, try again\n" % (lo, hi))
            continue
        return v


def _times_from_input(reader, attempts):
    """Comma-separated per-scan decode times (seconds since start)."""
    while True:
        raw = _ask("decode times in s, comma-separated (blank = none decoded)",
                   reader, "")
        if not raw:
            return []
        try:
            times = [float(t) for t in raw.split(",") if t.strip()]
        except ValueError:
            sys.stderr.write("  bad time list, try again\n")
            continue
        if len(times) > attempts:
            sys.stderr.write("  more times (%d) than attempts (%d), try again\n"
                             % (len(times), attempts))
            continue
        return times


def _times_stopwatch(attempts):
    """Interactive Enter-key stopwatch: one Enter per successful decode."""
    sys.stderr.write("stopwatch: press Enter at each decode beep; "
                     "press Enter after typing 'x' to stop early\n")
    times = []
    t0 = time.monotonic()
    while len(times) < attempts:
        line = sys.stdin.readline()
        if not line or line.strip().lower() == "x":
            break
        times.append(time.monotonic() - t0)
        sys.stderr.write("  decode %d at %.2fs\n" % (len(times), times[-1]))
    return times


def record(args):
    reader = None  # stdin is read line-by-line directly (pipe-friendly)
    symbology = _ask("symbology (qr, datamatrix, pdf417, aztec, code128, "
                     "qr-sa, ...)", reader, "qr")
    ec_raw = _ask("ec_level (L/M/Q/H, or NA for non-QR)", reader, "NA")
    ec = ec_raw.strip().upper()
    if ec and ec not in {"L", "M", "Q", "H", "NA"}:
        print("invalid ec_level %r -- use L/M/Q/H/NA" % ec, file=sys.stderr)
        return 1
    medium = _ask("medium (paper, screen, label, ...)", reader, "paper")
    module_mm = _ask_float("module_mm (printed module size)", reader, 0.1, 100.0)
    distance_cm = _ask_float("distance_cm (scanner-to-code)", reader, 0.0, 1000.0)
    angle_deg = _ask_float("angle_deg (incidence, 0=frontal)", reader, 0.0, 90.0)
    attempts = _ask_int("attempts (number of scan tries)", reader, 1, 10000)
    if args.stopwatch:
        if not sys.stdin.isatty():
            print("--stopwatch needs an interactive terminal", file=sys.stderr)
            return 1
        times = _times_stopwatch(attempts)
    else:
        times = _times_from_input(reader, attempts)

    successes = len(times)
    mean_decode_s = ""
    if successes:
        mean_decode_s = "%.3f" % (sum(times) / float(successes))
    row = [symbology, ec if ec != "NA" else "NA", medium,
           "%g" % module_mm, "%g" % distance_cm, "%g" % angle_deg,
           str(attempts), str(successes), mean_decode_s]
    validate_row(row, 0)  # never append an invalid row

    if not os.path.exists(args.csv) and not args.force_create:
        print("error: %s missing (expected header row); create it first "
              "or use --force-create" % args.csv, file=sys.stderr)
        return 1
    needs_header = (not os.path.exists(args.csv)) or os.path.getsize(args.csv) == 0
    with open(args.csv, "a", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        if args.force_create and needs_header:
            writer.writerow(HEADER)
        writer.writerow(row)
    print("appended: %s" % ",".join(row))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Record physical scan results into data/symbology.csv "
                    "(contract #3).")
    ap.add_argument("mode", nargs="?", default="record", choices=["record"],
                    help="record: prompt for one condition and append one row")
    ap.add_argument("--csv", default=DEFAULT_CSV,
                    help="target CSV (default %s)" % DEFAULT_CSV)
    ap.add_argument("--validate", action="store_true",
                    help="validate CSV against the contract #3 schema and exit")
    ap.add_argument("--stopwatch", action="store_true",
                    help="time successful decodes with Enter presses "
                         "(interactive terminals only)")
    ap.add_argument("--force-create", action="store_true",
                    help="create the CSV with a header row if missing")
    args = ap.parse_args(argv)

    if args.validate:
        return validate_csv(args.csv)
    return record(args)


if __name__ == "__main__":
    sys.exit(main())
