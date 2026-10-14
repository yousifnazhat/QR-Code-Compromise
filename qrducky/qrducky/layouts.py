"""Keyboard layout tables for HID keystroke simulation (W2.2 layout-safe encoder).

RESEARCH CONTEXT
================
A QR scanner acting as a HID keyboard emits *positional* USB HID usage codes
(usage IDs are key positions, not characters). The target OS maps a usage to a
character via the **active keyboard layout**. A scanner configured for the US
layout therefore types "wrong" characters on a machine whose active layout is
DE (QWERTZ) or FR (AZERTY) — the classic keystroke-injection layout problem.

Each table below maps HID usage ID -> (unshifted, shifted, altgr) as defined by
the corresponding Windows layout. Dead keys are represented as e.g. "acute(dead)"
so that corruption in simulations is explicit. `None` means the layout has no
key at that position (typing that usage produces nothing on the target).

Positional facts (stable across Windows builds):
  - German (DE) QWERTZ: y/z swapped; number row shifted = ! " § $ % & / ( ) =;
    ß?=, ´`=, ü Ü +*, #', ö Ö, ä Ä, ,; .: -_ <> | (ISO extra key).
  - French (FR) AZERTY: a<->q, z<->w, m at US-; position (US-m position unused),
    number row unshifted = & é " ' ( - è _ ç à  (digits require SHIFT),
    )° =+ ^¨ $£ *µ ù% ,? ;. :/ !§ (ISO) <> |.
  - US ANSI: reference layout (what a default-configured HID scanner assumes).

PORTABLE characters (W2.2 result): characters that a US-configured scanner can
type such that US, DE and FR all yield the identical character. See
`PORTABLE_LETTERS` — the 20 uppercase letters whose key position is unchanged on
all three layouts (A, M, Q, W, Y, Z are excluded; they are remapped or absent).
"""

import string
from typing import Dict, List, Optional, Tuple

Char3 = Tuple[Optional[str], Optional[str], Optional[str]]

Layout = Dict[int, Char3]

def _row(unshifted, shifted, altgr=None) -> Char3:
    return (unshifted, shifted, altgr)

def _letter_block(layout: Layout, swapped: Optional[Dict[int, str]] = None) -> None:
    """Fill a-z (usages 0x04..0x1D). `swapped` remaps US letter usages."""
    for i, ch in enumerate(string.ascii_lowercase):
        usage = 0x04 + i
        target = (swapped or {}).get(usage, ch)
        layout[usage] = _row(target, target.upper())

def _digit_row(layout: Layout, unshifted: str, shifted: str) -> None:
    for i, usage in enumerate(range(0x1E, 0x28)):
        layout[usage] = _row(unshifted[i], shifted[i])

# --- US (ANSI reference) ----------------------------------------------------
US: Layout = {}
_letter_block(US)
_digit_row(US, "1234567890", "!@#$%^&*()")
US.update({
    0x2C: _row(" ", " ", " "),   # Space
    0x2D: _row("-", "_"),
    0x2E: _row("=", "+"),
    0x2F: _row("[", "{"),
    0x30: _row("]", "}"),
    0x31: _row("\\", "|"),
    0x33: _row(";", ":"),
    0x34: _row("'", '"'),
    0x35: _row("`", "~"),
    0x36: _row(",", "<"),
    0x37: _row(".", ">"),
    0x38: _row("/", "?"),
})

# --- German (QWERTZ) ----------------------------------------------------------
DE: Layout = {}
_letter_block(DE, {0x1C: "z", 0x1D: "y"})
_digit_row(DE, "1234567890", '!"§$%&/()=')
DE.update({
    0x2C: _row(" ", " ", " "),
    0x2D: _row("ß", "?"),
    0x2E: _row("acute(dead)", "grave(dead)"),      # ´ `
    0x2F: _row("ü", "Ü"),
    0x30: _row("+", "*", "~"),
    0x31: _row("#", "'"),
    0x33: _row("ö", "Ö"),
    0x34: _row("ä", "Ä"),
    0x35: _row("circumflex(dead)", "°"),          # ^
    0x36: _row(",", ";"),
    0x37: _row(".", ":"),
    0x38: _row("-", "_"),
    0x64: _row("<", ">", "|"),                    # ISO key next to left shift
})
DE[0x14] = _row("q", "Q", "@")                     # AltGr+q = @

# --- French (AZERTY) ---------------------------------------------------------
FR: Layout = {}
# AZERTY letter remaps: a<->q (usages 0x04/0x14), z<->w (usages 0x1A/0x1D).
_letter_block(FR, {0x04: "q", 0x14: "a", 0x1A: "z", 0x1D: "w"})
FR[0x10] = (None, None, None)   # no key at the US-m position on AZERTY
FR[0x33] = _row("m", "M")       # m lives at the US-; position
_digit_row(FR, '&é"\'(-è_çà', "1234567890")
FR.update({
    0x2C: _row(" ", " ", " "),
    0x2D: _row(")", "°"),
    0x2E: _row("=", "+"),
    0x2F: _row("circumflex(dead)", "diaeresis(dead)"),  # ^ ¨
    0x30: _row("$", "£", "¤"),
    0x31: _row("*", "µ"),
    0x32: _row("!", "§"),       # ISO key next to right shift
    0x33: _row("m", "M"),
    0x34: _row("ù", "%"),
    0x35: _row("²", "~"),
    0x36: _row(",", "?"),
    0x37: _row(";", "."),
    0x38: _row(":", "/"),
    0x64: _row("<", ">", "|"),
})

LAYOUTS: Dict[str, Layout] = {"US": US, "DE": DE, "FR": FR}

#: The 20 uppercase letters whose key position is identical on US, DE and FR.
#: A, M, Q, W, Y, Z are excluded: A/M/Q/W/Z are remapped or absent on FR
#: (A->Q, M: key absent, Q->A, W->Z, Z->W), Y/Z swap on DE (QWERTZ).
PORTABLE_LETTERS: str = "BCDEFGHIJKLNOPRSTUVX"
assert len(PORTABLE_LETTERS) == 20
