"""Unit tests for the W4.4 HID report-descriptor parser/classifier."""

import pytest

from detection.allowlist.descriptor_parser import (
    DescriptorParseError,
    analyze,
    parse_descriptor,
)

# USB HID spec appendix example: standard boot keyboard.
KBD = ("05 01 09 06 A1 01 05 07 19 E0 29 E7 15 00 25 01 75 01 95 08 "
       "81 02 95 01 75 08 81 01 95 06 75 08 15 00 25 65 05 07 19 00 "
       "29 65 81 00 C0")

# Keyboard collection plus a vendor-defined input report.
KBD_VENDOR = "05 01 09 06 A1 01 06 00 FF 09 01 15 00 26 FF 00 75 08 95 40 81 00 C0"

# Mouse-only descriptor (HID spec example, trimmed).
MOUSE = ("05 01 09 02 A1 01 09 01 A1 00 05 09 19 01 29 03 15 00 25 01 "
         "95 03 75 01 81 02 95 01 75 05 81 01 05 01 09 30 09 31 75 0C "
         "95 02 81 02 C0 C0")

# Vendor-defined only (no keyboard declaration).
VENDOR_ONLY = "06 00 FF 09 01 A1 01 15 00 26 FF 00 75 08 95 08 81 00 C0"


def _pages(analysis):
    return [name for name, _ in analysis["classification"]["pages"]]


def test_standard_keyboard_verdict():
    cls = analyze(KBD)["classification"]
    assert cls["verdict"] == "standard_keyboard"
    assert cls["keyboard_declared"] is True
    assert cls["vendor_pages"] == []
    assert cls["allowlist_keyboard_admit"] is True


def test_keyboard_pages_detected():
    parsed = parse_descriptor(bytes.fromhex(
        KBD.replace(" ", "")))
    assert 0x01 in parsed["pages"]
    assert 0x07 in parsed["pages"]
    # modifier range E0-E7 and key array 00-65 registered as usages
    assert (0x07, 0xE0) in parsed["usages"]
    assert (0x07, 0x65) in parsed["usages"]


def test_keyboard_plus_vendor_verdict():
    cls = analyze(KBD_VENDOR)["classification"]
    assert cls["verdict"] == "keyboard_plus_vendor"
    assert "0xFF00" in cls["vendor_pages"]
    assert cls["allowlist_keyboard_admit"] is False


def test_single_byte_vendor_page_ff():
    cls = analyze("05 01 09 06 A1 01 05 FF 09 01 15 00 25 FF 75 08 95 40 "
                  "81 00 C0")["classification"]
    assert cls["verdict"] == "keyboard_plus_vendor"
    assert "0x00FF" in cls["vendor_pages"]


def test_mouse_only_is_other():
    cls = analyze(MOUSE)["classification"]
    assert cls["verdict"] == "other"
    assert cls["keyboard_declared"] is False


def test_vendor_only_verdict():
    cls = analyze(VENDOR_ONLY)["classification"]
    assert cls["verdict"] == "vendor_defined"
    assert cls["keyboard_declared"] is False


def test_truncated_item_raises():
    with pytest.raises(DescriptorParseError):
        parse_descriptor(bytes.fromhex("050109"))  # Usage Page w/ cut payload


def test_unterminated_collection_raises():
    with pytest.raises(DescriptorParseError):
        parse_descriptor(bytes.fromhex("05 01 09 06 A1 01".replace(" ", "")))


def test_usage_before_page_raises():
    with pytest.raises(DescriptorParseError):
        parse_descriptor(bytes.fromhex("0906"))  # Usage with no page set


def test_end_collection_without_open_raises():
    with pytest.raises(DescriptorParseError):
        parse_descriptor(bytes([0xC0]))


def test_hex_input_formats_accepted():
    reference = analyze(KBD)["classification"]
    # comma-separated
    assert analyze(KBD.replace(" ", ","))["classification"] == reference
    # 0x-prefixed, comma-separated tokens
    assert analyze("0x05, 0x01, 0x09, 0x06")["parsed"]["pages"] == [0x01]
    # unpadded byte run without separators
    assert analyze("05010906")["parsed"]["pages"] == [0x01]
    # mixed separators and 0x prefixes
    assert analyze("0x05 01,0x09 06")["parsed"]["pages"] == [0x01]


def test_invalid_hex_token_rejected():
    with pytest.raises(DescriptorParseError):
        analyze("05 01 zz")
    with pytest.raises(DescriptorParseError):
        analyze("")
    with pytest.raises(DescriptorParseError):
        analyze("050")  # odd-length run


def test_long_item_skipped():
    # long item: [FE][size 02][tag 00][2 data bytes] between normal items
    data = bytes.fromhex("05 01 FE 02 00 AB AB 09 06 A1 01 C0".replace(" ", ""))
    parsed = parse_descriptor(data)
    assert 0x01 in parsed["pages"]
    assert (0x01, 0x06) in parsed["usages"]


def test_modifier_and_key_usage_names():
    analysis = analyze(KBD)
    items = analysis["parsed"]["items"]
    # the single explicit Usage item is the keyboard collection usage
    names = [i["name"] for i in items if i.get("item") == "Usage"]
    assert names == ["Keyboard"]
    # key-array ranges are recorded as (page, usage) pairs
    usages = analysis["parsed"]["usages"]
    assert (0x07, 0xE0) in usages   # modifier range min
    assert (0x07, 0xE7) in usages   # modifier range max
    assert (0x07, 0x00) in usages   # key array min
    assert (0x07, 0x65) in usages   # key array max
