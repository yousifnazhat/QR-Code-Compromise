#!/usr/bin/env python3
"""run_matrix.py — render and plan the P3 payload-template matrix.

Usage:
    python3 run_matrix.py targets.toml [--dry-run] [--template ID ...]
    python3 run_matrix.py --manifest payloads/manifest.yaml targets.toml

Behavior:
  * targets.toml is a REQUIRED argument — the tool refuses to run without it.
    Copy payloads/targets.toml.example to targets.toml and fill in YOUR
    AUTHORIZED LAB placeholder values (attacker.example / RFC1918 10.x).
  * --dry-run prints, per template: the exact rendered Run-dialog command
    line and its expected-artifact list (feeds the P4 artifact runbook).
  * Without --dry-run the tool prints the execution PLAN only. It NEVER
    executes anything: VM execution is a manual physical slot for the
    human operator (see payloads/results/README.md).

Python 3.9+, stdlib only. Authorized lab security research only — see
payloads/README.md for the authorization statement.
"""

import argparse
import os
import re
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MANIFEST_PATH = os.path.join(BASE_DIR, "manifest.yaml")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
KILLCHAIN_PATH = os.path.join(BASE_DIR, "results", "killchain.csv")

# Contract #4 enums (frozen in COORDINATION.md)
RUNNERS = {"winr", "powershell", "mshta", "curl", "certutil", "msiexec", "unc"}
STAGING_MODES = {"inline", "staged"}
AMSI_STATES = {"bypassed", "blocked", "na"}
MANIFEST_FIELDS = {"id", "runner", "staging", "layout_safe", "win_build", "amsi", "notes"}
KILLCHAIN_HEADER = ["payload_id", "runner", "mitigation", "verdict"]
VERDICTS = {"bypass", "blocked", "partial"}

# ID set locked by coordinator (Main) — P4's runbook validates against this
# list verbatim. Change only via the contract-amendment flow.
LOCKED_IDS = ["ps-enc-001", "mshta-001", "curl-001", "certutil-001",
              "msiexec-001", "unc-001"]

REQUIRED_TEMPLATE_KEYS = ["TEMPLATE", "CLASS", "AUTHORIZATION", "PURPOSE",
                          "PREREQUISITES", "CLEANUP"]


class ManifestError(Exception):
    """Manifest or template does not conform to contract #4."""


class TargetError(Exception):
    """targets.toml missing/invalid or a placeholder cannot be resolved."""


# ---------------------------------------------------------------- manifest

