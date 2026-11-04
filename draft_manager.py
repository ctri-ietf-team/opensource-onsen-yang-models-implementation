"""Draft & mapping management for the L3VPN mapping app.

Researcher-facing extension hooks:

  - upload a new YANG draft per model layer (business / network / device):
      pyang compile check -> save under yang/drafts/<layer>/ -> rebuild
      yang-library.json -> reload the yangson DataModel -> extract the
      feature tree (containers / lists / leaves / types) for the UI.
  - define cross-layer mapping relations, either as a text draft
      ("[R7.1-01:] l3sm:vpn-service/vpn-id -> l3nm:vpn-service/vpn-id (COPY)")
      or as table rows; parsed rules are persisted and applied on the next
      mapping run (COPY / DROP / DERIVE on resolved instance paths).
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from pyang import context
from pyang.repository import FileRepository
from yangson import DataModel

HERE = os.path.dirname(os.path.abspath(__file__))
YANG_DIR = os.path.join(HERE, "yang")
LIBRARY = os.path.join(YANG_DIR, "yang-library.json")
DRAFTS_DIR = os.path.join(YANG_DIR, "drafts")
MAPPINGS_DIR = os.path.join(HERE, "mappings")
DYNAMIC_RULES_FILE = os.path.join(MAPPINGS_DIR, "dynamic-rules.json")

LAYER_LABEL = {
    "business": "业务模型 (L3SM)",
    "network": "网络模型 (L3NM)",
    "device": "设备模型 (OpenConfig)",
}

_dm: Optional[DataModel] = None


# ---------------------------------------------------------------------------
# DataModel lifecycle
# ---------------------------------------------------------------------------

def _search_dirs() -> List[str]:
    """yangson search dirs: yang/ root plus every layer draft dir."""
    dirs = [YANG_DIR]
    for layer in LAYER_LABEL:
        d = os.path.join(DRAFTS_DIR, layer)
        if os.path.isdir(d):
            dirs.append(d)
    return dirs


def init_dm() -> DataModel:
    global _dm
    _dm = DataModel.from_file(LIBRARY, _search_dirs())
    return _dm


def get_dm() -> DataModel:
    if _dm is None:
        init_dm()
    return _dm


def reload_dm() -> DataModel:
    return init_dm()


# ---------------------------------------------------------------------------
# YANG feature extraction
# ---------------------------------------------------------------------------

def _walk_statements(stmt: Any) -> List[Dict[str, Any]]:
    """Walk a pyang statement tree and collect model features."""
    nodes: List[Dict[str, Any]] = []
    for s in stmt.substmts:
        if s.keyword in ("container", "list", "leaf", "leaf-list"):
            node: Dict[str, Any] = {"name": s.arg, "kind": s.keyword}
            t = s.search_one("type")
            if t is not None:
                node["type"] = t.arg
            d = s.search_one("description")
            if d is not None:
                node["description"] = d.arg.strip().replace("\n", " ")[:140]
            if s.keyword in ("container", "list"):
                node["children"] = _walk_statements(s)
            nodes.append(node)
        elif s.keyword == "augment":
            aug: Dict[str, Any] = {
                "name": s.arg,
                "kind": "augment",
                "children": _walk_statements(s),
            }
            nodes.append(aug)
    return nodes


def _extract_module_name(yang_text: str) -> Optional[str]:
    m = re.search(r"^\s*module\s+([\w\-\.]+)\s*\{", yang_text, re.M)
    return m.group(1) if m else None


def parse_yang_features(yang_path: str) -> Dict[str, Any]:
    """Parse a YANG file and return its feature tree."""
    module_name = os.path.basename(yang_path)[:-5]
    repo = FileRepository(YANG_DIR)
    ctx = context.Context(repo)
    with open(yang_path, "r", encoding="utf-8") as f:
        text = f.read()
    ctx.add_module(module_name, text)
    mod = ctx.get_module(module_name)
    if mod is None:
        return {"name": module_name, "kind": "module", "children": []}
    rev = mod.search_one("revision")
    return {
        "name": mod.arg,
        "revision": rev.arg if rev is not None else "",
        "kind": "module",
        "children": _walk_statements(mod),
    }


def _compile_check(yang_text: str, module_name: str) -> List[str]:
    """Compile a YANG module with pyang; return error strings (empty = ok)."""
    repo = FileRepository(YANG_DIR)
    ctx = context.Context(repo)
    ctx.add_module(module_name, yang_text)
    errors = ctx.validate() or []
    return [str(e) for e in errors]


# ---------------------------------------------------------------------------
# Library rebuild
# ---------------------------------------------------------------------------

def _scan_modules() -> List[Tuple[str, str]]:
    """Scan yang/ (recursively) for .yang files -> [(module_name, path)]."""
    mods: List[Tuple[str, str]] = []
    for root, _dirs, files in os.walk(YANG_DIR):
        for f in sorted(files):
            if f.endswith(".yang"):
                mods.append((f[:-5], os.path.join(root, f)))
    return mods


def rebuild_library() -> int:
    """Rebuild yang-library.json from every .yang file under yang/."""
    repo = FileRepository(YANG_DIR)
    ctx = context.Context(repo)
    mods = _scan_modules()
    for name, path in mods:
        with open(path, "r", encoding="utf-8") as f:
            ctx.add_module(name, f.read())
    modules_state: Dict[str, Any] = {
        "ietf-yang-library:modules-state": {
            "module-set-id": "l3vpn-mapping-dynamic",
            "module": [],
        }
    }
    for name, _path in mods:
        mod = ctx.get_module(name)
        if mod is None:
            continue
        rev = mod.search_one("revision")
        entry = {
            "name": name,
            "revision": rev.arg if rev is not None else "1970-01-01",
            "namespace": mod.search_one("namespace").arg,
            "prefix": mod.search_one("prefix").arg,
            "conformance-type": "implement",
            "feature": [feat.arg for feat in mod.search("feature")],
        }
        modules_state["ietf-yang-library:modules-state"]["module"].append(entry)
    with open(LIBRARY, "w", encoding="utf-8") as f:
        json.dump(modules_state, f, indent=2, ensure_ascii=False)
    return len(modules_state["ietf-yang-library:modules-state"]["module"])


# ---------------------------------------------------------------------------
# Draft upload
# ---------------------------------------------------------------------------

def upload_draft(layer: str, draft_name: str, yang_text: str) -> Dict[str, Any]:
    """Validate, store and activate a researcher-uploaded YANG draft."""
    if layer not in LAYER_LABEL:
        return {"ok": False, "error": f"未知模型层级: {layer}（应为 business/network/device）"}
    module_name = _extract_module_name(yang_text)
    if not module_name:
        return {"ok": False, "error": "无法从文件内容中识别 module 名称（需以 'module <name> {' 开头）"}

    layer_dir = os.path.join(DRAFTS_DIR, layer)
    os.makedirs(layer_dir, exist_ok=True)
    target = os.path.join(layer_dir, module_name + ".yang")

    errors = _compile_check(yang_text, module_name)
    if errors:
        return {"ok": False, "error": "YANG 编译失败: " + "; ".join(errors[:5])}

    with open(target, "w", encoding="utf-8") as f:
        f.write(yang_text)

    try:
        count = rebuild_library()
        reload_dm()
    except Exception as e:  # noqa: BLE001
        os.remove(target)
        return {"ok": False, "error": f"模型库重建失败: {e}"}

    features = parse_yang_features(target)
    return {
        "ok": True,
        "layer": layer,
        "draft": draft_name,
        "module": module_name,
        "features": features,
        "library_modules": count,
    }


def list_drafts() -> Dict[str, List[Dict[str, str]]]:
    """List uploaded drafts per layer."""
    result: Dict[str, List[Dict[str, str]]] = {k: [] for k in LAYER_LABEL}
    for layer in LAYER_LABEL:
        layer_dir = os.path.join(DRAFTS_DIR, layer)
        if not os.path.isdir(layer_dir):
            continue
        for f in sorted(os.listdir(layer_dir)):
            if f.endswith(".yang"):
                result[layer].append({"module": f[:-5], "file": f})
    return result


# ---------------------------------------------------------------------------
# Mapping rule definition (text draft or table rows)
# ---------------------------------------------------------------------------

_RULE_RE = re.compile(
    r"^\s*(?:\[([Rr][A-Za-z0-9\.\-]*)\]\s*[:：]\s*"
    r"|\[([Rr][A-Za-z0-9\.\-]*):\]\s*"
    r"|([Rr][A-Za-z0-9\.\-]*)\s*[:：]\s*)?"
    r"(.+?)\s*->\s*(.+?)\s*\(([A-Za-z\*]+)\)\s*(?:#\s*(.*))?$"
)


def parse_mapping_text(text: str) -> List[Dict[str, str]]:
    """Parse a mapping-relation draft text into rule rows.

    Accepted line format:
        [R7.1-01:] l3sm:vpn-service/vpn-id -> l3nm:vpn-service/vpn-id (COPY) # note
    """
    rules: List[Dict[str, str]] = []
    for i, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("//"):
            continue
        m = _RULE_RE.match(line)
        if not m:
            rules.append({
                "id": f"R7.{i:02d}",
                "source": line,
                "target": "?",
                "op": "?",
                "note": "无法解析（格式: [ID:] 源路径 -> 目标路径 (OP)）",
            })
            continue
        rid = m.group(1) or m.group(2) or m.group(3)
        src, tgt, op, note = m.group(4), m.group(5), m.group(6), m.group(7)
        rules.append({
            "id": rid or f"R7.{i:02d}",
            "source": src.strip(),
            "target": tgt.strip(),
            "op": op.strip().upper(),
            "note": (note or "").strip(),
        })
    return rules


def save_dynamic_rules(rules: List[Dict[str, str]]) -> None:
    os.makedirs(MAPPINGS_DIR, exist_ok=True)
    with open(DYNAMIC_RULES_FILE, "w", encoding="utf-8") as f:
        json.dump(rules, f, ensure_ascii=False, indent=2)


def load_dynamic_rules() -> List[Dict[str, str]]:
    if os.path.exists(DYNAMIC_RULES_FILE):
        try:
            with open(DYNAMIC_RULES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError):
            return []
    return []


# ---------------------------------------------------------------------------
# Dynamic rule application on instances
# ---------------------------------------------------------------------------

def _split_path(path: str) -> List[str]:
    return [p.strip() for p in path.split("/") if p.strip()]


def _root_for(data: Dict[str, Any], prefix: str) -> Dict[str, Any]:
    if prefix in ("l3sm", "business"):
        return data.get("ietf-l3vpn-svc:l3vpn-svc", {})
    if prefix in ("l3nm", "network"):
        return data.get("ietf-l3vpn-ntw:l3vpn-ntw", {})
    return data


def _resolve(data: Dict[str, Any], path: str) -> List[Any]:
    """Resolve 'l3sm:seg/seg[...]/leaf' against an instance; list segments iterate."""
    prefix, _, rest = path.partition(":")
    root = _root_for(data, prefix)
    current: List[Any] = [root]
    for seg in _split_path(rest):
        nxt: List[Any] = []
        for node in current:
            if not isinstance(node, dict):
                continue
            if "[" in seg:
                name, _, keyexpr = seg.partition("[")
                keyexpr = keyexpr.rstrip("]")
                key, _, val = keyexpr.partition("=")
                items = node.get(name, [])
                if isinstance(items, list):
                    for it in items:
                        if isinstance(it, dict) and it.get(key) == val:
                            nxt.append(it)
                elif isinstance(items, dict):
                    nxt.append(items)
            else:
                v = node.get(seg)
                if v is None:
                    # bare name may match a module-prefixed key (augment nodes)
                    for key in node:
                        if key.split(":", 1)[-1] == seg:
                            v = node[key]
                            break
                if isinstance(v, list):
                    nxt.extend(v)
                elif v is not None:
                    nxt.append(v)
        current = nxt
        if not current:
            break
    return current


def _set_path(data: Dict[str, Any], path: str, value: Any) -> bool:
    """Write value at 'l3nm:seg/seg[...]/leaf', creating intermediate nodes."""
    prefix, _, rest = path.partition(":")
    if prefix in ("l3sm", "business"):
        root = data.setdefault("ietf-l3vpn-svc:l3vpn-svc", {})
    elif prefix in ("l3nm", "network"):
        root = data.setdefault("ietf-l3vpn-ntw:l3vpn-ntw", {})
    else:
        root = data
    segs = _split_path(rest)
    if not segs:
        return False
    node = root
    for seg in segs[:-1]:
        if "[" in seg:
            name, _, keyexpr = seg.partition("[")
            keyexpr = keyexpr.rstrip("]")
            key, _, val = keyexpr.partition("=")
            items = node.setdefault(name, [])
            if not isinstance(items, list):
                items = [items]
                node[name] = items
            found = None
            for it in items:
                if isinstance(it, dict) and it.get(key) == val:
                    found = it
                    break
            if found is None:
                found = {key: val}
                items.append(found)
            node = found
        else:
            key = seg
            if key not in node:
                for k in node:
                    if k.split(":", 1)[-1] == seg:
                        key = k
                        break
            nxt = node.get(key)
            if isinstance(nxt, list):
                # bare list segment: descend into the first entry (or create one)
                if nxt and isinstance(nxt[0], dict):
                    node = nxt[0]
                else:
                    nxt.append({})
                    node = nxt[-1]
            elif not isinstance(nxt, dict):
                nxt = {}
                node[key] = nxt
                node = nxt
            else:
                node = nxt
    last = segs[-1]
    if "[" in last:
        name, _, keyexpr = last.partition("[")
        keyexpr = keyexpr.rstrip("]")
        key, _, val = keyexpr.partition("=")
        items = node.setdefault(name, [])
        if not isinstance(items, list):
            items = [items]
            node[name] = items
        for it in items:
            if isinstance(it, dict) and it.get(key) == val:
                if isinstance(value, dict):
                    it.update(value)
                else:
                    it[key] = value
                return True
        items.append({key: val, **(value if isinstance(value, dict) else {})})
        return True
    last_key = last
    if last_key not in node:
        for k in node:
            if k.split(":", 1)[-1] == last:
                last_key = k
                break
    node[last_key] = value
    return True


def apply_dynamic_rules(
    l3sm: Dict[str, Any],
    l3nm: Dict[str, Any],
    rules: List[Dict[str, str]],
    trace: Any,
) -> List[str]:
    """Apply researcher-defined rules; record trace entries. Returns applied ids."""
    applied: List[str] = []
    for r in rules:
        op = (r.get("op") or "?").upper()
        src, tgt = r.get("source", ""), r.get("target", "")
        rid = r.get("id", "R7.00")
        if op == "COPY":
            vals = _resolve(l3sm, src)
            if vals:
                _set_path(l3nm, tgt, vals[0])
                trace.record(rid, "#R", src, tgt, "COPY", vals[0], r.get("note", ""))
                applied.append(rid)
            else:
                trace.record(rid, "#R", src, tgt, "COPY", None, "源字段不存在，跳过")
        elif op == "DROP":
            trace.record(rid, "#R", src, "-", "DROP", None, r.get("note", ""))
            applied.append(rid)
        elif op == "DERIVE":
            vals = _resolve(l3sm, src)
            v = vals[0] if vals else None
            _set_path(l3nm, tgt, v)
            trace.record(rid, "#R", src, tgt, "DERIVE", v, r.get("note", ""))
            applied.append(rid)
        else:
            trace.record(rid, "#R", src, tgt, op, None, "未识别的操作类型")
    return applied