"""Lossless mapping metrics: coverage, round-trip diff, traceability.

TC-MAP-001: coverage rate == 100%
TC-MAP-002: round-trip diff == 0
TC-MAP-003: traceability rate == 100%
"""

from __future__ import annotations

from typing import Any, Dict, List

from .cir import is_prefix, leaf_paths

IDENTITY_ALIASES = {
    "ietf-l3vpn-svc:": "id:",
    "ietf-l3vpn-ntw:": "id:",
}


def _normalize_value(v: Any) -> Any:
    """Normalize identityref prefixes for value comparison."""
    if isinstance(v, str):
        for old, new in IDENTITY_ALIASES.items():
            if v.startswith(old):
                return new + v[len(old):]
        return v
    if isinstance(v, dict):
        return {k: _normalize_value(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_normalize_value(x) for x in v]
    return v


def _get_by_path(instance: Dict[str, Any], path: str) -> Any:
    """Navigate an instance dict by a slash path with list keys.

    Path format: 'l3sm:/vpn-services/vpn-service[vpn-id=VPN1]/vpn-id'
    Bare list segments ('vpn-service/vpn-id') descend into the first entry.
    """
    segs = [s for s in path.split("/") if s]
    if segs and segs[0].endswith(":"):
        segs = segs[1:]
    cur = instance
    # auto-enter a single top-level container carrying a module prefix
    if isinstance(cur, dict) and len(cur) == 1:
        only = next(iter(cur))
        if ":" in only:
            cur = cur[only]
    for seg in segs:
        if isinstance(cur, list):
            # cur is a list: seg either selects an entry ([key=value]) or is a
            # field name to look up inside the first entry.
            if "[" in seg:
                name, keys = seg.split("[", 1)
                keys = keys.rstrip("]")
                if "=" in keys:
                    k, v = keys.split("=", 1)
                    found = None
                    for item in cur:
                        if isinstance(item, dict) and str(item.get(k)) == v:
                            found = item
                            break
                    if found is None:
                        return None
                    cur = found
                    continue
                cur = cur[0] if cur else None
                if cur is None:
                    return None
                continue
            cur = cur[0] if cur else None
            if cur is None:
                return None
            # fall through to the dict lookup below
        if not isinstance(cur, dict):
            return None
        if "[" in seg:
            name, keys = seg.split("[", 1)
            keys = keys.rstrip("]")
            if "=" not in keys:
                return None
            k, v = keys.split("=", 1)
            found = None
            for item in cur.get(name, []):
                if str(item.get(k)) == v:
                    found = item
                    break
            if found is None:
                return None
            cur = found
        else:
            if seg in cur:
                cur = cur[seg]
            else:
                matched = None
                for key in cur:
                    if key.split(":", 1)[-1] == seg:
                        matched = key
                        break
                if matched is None:
                    return None
                cur = cur[matched]
    return cur


def _is_leaf_path(path: str) -> bool:
    """A leaf path ends with a plain segment (no list key annotation)."""
    last = path.split("/")[-1]
    return "[" not in last


def compute_coverage(
    l3sm: Dict[str, Any], trace_entries: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Fraction of L3SM leaf paths covered by trace source paths."""
    leaves = leaf_paths(l3sm)
    sources = [e["source"] for e in trace_entries]
    covered = [p for p in leaves if any(is_prefix(p, s) for s in sources)]
    return {
        "total": len(leaves),
        "covered": len(covered),
        "rate": round(len(covered) / len(leaves), 6) if leaves else 1.0,
        "uncovered": [p for p in leaves if p not in covered],
    }


def compute_roundtrip_diff(
    l3sm: Dict[str, Any],
    l3nm: Dict[str, Any],
    trace_entries: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """For reversible fields (COPY/RENAME), compare the L3NM value mapped
    back against the original L3SM value. diff_count == 0 means lossless."""
    diffs: List[Dict[str, Any]] = []
    for e in trace_entries:
        if e["op"] not in ("COPY", "RENAME") or e["target"] == "-":
            continue
        # skip structural list-item renames (site -> vpn-node etc.)
        if not _is_leaf_path(e["source"]) or not _is_leaf_path(e["target"]):
            continue
        src = _get_by_path(l3sm, e["source"])
        tgt = _get_by_path(l3nm, e["target"])
        if src is None or tgt is None:
            continue
        if _normalize_value(src) != _normalize_value(tgt):
            diffs.append({
                "rule": e["rule_id"],
                "source": e["source"],
                "target": e["target"],
                "src_value": src,
                "tgt_value": tgt,
            })
    return {"diff_count": len(diffs), "diffs": diffs}


def compute_traceability(
    l3nm: Dict[str, Any], trace_entries: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Fraction of L3NM leaf paths traceable to an L3SM source."""
    leaves = leaf_paths(l3nm)
    targets = [e["target"] for e in trace_entries if e["target"] != "-"]
    traced = [p for p in leaves if any(is_prefix(p, t) for t in targets)]
    return {
        "total": len(leaves),
        "traced": len(traced),
        "rate": round(len(traced) / len(leaves), 6) if leaves else 1.0,
        "untraced": [p for p in leaves if p not in traced],
    }


def compute_all(
    l3sm: Dict[str, Any],
    l3nm: Dict[str, Any],
    trace_entries: List[Dict[str, Any]],
) -> Dict[str, Any]:
    return {
        "coverage": compute_coverage(l3sm, trace_entries),
        "roundtrip_diff": compute_roundtrip_diff(l3sm, l3nm, trace_entries),
        "traceability": compute_traceability(l3nm, trace_entries),
    }