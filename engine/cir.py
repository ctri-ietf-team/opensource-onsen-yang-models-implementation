"""Canonical Intermediate Representation (CIR) flattening utilities.

The CIR is a flattened, module-prefix-stripped view of an instance tree
used for lossless-metric computation and trace path matching.
"""

from __future__ import annotations

from typing import Any, Dict, List


def strip_module_prefix(seg: str) -> str:
    """Strip a module prefix from a path segment, preserving key values.

    'l3vpn-svc:vpn-service' -> 'vpn-service'
    'vpn-service[vpn-id=VPN1]' -> unchanged (no prefix before '[')
    'rt=65000:100' -> unchanged (colon is inside the key value)
    """
    if ":" in seg and "=" not in seg and "[" not in seg:
        return seg.split(":", 1)[1]
    return seg


def _norm(path: str) -> List[str]:
    """Normalize a path into segments: strip module prefixes, drop the
    top-level container segment, and merge consecutive duplicate segments."""
    segs = [s for s in path.split("/") if s]
    if segs and ":" in segs[0]:
        segs = segs[1:]  # drop top-level container
    out: List[str] = []
    for s in segs:
        s = strip_module_prefix(s)
        if out and out[-1] == s:
            continue
        out.append(s)
    return out


def _base(seg: str) -> str:
    """Strip list key annotations: 'vpn-service[vpn-id=VPN1]' -> 'vpn-service'."""
    return seg.split("[", 1)[0]


def _seg_match(a: str, b: str) -> bool:
    """Match two path segments tolerating list-container name differences
    and leaf-list indices."""
    return _base(a) == _base(b)


def is_prefix(path: str, prefix: str) -> bool:
    """Segment-level prefix match: `path` is covered if the segments of
    `prefix` form a prefix of the segments of `path`."""
    p = _norm(prefix)
    q = _norm(path)
    if len(p) > len(q):
        return False
    return all(_seg_match(a, b) for a, b in zip(p, q))


def cir_keys(instance: Dict[str, Any], prefix: str = "") -> List[str]:
    """Flatten an instance dict into canonical leaf paths, preserving the
    original key names (including module prefixes)."""
    keys: List[str] = []
    for k, v in instance.items():
        path = f"{prefix}/{k}" if prefix else k
        if isinstance(v, dict):
            keys.extend(cir_keys(v, path))
        elif isinstance(v, list):
            for i, item in enumerate(v):
                if isinstance(item, dict):
                    keys.extend(cir_keys(item, path))
                else:
                    keys.append(f"{path}[{i}]")
        else:
            keys.append(path)
    return keys


def leaf_paths(instance: Dict[str, Any], prefix: str = "") -> List[str]:
    """Return only leaf (non-container) canonical paths."""
    out: List[str] = []
    for k, v in instance.items():
        path = f"{prefix}/{k}" if prefix else k
        if isinstance(v, dict):
            out.extend(leaf_paths(v, path))
        elif isinstance(v, list):
            for i, item in enumerate(v):
                if isinstance(item, dict):
                    out.extend(leaf_paths(item, path))
                else:
                    out.append(f"{path}[{i}]")
        else:
            out.append(path)
    return out