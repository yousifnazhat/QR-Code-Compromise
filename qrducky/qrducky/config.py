"""qrducky.toml configuration loading (contract #2: "Config via qrducky.toml").

Search order: --config flag > $QRDUCKY_CONFIG > ./qrducky.toml > the packaged
example. Missing file is not an error — built-in defaults apply — EXCEPT for
engagement targets, which must always be declared explicitly (GX.2: no default
endpoints anywhere).
"""

import copy
import os
import tomllib
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

DEFAULTS: Dict[str, Any] = {
    "sheet": {"module_mm": 4.0, "ec": "M"},
    "bench": {"default_repeat": 5, "targets": {}},
    "engagement": {"targets": {}},
}

@dataclass
class Config:
    path: Optional[str]
    sheet: Dict[str, Any] = field(default_factory=lambda: dict(DEFAULTS["sheet"]))
    bench: Dict[str, Any] = field(default_factory=lambda: dict(DEFAULTS["bench"]))
    engagement: Dict[str, Any] = field(
        default_factory=lambda: dict(DEFAULTS["engagement"]))

class ConfigError(ValueError):
    pass

def _merge(target: Dict[str, Any], source: Dict[str, Any]) -> None:
    for k, v in source.items():
        if isinstance(v, dict) and isinstance(target.get(k), dict):
            _merge(target[k], v)
        else:
            target[k] = v

def load_config(path: Optional[str] = None) -> Config:
    candidates = []
    if path:
        candidates.append(path)
    if os.environ.get("QRDUCKY_CONFIG"):
        candidates.append(os.environ["QRDUCKY_CONFIG"])
    candidates.append(os.path.join(os.getcwd(), "qrducky.toml"))

    # Deep-copy defaults: a Config must never share mutable state with
    # DEFAULTS (callers may mutate cfg.bench["targets"] in place).
    cfg = Config(
        path=None,
        sheet=copy.deepcopy(DEFAULTS["sheet"]),
        bench=copy.deepcopy(DEFAULTS["bench"]),
        engagement=copy.deepcopy(DEFAULTS["engagement"]),
    )
    for cand in candidates:
        if cand and os.path.isfile(cand):
            with open(cand, "rb") as f:
                data = tomllib.load(f)
            for section in ("sheet", "bench", "engagement"):
                if isinstance(data.get(section), dict):
                    _merge(cfg.__dict__[section], data[section])
            cfg.path = cand
            break
    # normalize target tables
    cfg.bench.setdefault("targets", {})
    cfg.engagement.setdefault("targets", {})
    return cfg

def bench_target(cfg: Config, name: str) -> Dict[str, Any]:
    targets = cfg.bench.get("targets", {})
    if name not in targets:
        raise ConfigError(
            f"bench target {name!r} is not declared in qrducky.toml "
            f"[bench.targets] (declared: {sorted(targets) or 'none'})")
    return targets[name]

def engagement_target(cfg: Config, name: str) -> Dict[str, Any]:
    targets = cfg.engagement.get("targets", {})
    if name not in targets:
        raise ConfigError(
            f"engagement target {name!r} is not declared in qrducky.toml "
            f"[engagement.targets] — explicit authorization required; "
            f"no implicit targets exist (declared: {sorted(targets) or 'none'})")
    return targets[name]
