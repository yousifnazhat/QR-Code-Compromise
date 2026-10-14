"""USB HID report-descriptor parser + allowlisting classifier (W4.4).

AUTHORIZATION: lab-only defensive tooling. Parses descriptors the
analyst dumps from OWNED lab hardware (P1's ``descriptor_dump.sh``)
and classifies them for HID-allowlist feasibility. No firmware
modification, no injection functionality.

Parses a HID report descriptor (raw bytes) into its items, tracks
global state (usage page, report size/count), and emits the usage
(page, usage) set a device declares, then classifies:

- standard_keyboard     — Generic Desktop + Keyboard/Keypad pages only
                          (optionally with common consumer extras);
- keyboard_plus_vendor  — keyboard pages plus vendor-defined pages;
- vendor_defined        — vendor pages and no keyboard declaration;
- other                 — neither (e.g. mouse-only, digitizer-only).

This is what a HID allowlist engine would gate on: descriptor
whitelisting (as in endpoint-protection products) allows "this exact
descriptor or usage set". The W4.4 hypothesis (see README.md) is that
a 2D imager in HID keyboard-wedge mode declares the *same* standard
keyboard descriptor as a normal keyboard, making descriptor-level
allowlisting blind to it — parsing lab descriptors quantifies that.

CLI:
    python3 -m detection.allowlist.descriptor_parser <hex-file|hex-string|->
        [--json]
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional, Tuple

__all__ = ["parse_descriptor", "classify", "analyze", "main"]

# --- HID item tags -------------------------------------------------
# The parser masks each item prefix with 0xFC (dropping the two size
# bits), so these constants are the *masked tag* values, not the raw
# prefix bytes (e.g. Usage Page prefix byte 0x05 -> masked tag 0x04).
USAGE_PAGE = 0x04
LOGICAL_MIN = 0x14
LOGICAL_MAX = 0x24
REPORT_SIZE = 0x74
REPORT_COUNT = 0x94
REPORT_ID = 0x84
# Local items
USAGE = 0x08
USAGE_MIN = 0x18
USAGE_MAX = 0x28
# Main items
COLLECTION = 0xA0
END_COLLECTION = 0xC0
INPUT = 0x80
OUTPUT = 0x90
FEATURE = 0xB0
# Long item prefix (checked before masking)
LONG_ITEM = 0xFE

USAGE_PAGES = {
    0x01: "Generic Desktop",
    0x02: "Simulation",
    0x03: "VR Controls",
    0x04: "Sport Controls",
    0x05: "Game Controls",
    0x06: "Generic Device Controls",
    0x07: "Keyboard/Keypad",
    0x08: "LED",
    0x09: "Button",
    0x0B: "Telephony",
    0x0C: "Consumer",
    0x0D: "Digitizer",
    0x0F: "Physical Interface Device",
    0x10: "Unicode",
    0x12: "Eye and Head Trackers",
    0x20: "Sensor",
    0x84: "Power Device",
    0x85: "Battery System",
}

GENERIC_DESKTOP_USAGES = {
    0x01: "Pointer", 0x02: "Mouse", 0x04: "Joystick", 0x05: "Game Pad",
    0x06: "Keyboard", 0x07: "Keypad", 0x30: "X", 0x31: "Y", 0x32: "Z",
    0x38: "Wheel", 0x39: "Hat Switch",
}

# Pages seen on ordinary consumer keyboards/mice beyond page 7 —
# treated as "common consumer HID", not a red flag for allowlisting.
COMMON_CONSUMER_PAGES = {0x01, 0x06, 0x07, 0x08, 0x09, 0x0C, 0x0D}

VENDOR_PAGE_MIN = 0xFF00


def _is_vendor_page(page: int) -> bool:
    """Vendor-defined usage pages: 0xFF00-0xFFFF, plus the ubiquitous
    single-byte page 0xFF declared by many real vendor devices."""
    return page >= VENDOR_PAGE_MIN or page == 0xFF


class DescriptorParseError(ValueError):
    """Raised when the byte stream is not a well-formed descriptor."""


def _page_name(page: int) -> str:
    if _is_vendor_page(page):
        return "Vendor-Defined 0x%04X" % page
    return USAGE_PAGES.get(page, "Unknown 0x%04X" % page)


def _usage_name(page: int, usage: int) -> str:
    if page == 0x01:
        return GENERIC_DESKTOP_USAGES.get(usage, "usage 0x%02X" % usage)
    if page == 0x07:
        if 0x04 <= usage <= 0xA4:
            return "key 0x%02X" % usage
        if 0xE0 <= usage <= 0xE7:
            return "modifier 0x%02X" % usage
        return "keycode 0x%02X" % usage
    return "usage 0x%02X" % usage


def _le(bytes_in: List[int]) -> int:
    return int.from_bytes(bytes(bytes_in), "little")


def parse_descriptor(data: bytes) -> Dict[str, Any]:
    """Walk the descriptor; return items, usages, collection depth.

    Raises DescriptorParseError on truncation or malformed structure.
    """
    items: List[Dict[str, Any]] = []
    usages: List[Tuple[int, int]] = []
    pages: List[int] = []
    collection_stack: List[int] = []
    page = None  # current global usage page
    i = 0
    report_sizes: List[int] = []
    report_counts: List[int] = []
    report_ids: List[int] = []

    while i < len(data):
        prefix = data[i]
        if prefix == LONG_ITEM:
            # Long item: [0xFE][data size][long tag][data...]
            if i + 2 >= len(data):
                raise DescriptorParseError("truncated long item at %d" % i)
            size = data[i + 1]
            if i + 3 + size > len(data):
                raise DescriptorParseError("truncated long item at %d" % i)
            i += 3 + size
            continue
        size = prefix & 0x03
        tag = prefix & 0xFC
        i += 1
        if i + size > len(data):
            raise DescriptorParseError("truncated item at offset %d" % i)
        payload = data[i:i + size]
        i += size

        if tag == USAGE_PAGE:
            page = _le(list(payload))
            if page not in pages:
                pages.append(page)
            items.append({"offset": i - 1 - size, "item": "UsagePage",
                          "value": page, "name": _page_name(page)})
        elif tag == USAGE:
            if page is None:
                raise DescriptorParseError(
                    "Usage item before any Usage Page declaration")
            usages.append((page, _le(list(payload))))
            items.append({"offset": i - 1 - size, "item": "Usage",
                          "value": _le(list(payload)),
                          "page": page,
                          "name": _usage_name(page, _le(list(payload)))})
        elif tag in (USAGE_MIN, USAGE_MAX):
            if page is None:
                raise DescriptorParseError(
                    "Usage Min/Max before any Usage Page declaration")
            kind = "UsageMin" if tag == USAGE_MIN else "UsageMax"
            value = _le(list(payload))
            usages.append((page, value))
            items.append({"offset": i - 1 - size, "item": kind,
                          "value": value, "page": page})
        elif tag == COLLECTION:
            collection_stack.append(_le(list(payload)))
            items.append({"offset": i - 1 - size, "item": "Collection",
                          "value": _le(list(payload))})
        elif tag == END_COLLECTION:
            if not collection_stack:
                raise DescriptorParseError(
                    "End Collection without open collection")
            collection_stack.pop()
            items.append({"offset": i - 1 - size, "item": "EndCollection"})
        elif tag == REPORT_SIZE:
            report_sizes.append(_le(list(payload)))
            items.append({"offset": i - 1 - size, "item": "ReportSize",
                          "value": _le(list(payload))})
        elif tag == REPORT_COUNT:
            report_counts.append(_le(list(payload)))
            items.append({"offset": i - 1 - size, "item": "ReportCount",
                          "value": _le(list(payload))})
        elif tag == REPORT_ID:
            report_ids.append(_le(list(payload)))
            items.append({"offset": i - 1 - size, "item": "ReportId",
                          "value": _le(list(payload))})
        elif tag in (INPUT, OUTPUT, FEATURE):
            name = {INPUT: "Input", OUTPUT: "Output",
                    FEATURE: "Feature"}[tag]
            items.append({"offset": i - 1 - size, "item": name,
                          "value": _le(list(payload))})
        else:
            items.append({"offset": i - 1 - size, "item": "item-0x%02X" % tag,
                          "value": _le(list(payload))})

    if collection_stack:
        raise DescriptorParseError(
            "unterminated collection(s): depth %d at end" % len(collection_stack))

    return {
        "items": items,
        "pages": pages,
        "usages": usages,
        "collection_depth": len(collection_stack) or 0,
        "report_sizes": report_sizes,
        "report_counts": report_counts,
        "report_ids": report_ids,
    }


def classify(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """Keyboard vs vendor classification of a parsed descriptor."""
    pages = parsed["pages"]
    usages = parsed["usages"]
    vendor_pages = [p for p in pages if _is_vendor_page(p)]
    keyboard_declared = (
        0x07 in pages                      # Keyboard/Keypad page
        # Generic Desktop collection declared as Keyboard/Keypad
        or any(p == 0x01 and u in (0x06, 0x07) for p, u in usages)
    )
    non_common = [p for p in pages if p not in COMMON_CONSUMER_PAGES]

    if keyboard_declared and vendor_pages:
        verdict = "keyboard_plus_vendor"
    elif keyboard_declared:
        verdict = "standard_keyboard"
    elif vendor_pages:
        verdict = "vendor_defined"
    else:
        verdict = "other"

    return {
        "verdict": verdict,
        "keyboard_declared": keyboard_declared,
        "pages": [(_page_name(p), "0x%04X" % p) for p in pages],
        "vendor_pages": ["0x%04X" % p for p in vendor_pages],
        "non_consumer_pages": [(_page_name(p), "0x%04X" % p) for p in non_common],
        "usage_count": len(usages),
        # The W4.4 allowlisting hypothesis: this descriptor would be
        # admitted by a keyboard allowlist because it declares nothing
        # beyond standard keyboard pages.
        "allowlist_keyboard_admit": verdict == "standard_keyboard",
    }


def analyze(hex_text: str) -> Dict[str, Any]:
    """Parse hex text -> full analysis dict (parse + classify).

    Accepts whitespace- or comma-separated hex bytes, with or without
    ``0x`` prefixes; byte runs without separators (``05010906``) are
    split into byte pairs.
    """
    cleaned = hex_text.replace(",", " ").replace("0x", " ").replace("0X", " ")
    tokens = cleaned.split()
    if not tokens:
        raise DescriptorParseError("no hex bytes provided")
    bytes_hex = []
    hex_digits = set("0123456789abcdef")
    for tok in tokens:
        tok = tok.lower()
        if not tok or len(tok) % 2 or not set(tok) <= hex_digits:
            raise DescriptorParseError("invalid hex token: %r" % tok)
        bytes_hex.extend(tok[i:i + 2] for i in range(0, len(tok), 2))
    data = bytes(int(t, 16) for t in bytes_hex)
    parsed = parse_descriptor(data)
    return {"parsed": parsed, "classification": classify(parsed)}


def _render(analysis: Dict[str, Any]) -> str:
    parsed = analysis["parsed"]
    cls = analysis["classification"]
    lines = []
    lines.append("HID report descriptor analysis (W4.4)")
    lines.append("-" * 48)
    lines.append("items        : %d" % len(parsed["items"]))
    lines.append("report ids   : %s" % (parsed["report_ids"] or "single report"))
    lines.append("usage pages  :")
    for name, hexid in cls["pages"]:
        lines.append("  %-24s (%s)" % (name, hexid))
    lines.append("declared usages: %d" % cls["usage_count"])
    lines.append("verdict      : %s" % cls["verdict"])
    lines.append("keyboard     : %s" % ("yes" if cls["keyboard_declared"] else "no"))
    lines.append("vendor pages : %s" % (", ".join(cls["vendor_pages"]) or "none"))
    lines.append("allowlist    : %s by a keyboard-descriptor allowlist"
                 % ("ADMITTED" if cls["allowlist_keyboard_admit"]
                    else "not admitted (review)"))
    return "\n".join(lines) + "\n"


def main(argv: List[str] = None) -> int:
    ap = argparse.ArgumentParser(
        description="HID report descriptor parser + classifier")
    ap.add_argument("input",
                    help="hex file path, hex string (space/comma separated), "
                         "or '-' for stdin")
    ap.add_argument("--json", action="store_true",
                    help="emit JSON instead of text")
    args = ap.parse_args(argv)

    if args.input == "-":
        hex_text = sys.stdin.read()
    else:
        import os
        if os.path.exists(args.input):
            with open(args.input, "r", encoding="utf-8") as fh:
                hex_text = fh.read()
        else:
            hex_text = args.input  # treat the argument as hex text
    try:
        analysis = analyze(hex_text)
    except DescriptorParseError as exc:
        sys.stderr.write("descriptor parse error: %s\n" % exc)
        return 2

    if args.json:
        json.dump(analysis, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        sys.stdout.write(_render(analysis))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
