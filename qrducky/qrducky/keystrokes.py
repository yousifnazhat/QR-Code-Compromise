"""HID keystroke generation and layout simulation (W2.2).

Two keystroke strategies are modeled — this distinction is the research core:

- **naive US** (`naive_us_keystrokes`): the keystrokes a US-configured HID
  scanner (the factory default) emits for a text. Positional codes are then
  reinterpreted by the target layout. This is the "unknown target layout"
  deployment: the text survives only if every character is layout-portable.

- **layout-native** (`native_keystrokes`): for each character, the keystroke
  that the *target layout itself* uses to produce that character (i.e. what a
  keyboard with that layout would send). Requires knowing the target layout
  and configuring the scanner accordingly — the "known target" deployment.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

from .layouts import LAYOUTS, Layout

#: Sentinel produced when a keystroke hits a position with no key on the layout.
MISSING = "\u2205"  # ∅

@dataclass(frozen=True)
class Keystroke:
    usage: int
    shift: bool = False
    altgr: bool = False

def _char_to_keystroke(ch: str, layout: Layout) -> Optional[Keystroke]:
    """Reverse-map a character to the keystroke that produces it on `layout`."""
    for usage, (unshifted, shifted, altgr) in layout.items():
        if unshifted == ch:
            return Keystroke(usage)
        if shifted == ch:
            return Keystroke(usage, shift=True)
        if altgr == ch:
            return Keystroke(usage, altgr=True)
    return None

def native_keystrokes(text: str, layout_name: str) -> List[Keystroke]:
    """Keystrokes a keyboard with layout `layout_name` would send for `text`."""
    layout = LAYOUTS[layout_name]
    ks: List[Keystroke] = []
    for ch in text:
        k = _char_to_keystroke(ch, layout)
        if k is None:
            raise LayoutError(
                f"character {ch!r} is not typeable on layout {layout_name}")
        ks.append(k)
    return ks

def naive_us_keystrokes(text: str) -> Optional[List[Keystroke]]:
    """Keystrokes a US-configured HID scanner sends for `text`.

    Returns None if the text contains characters with no US keystroke.
    """
    ks: List[Keystroke] = []
    for ch in text:
        k = _char_to_keystroke(ch, LAYOUTS["US"])
        if k is None:
            return None
        ks.append(k)
    return ks

def simulate(keystrokes: List[Keystroke], layout_name: str) -> str:
    """Apply a keystroke stream on `layout_name`; return the resulting text.

    Positions with no key on the layout produce `MISSING` (∅), making the
    classic "AZERTY m key" failure explicit rather than silent.
    """
    layout = LAYOUTS[layout_name]
    out = []
    for k in keystrokes:
        triple = layout.get(k.usage)
        if triple is None:
            out.append(MISSING)
            continue
        if k.altgr:
            ch = triple[2]
        elif k.shift:
            ch = triple[1]
        else:
            ch = triple[0]
        out.append(ch if ch is not None else MISSING)
    return "".join(out)

class LayoutError(ValueError):
    pass