def parse_manifest(path):
    """Parse the manifest.yaml subset used by contract #4.

    Accepted grammar: optional '#' comment lines; entries start with '- key:'
    and continue as indented 'key: value' lines; values are bare words
    (no spaces, no '#') or double-quoted strings.
    """
    try:
        with open(path, encoding="utf-8") as fh:
            lines = fh.read().splitlines()
    except OSError as exc:
        raise ManifestError("cannot read manifest %s: %s" % (path, exc))

    entries = []
    current = None
    for lineno, raw in enumerate(lines, 1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if raw.startswith("- "):
            current = {}
            entries.append(current)
            _manifest_kv(current, raw[2:], path, lineno)
        elif current is not None and (raw.startswith(" ") or raw.startswith("\t")):
            _manifest_kv(current, raw.strip(), path, lineno)
        else:
            raise ManifestError("%s:%d: unexpected top-level line %r"
                                % (path, lineno, raw))
    if not entries:
        raise ManifestError("%s: no entries found" % path)
    return entries


def _manifest_kv(entry, line, path, lineno):
    if ":" not in line:
        raise ManifestError("%s:%d: expected 'key: value', got %r"
                            % (path, lineno, line))
    key, _, value = line.partition(":")
    key = key.strip()
    value = value.strip()
    if value.startswith('"'):
        if len(value) < 2 or not value.endswith('"'):
            raise ManifestError("%s:%d: unterminated quoted value for %r"
                                % (path, lineno, key))
        value = value[1:-1]
    else:
        value = value.split(" #", 1)[0].strip()
    if key not in MANIFEST_FIELDS:
        raise ManifestError("%s:%d: unknown field %r (contract #4 fields: %s)"
                            % (path, lineno, key,
                               ", ".join(sorted(MANIFEST_FIELDS))))
    entry[key] = value


# ---------------------------------------------------------------- targets

def parse_targets(path):
    """Parse the flat TOML subset used by targets.toml: key = "value"."""
    if not os.path.isfile(path):
        raise TargetError("targets file not found: %s (copy "
                          "targets.toml.example to targets.toml and fill in "
                          "your authorized lab values)" % path)
    targets = {}
    with open(path, encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, 1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            match = re.match(r'^([A-Za-z0-9_]+)\s*=\s*"(.*)"\s*$', line)
            if not match:
                raise TargetError("%s:%d: expected key = \"value\", got %r"
                                  % (path, lineno, line))
            key, value = match.group(1), match.group(2)
            if key in targets:
                raise TargetError("%s:%d: duplicate key %r" % (path, lineno, key))
            if '"' in value:
                raise TargetError("%s:%d: embedded quote in value %r"
                                  % (path, lineno, value))
            targets[key] = value
    if not targets:
        raise TargetError("%s: no key = \"value\" lines found" % path)
    return targets


# --------------------------------------------------------------- templates

def parse_template(path):
    """Parse a template file into (meta, command).

    Header lines start with '# KEY: value' (continuation lines '#   text');
    ARTIFACT is repeatable; the header ends at the '# ---' separator or the
    first non-comment line. Everything after the header is the command body.
    """
    meta = {"ARTIFACT": []}
    command_lines = []
    in_header = True
    last_key = None
    with open(path, encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, 1):
            line = raw.rstrip("\n")
            if in_header and line.startswith("#"):
                body = line[1:]
                if body.strip() == "---":
                    in_header = False
                    continue
                match = re.match(r"^ ([A-Z]+): ?(.*)$", body)
                if match:
                    last_key = match.group(1)
                    if last_key == "ARTIFACT":
                        meta["ARTIFACT"].append(match.group(2).strip())
                    elif last_key in meta:
                        raise ManifestError("%s:%d: duplicate header key %s"
                                            % (path, lineno, last_key))
                    else:
                        meta[last_key] = match.group(2).strip()
                elif re.match(r"^   +\S", body) and last_key:
                    if last_key == "ARTIFACT":
                        meta["ARTIFACT"][-1] += " " + body.strip()
                    else:
                        meta[last_key] += " " + body.strip()
                else:
                    raise ManifestError("%s:%d: malformed header line %r"
                                        % (path, lineno, line))
            elif line.strip():
                in_header = False
                command_lines.append(line.strip())
    command = "\n".join(command_lines).strip()
    for key in REQUIRED_TEMPLATE_KEYS:
        if key == "ARTIFACT":
            if not meta["ARTIFACT"]:
                raise ManifestError("%s: no ARTIFACT lines in header" % path)
        elif not meta.get(key):
            raise ManifestError("%s: missing header key %s" % (path, key))
    if not command:
        raise ManifestError("%s: no command line after header" % path)
    return meta, command


def render(command, targets):
    """Replace <PLACEHOLDER> markers with values from targets (case-insensitive)."""
    lookup = {k.upper(): v for k, v in targets.items()}
    missing = []

    def repl(match):
        key = match.group(1)
        if key not in lookup:
            missing.append(key)
            return match.group(0)
        return lookup[key]

    rendered = re.sub(r"<([A-Z][A-Z0-9_]*)>", repl, command)
    if missing:
        raise TargetError("unresolved placeholders (add to targets.toml): %s"
                          % ", ".join(sorted(set(missing))))
    return rendered


# ----------------------------------------------------------------- checks

def validate_entries(entries):
    """Validate manifest entries against contract #4. Returns error list."""
    errors = []
    seen = set()
    ids = [entry.get("id") for entry in entries]
    if ids != LOCKED_IDS:
        errors.append("manifest ID set/order is locked to %s (P4 runbook "
                      "contract); found: %s — coordinate with the "
                      "coordinator before changing"
                      % (LOCKED_IDS, ids))
    for entry in entries:
        pid = entry.get("id", "<missing id>")
        extra = set(entry) - MANIFEST_FIELDS
        if extra:
            errors.append("%s: unknown fields %s" % (pid, sorted(extra)))
        missing = MANIFEST_FIELDS - set(entry)
        if missing:
            errors.append("%s: missing fields %s" % (pid, sorted(missing)))
            continue
        if pid in seen:
            errors.append("%s: duplicate id" % pid)
        seen.add(pid)
        if not re.match(r"^[a-z]+(?:-[a-z0-9]+)*-\d{3}$", pid):
            errors.append("%s: id must match <runner>-<NNN>" % pid)
        if entry["runner"] not in RUNNERS:
            errors.append("%s: runner %r not in contract enum %s"
                          % (pid, entry["runner"], sorted(RUNNERS)))
        if entry["staging"] not in STAGING_MODES:
            errors.append("%s: staging %r not in %s"
                          % (pid, entry["staging"], sorted(STAGING_MODES)))
        if entry["layout_safe"] not in ("true", "false"):
            errors.append("%s: layout_safe must be true|false, got %r"
                          % (pid, entry["layout_safe"]))
        if entry["amsi"] not in AMSI_STATES:
            errors.append("%s: amsi must be bypassed|blocked|na, got %r"
                          % (pid, entry["amsi"]))
        if entry["win_build"] != "any" and not re.match(r"^\d{4}$", entry["win_build"]):
            errors.append("%s: win_build must be a 4-digit Win10 build or "
                          "'any', got %r" % (pid, entry["win_build"]))
        if not entry["notes"].strip():
            errors.append("%s: notes must not be empty" % pid)
        # template cross-check
        tpath = os.path.join(TEMPLATES_DIR, pid + ".txt")
        if not os.path.isfile(tpath):
            errors.append("%s: template file missing: %s" % (pid, tpath))
        else:
            try:
                meta, command = parse_template(tpath)
                if meta.get("TEMPLATE") != pid:
                    errors.append("%s: header TEMPLATE %r != manifest id"
                                  % (pid, meta.get("TEMPLATE")))
            except ManifestError as exc:
                errors.append("%s: %s" % (pid, exc))
    return errors


# ------------------------------------------------------------------ main

def load_matrix(manifest_path, targets_path):
    entries = parse_manifest(manifest_path)
    errors = validate_entries(entries)
    if errors:
        for err in errors:
            print("ERROR: %s" % err, file=sys.stderr)
        raise ManifestError("manifest validation failed (%d error(s)); "
                            "run validate_manifest.py for details" % len(errors))
    targets = parse_targets(targets_path)
    return entries, targets


def select(entries, wanted):
    if not wanted:
        return entries
    known = {e["id"] for e in entries}
    for wid in wanted:
        if wid not in known:
            raise ManifestError("unknown --template id %r (known: %s)"
                                % (wid, ", ".join(sorted(known))))
    return [e for e in entries if e["id"] in wanted]


def emit_dry_run(entry, meta, rendered):
    print("=== %s [runner=%s staging=%s layout_safe=%s win_build=%s amsi=%s] ==="
          % (entry["id"], entry["runner"], entry["staging"],
             entry["layout_safe"], entry["win_build"], entry["amsi"]))
    print("COMMAND (%d chars):" % len(rendered))
    print("  %s" % rendered)
    print("EXPECTED ARTIFACTS:")
    for artifact in meta["ARTIFACT"]:
        print("  - %s" % artifact)
    print()


def emit_plan(entry, rendered):
    print("=== %s [runner=%s staging=%s] ===" % (entry["id"], entry["runner"],
                                                 entry["staging"]))
    print("PLAN (execution is a manual physical VM slot — this tool never "
          "executes payloads; see results/README.md):")
    print("  1. On the target VM, open the Run dialog (Win+R) — keystrokes "
          "delivered by scanner HID injection or the P0 replay rig.")
    print("  2. Inject the rendered template command (%d keystrokes) and press "
          "Enter." % len(rendered))
    print("  3. Observe the expected artifacts listed by --dry-run for %s "
          "(feeds W4.3 artifact runbook)." % entry["id"])
    print("  4. Record the verdict row in payloads/results/killchain.csv: "
          "payload_id,runner,mitigation,verdict.")
    print("  5. Perform the CLEANUP steps from the template header.")
    print()


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Render the P3 payload-template matrix against a lab "
                    "targets.toml. Plan/dry-run only — never executes.")
    parser.add_argument("targets", help="path to targets.toml (REQUIRED; the "
                        "tool refuses to run without it)")
    parser.add_argument("--manifest", default=MANIFEST_PATH,
                        help="manifest path (default: %(default)s)")
    parser.add_argument("--template", action="append", metavar="ID",
                        help="restrict to template id (repeatable)")
    parser.add_argument("--dry-run", action="store_true",
                        help="print exact rendered command lines + expected "
                             "artifact lists (default: plan only)")
    args = parser.parse_args(argv)

    if not os.path.isfile(args.targets):
        print("ERROR: refusing to run without a targets.toml: %s not found.\n"
              "       Copy payloads/targets.toml.example to targets.toml and "
              "fill in authorized lab placeholder values."
              % args.targets, file=sys.stderr)
        return 2

    try:
        entries, targets = load_matrix(args.manifest, args.targets)
        entries = select(entries, args.template)
    except (ManifestError, TargetError) as exc:
        print("ERROR: %s" % exc, file=sys.stderr)
        return 1

    print("# P3 payload matrix — %d template(s), targets=%s, mode=%s"
          % (len(entries), args.targets,
             "dry-run" if args.dry_run else "plan"))
    print("# AUTHORIZED LAB RESEARCH ONLY — all endpoints are placeholders "
          "(attacker.example / RFC1918 10.x example-only)\n")
    for entry in entries:
        tpath = os.path.join(TEMPLATES_DIR, entry["id"] + ".txt")
        try:
            meta, command = parse_template(tpath)
            rendered = render(command, targets)
        except (ManifestError, TargetError) as exc:
            print("ERROR: %s: %s" % (entry["id"], exc), file=sys.stderr)
            return 1
        if args.dry_run:
            emit_dry_run(entry, meta, rendered)
        else:
            emit_plan(entry, rendered)
    return 0


if __name__ == "__main__":
    sys.exit(main())
