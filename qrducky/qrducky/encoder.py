"""Layout-safe payload encoders (W2.2 — the core research piece).

Modes
=====
``b64``   — standard base64 (A-Za-z0-9+/=). Compact but NOT layout-portable:
            ``+``, ``/``, ``=`` have different positions on DE/FR, and ``y/z``
            swap on DE while FR remaps digits/a/q/w/z/m. Kept as the negative
            control / known-target mode.

``hex``   — uppercase hexadecimal (0-9A-F). Layout-portable across **US+DE**
            (digits unshifted identical, A-F positions unchanged; only y/z
            swap on DE, which hex never uses). FR breaks the naive-US stream
            (digits become & é " ' ( - è _ ç à, A becomes Q) — FR requires the
            layout-native keystroke variant (`--layout FR`).

``alnum`` — the portable mode. Each byte becomes a **pair of letters drawn
            only from the 20 layout-portable letters** (``BCDEFGHIJKLNOPRSTUVX``
            — positions identical on US, DE and FR). One US-configured scanner
            stream survives *all three* layouts simultaneously, with no target
            knowledge. A length-prefix pair is prepended (limits payloads to
            399 bytes, ample for Win+R one-liners). Density equals hex: 2
            characters per byte.

Encoding form (``alnum``): byte value ``v`` (< 400) -> pair
``PORTABLE_LETTERS[v // 20] + PORTABLE_LETTERS[v % 20]``.

Decoding on the target is P3's runner problem (payloads/manifest.yaml field
``layout_safe``); this module provides the authoritative Python reference
decoder used by the simulation matrix, plus US-syntax PowerShell decode hints
that P3 can adapt.
"""

import base64
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .keystrokes import Keystroke, native_keystrokes, naive_us_keystrokes
from .layouts import PORTABLE_LETTERS

MODES = ("alnum", "hex", "b64")
ALNUM_MAX_BYTES = 399  # length-prefix pair encodes 0..399

class EncodeError(ValueError):
    pass

class DecodeError(ValueError):
    pass

@dataclass
class EncodingResult:
    mode: str
    layout: str                    # target layout the keystrokes are built for
    text: str                      # characters that must appear on the target
    keystrokes: List[Keystroke]    # layout-native keystroke stream
    portable: bool                 # True if US-naive keystrokes survive US/DE/FR
    decoder_hint: str              # reference PowerShell decode (US syntax)
    warnings: List[str] = field(default_factory=list)

# ---------------------------------------------------------------------------
# Encoders
# ---------------------------------------------------------------------------
def encode_alnum(data: bytes) -> str:
    if len(data) > ALNUM_MAX_BYTES:
        raise EncodeError(
            f"alnum mode supports up to {ALNUM_MAX_BYTES} bytes "
            f"(got {len(data)}); use hex or b64")
    values = [len(data)] + list(data)
    return "".join(
        PORTABLE_LETTERS[v // 20] + PORTABLE_LETTERS[v % 20] for v in values)

def encode_hex(data: bytes) -> str:
    return data.hex().upper()

def encode_b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")

_ENCODERS = {"alnum": encode_alnum, "hex": encode_hex, "b64": encode_b64}

# ---------------------------------------------------------------------------
# Reference decoders (authoritative semantics; P3 ports these to runners)
# ---------------------------------------------------------------------------
def decode_alnum(text: str) -> bytes:
    text = "".join(text.split())
    if len(text) % 2:
        raise DecodeError("alnum text must have an even number of characters")
    idx = {c: i for i, c in enumerate(PORTABLE_LETTERS)}
    try:
        values = [idx[a] * 20 + idx[b]
                  for a, b in zip(text[0::2], text[1::2])]
    except KeyError as e:
        raise DecodeError(f"non-portable character {e} in alnum text") from e
    if not values:
        return b""
    length, rest = values[0], values[1:]
    if length != len(rest):
        raise DecodeError(
            f"alnum length prefix {length} != payload length {len(rest)}")
    if any(v > 255 for v in rest):
        raise DecodeError("alnum pair decodes above 0xFF — corrupted text")
    return bytes(rest)

def decode_hex(text: str) -> bytes:
    return bytes.fromhex(text)

def decode_b64(text: str) -> bytes:
    return base64.b64decode(text.encode("ascii"), validate=True)

_DECODERS = {"alnum": decode_alnum, "hex": decode_hex, "b64": decode_b64}


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
def is_portable(text: str) -> bool:
    """True if a US-configured scanner stream for `text` survives US/DE/FR."""
    ks = naive_us_keystrokes(text)
    if ks is None:
        return False
    from .keystrokes import simulate
    return all(simulate(ks, layout) == text for layout in ("US", "DE", "FR"))

def _hint_alnum(text: str) -> str:
    out = (
        'powershell -c "$t=\'__T__\';'
        '$a=\'__A__\'.ToCharArray();'
        '$p=@();for($i=0;$i -lt $t.Length;$i+=2){'
        '$x=$a.IndexOf($t[$i]);$y=$a.IndexOf($t[$i+1]);'
        '$p+=[byte]($x*20+$y)};$n=$p[0];'
        '[Text.Encoding]::UTF8.GetString($p[1..$n])"'
    )
    return out.replace("__T__", text).replace("__A__", PORTABLE_LETTERS)

def _hint_hex(text: str) -> str:
    out = (
        'powershell -c "$h=\'__T__\';'
        '[byte[]]$b=0..($h.Length/2-1)|'
        '%{[Convert]::ToByte($h.Substring($_*2,2),16)};'
        '[Text.Encoding]::UTF8.GetString($b)"'
    )
    return out.replace("__T__", text)

def _hint_b64(text: str) -> str:
    out = (
        'powershell -c "'
        "[Text.Encoding]::UTF8.GetString("
        "[Convert]::FromBase64String('__T__'))\""
    )
    return out.replace("__T__", text)

_HINTS = {"alnum": _hint_alnum, "hex": _hint_hex, "b64": _hint_b64}

def encode(data: bytes, mode: str = "alnum", layout: str = "US") -> EncodingResult:
    """Encode payload bytes for a target with active keyboard `layout`."""
    if mode not in MODES:
        raise EncodeError(f"unknown mode {mode!r} (choose from {MODES})")
    if layout not in ("US", "DE", "FR"):
        raise EncodeError(f"unknown layout {layout!r} (choose US, DE or FR)")
    if not isinstance(data, (bytes, bytearray)):
        raise EncodeError("payload must be bytes")

    data = bytes(data)
    text = _ENCODERS[mode](data)
    warnings: List[str] = []

    portable = is_portable(text)
    keystrokes = native_keystrokes(text, layout)
    if mode == "b64" and not portable:
        warnings.append(
            f"b64 is not layout-portable; this stream assumes the target "
            f"layout is {layout} (scanner must be configured accordingly). "
            f"Prefer alnum for unknown-layout targets.")
    if mode == "hex" and not portable:
        warnings.append(
            f"hex is layout-portable across US/DE but not FR; this stream "
            f"assumes the target layout is {layout}.")


    return EncodingResult(
        mode=mode,
        layout=layout,
        text=text,
        keystrokes=keystrokes,
        portable=portable,
        decoder_hint=_HINTS[mode](text),
        warnings=warnings,
    )

def decode(text: str, mode: str) -> bytes:
    if mode not in _DECODERS:
        raise DecodeError(f"unknown mode {mode!r}")
    return _DECODERS[mode](text)
