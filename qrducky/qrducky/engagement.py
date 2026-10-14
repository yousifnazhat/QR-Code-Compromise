"""Engagement mode (W2.3): per-target variant tagging.

`--beacon-id` stamps a payload variant with a per-target id so a lab
engagement can attribute observed scans to a specific physical placement.
Two embedding methods, chosen by the target's config entry:

- ``url-param``   — appends ``bid=<beacon-id>`` to the first URL in the payload
                    (query or first param as appropriate). No endpoint is ever
                    invented: the payload must already carry its (lab) URL.
- ``ps-comment``  — appends a PowerShell comment `` # <beacon-id>``.

Authorization posture (GX.2): the target must be **explicitly declared** in
``qrducky.toml [engagement.targets]``; there are no defaults and no committed
endpoints. Example URLs in the packaged config use ``attacker.example``,
reserved for documentation (RFC 2606 style lab placeholder).
"""

import re
from dataclasses import dataclass
from typing import Dict, List

from .config import ConfigError, engagement_target

_URL_RE = re.compile(r"https?://[^\s\"'<>]+")

class EngagementError(ValueError):
    pass

@dataclass
class EngagementResult:
    text: str
    method: str
    beacon_id: str
    target: str

def apply_engagement(payload_text: str, beacon_id: str, target: str,
                     cfg) -> EngagementResult:
    """Return payload text with the beacon embedded for the declared target."""
    if not beacon_id or re.search(r"\s", beacon_id):
        raise EngagementError(
            "--beacon-id must be a non-empty id without whitespace")
    entry = engagement_target(cfg, target)  # raises ConfigError if undeclared
    method = entry.get("method", "ps-comment")
    if method not in ("url-param", "ps-comment"):
        raise ConfigError(
            f"engagement target {target!r}: method must be "
            f"'url-param' or 'ps-comment', got {method!r}")

    if method == "url-param":
        m = _URL_RE.search(payload_text)
        if not m:
            raise EngagementError(
                f"--beacon-id with url-param requires a http(s) URL in the "
                f"payload (or use method = 'ps-comment' for target {target!r})")
        url = m.group(0)
        sep = "&" if "?" in url else "?"
        stamped = url + sep + "bid=" + beacon_id
        text = payload_text.replace(url, stamped, 1)
    else:  # ps-comment
        text = payload_text.rstrip("\n") + f" # {beacon_id}"

    return EngagementResult(text=text, method=method,
                            beacon_id=beacon_id, target=target)
