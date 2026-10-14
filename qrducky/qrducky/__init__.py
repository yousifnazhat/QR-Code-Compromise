"""qrducky — QR keystroke-injection tooling for authorized lab security research.

WARNING: dual-use research tooling. Lab-only, written-authorization posture
(see qrducky/README.md and docs/governance/policy.md). No default endpoints.
"""

__version__ = "0.1.0"

from .encoder import (MODES, EncodingResult, EncodeError, DecodeError,
                      decode, encode)
from .keystrokes import (Keystroke, LayoutError, naive_us_keystrokes,
                         native_keystrokes, simulate)
from .layouts import LAYOUTS, PORTABLE_LETTERS
from .sheet import (SheetError, SheetResult, build_sheet, make_pdf, make_png,
                    make_qr)
from .engagement import EngagementError, apply_engagement

__all__ = [
    "__version__",
    "MODES", "EncodingResult", "EncodeError", "DecodeError", "encode", "decode",
    "Keystroke", "LayoutError", "naive_us_keystrokes", "native_keystrokes",
    "simulate", "LAYOUTS", "PORTABLE_LETTERS",
    "build_sheet", "SheetError", "SheetResult",
    "apply_engagement", "EngagementError",
]
