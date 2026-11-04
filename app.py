"""L3VPN mapping app: self-contained FastAPI service (backend + frontend).

Run from the app root directory:

    python3 -m uvicorn app:app --host 127.0.0.1 --port 8000

or simply use the one-click launcher (start.sh / start.bat).

Endpoints:
  GET  /                    frontend page (web/lab-page1.html)
  GET  /health              health check
  POST /api/map             map an L3SM instance -> L3NM + devices + trace
  WS   /ws/trace            receive trace events pushed during mapping
  GET  /api/models          feature trees of the three model layers
  POST /api/draft/upload    upload a new YANG draft (multipart: layer/draft_name/file)
  GET  /api/drafts          list uploaded drafts per layer
  POST /api/mapping/define  define cross-layer mapping relations (text or table)
  GET  /api/mappings        list researcher-defined mapping rules
  /static/*                 static assets (web/)
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any, Dict, List, Set

from fastapi import FastAPI, File, Form, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from yangson import DataModel

import draft_manager as dmgr
from engine.mapper import run_mapping
from engine.metrics import compute_all

# ---- paths are relative to this file, so the whole app folder is portable ----
HERE = os.path.dirname(os.path.abspath(__file__))
YANG_DIR = os.path.join(HERE, "yang")
WEB_DIR = os.path.join(HERE, "web")
INDEX_HTML = os.path.join(WEB_DIR, "lab-page1.html")

app = FastAPI(title="L3VPN Mapping App", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

dm: DataModel = dmgr.init_dm()


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: Set[WebSocket] = set()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.add(ws)

    def disconnect(self, ws: WebSocket) -> None:
        self._connections.discard(ws)

    async def broadcast(self, message: Dict[str, Any]) -> None:
        for ws in list(self._connections):
            try:
                await ws.send_json(message)
            except Exception:  # noqa: BLE001 - drop dead connections
                self._connections.discard(ws)


manager = ConnectionManager()


class MapRequest(BaseModel):
    l3sm: Dict[str, Any]


class MappingDefineRequest(BaseModel):
    mode: str = "text"          # "text" | "table"
    text: str = ""              # used when mode == "text"
    rows: List[Dict[str, str]] = []  # used when mode == "table"


# ---------------------------------------------------------------------------
# health & trace
# ---------------------------------------------------------------------------

@app.get("/health")
async def health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "engine": "l3vpn-mapping-engine",
        "dynamic_rules": len(dmgr.load_dynamic_rules()),
    }


@app.websocket("/ws/trace")
async def ws_trace(ws: WebSocket) -> None:
    await manager.connect(ws)
    try:
        while True:
            await ws.receive_text()  # keep the connection alive
    except WebSocketDisconnect:
        manager.disconnect(ws)


# ---------------------------------------------------------------------------
# mapping
# ---------------------------------------------------------------------------

@app.post("/api/map")
async def map_l3sm(req: MapRequest) -> Dict[str, Any]:
    """Validate the L3SM instance, run the mapping engine (built-in rules +
    researcher-defined dynamic rules), push trace over WebSocket."""
    # 1. validate L3SM against the YANG data model
    try:
        dm.from_raw(req.l3sm)
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"L3SM validation failed: {e}"}

    # 2. run the mapping engine
    result = run_mapping(req.l3sm)
    # 2b. apply researcher-defined dynamic rules on top
    dynamic = dmgr.load_dynamic_rules()
    if dynamic:
        dmgr.apply_dynamic_rules(req.l3sm, result.l3nm, dynamic, result.trace)
    entries = result.trace.to_dict_list()
    metrics = compute_all(req.l3sm, result.l3nm, entries)

    # 3. push trace events over WebSocket
    await manager.broadcast({
        "type": "mapping_start",
        "total": len(entries),
        "rules": len(entries),
    })
    for e in entries:
        await manager.broadcast({"type": "trace", "entry": e})
        await asyncio.sleep(0.015)
    await manager.broadcast({
        "type": "mapping_done",
        "metrics": {
            "coverage_rate": metrics["coverage"]["rate"],
            "roundtrip_diff": metrics["roundtrip_diff"]["diff_count"],
            "traceability_rate": metrics["traceability"]["rate"],
        },
    })

    # 4. return the full result
    return {
        "ok": True,
        "l3nm": result.l3nm,
        "devices": result.devices,
        "metrics": metrics,
        "trace": entries,
        "dynamic_rules": len(dynamic),
    }


# ---------------------------------------------------------------------------
# model features & draft upload (researcher extension hooks)
# ---------------------------------------------------------------------------

_DEVICE_FEATURES: Dict[str, Any] = {
    "name": "openconfig-network-instance",
    "revision": "2022-01-10",
    "kind": "module",
    "children": [
        {"name": "network-instances", "kind": "container", "children": [
            {"name": "network-instance", "kind": "list", "children": [
                {"name": "name", "kind": "leaf", "type": "string"},
                {"name": "type", "kind": "leaf", "type": "identityref"},
                {"name": "rd", "kind": "leaf", "type": "string"},
                {"name": "route-targets", "kind": "container", "children": [
                    {"name": "rt", "kind": "leaf", "type": "string"},
                    {"name": "type", "kind": "leaf", "type": "identityref"},
                ]},
                {"name": "interfaces", "kind": "container", "children": [
                    {"name": "interface", "kind": "list", "children": [
                        {"name": "name", "kind": "leaf", "type": "string"},
                        {"name": "ipv4", "kind": "container", "children": [
                            {"name": "address", "kind": "leaf-list", "type": "string"},
                        ]},
                    ]},
                ]},
                {"name": "protocols", "kind": "container", "children": [
                    {"name": "bgp", "kind": "container", "children": [
                        {"name": "neighbor", "kind": "list", "children": [
                            {"name": "remote-address", "kind": "leaf", "type": "string"},
                            {"name": "peer-as", "kind": "leaf", "type": "uint32"},
                        ]},
                    ]},
                    {"name": "static", "kind": "container", "children": [
                        {"name": "route", "kind": "list", "children": [
                            {"name": "prefix", "kind": "leaf", "type": "string"},
                            {"name": "next-hop", "kind": "leaf", "type": "string"},
                        ]},
                    ]},
                ]},
            ]},
        ]},
    ],
}


def _features_for_layer(layer: str) -> Dict[str, Any]:
    """Feature tree for a layer: uploaded draft first, else default."""
    layer_dir = os.path.join(dmgr.DRAFTS_DIR, layer)
    if os.path.isdir(layer_dir):
        files = sorted(f for f in os.listdir(layer_dir) if f.endswith(".yang"))
        if files:
            path = os.path.join(layer_dir, files[-1])
            feats = dmgr.parse_yang_features(path)
            feats["draft"] = files[-1][:-5]
            return feats
    if layer == "device":
        feats = json.loads(json.dumps(_DEVICE_FEATURES))
        feats["draft"] = "openconfig-network-instance"
        return feats
    # business / network: parse the core module
    mod = "ietf-l3vpn-svc" if layer == "business" else "ietf-l3vpn-ntw"
    path = os.path.join(YANG_DIR, mod + ".yang")
    feats = dmgr.parse_yang_features(path)
    feats["draft"] = mod
    return feats


@app.get("/api/models")
async def get_models() -> Dict[str, Any]:
    """Feature trees for business / network / device layers."""
    return {
        "layers": {
            layer: {
                "label": dmgr.LAYER_LABEL[layer],
                "draft": _features_for_layer(layer).get("draft", ""),
                "features": _features_for_layer(layer),
            }
            for layer in ("business", "network", "device")
        },
        "dynamic_rules": dmgr.load_dynamic_rules(),
    }


@app.get("/api/drafts")
async def get_drafts() -> Dict[str, Any]:
    return {"ok": True, "drafts": dmgr.list_drafts()}


@app.post("/api/draft/upload")
async def upload_draft(
    layer: str = Form(...),
    draft_name: str = Form(...),
    file: UploadFile = File(...),
) -> Dict[str, Any]:
    """Upload a new YANG draft for a model layer."""
    content = (await file.read()).decode("utf-8", errors="replace")
    if not content.strip():
        return {"ok": False, "error": "上传文件为空"}
    result = dmgr.upload_draft(layer, draft_name, content)
    if result.get("ok"):
        # refresh the shared DataModel used by /api/map
        global dm
        dm = dmgr.get_dm()
    return result


# ---------------------------------------------------------------------------
# mapping relation definition (researcher hook)
# ---------------------------------------------------------------------------

@app.post("/api/mapping/define")
async def define_mapping(req: MappingDefineRequest) -> Dict[str, Any]:
    """Parse and persist researcher-defined mapping relations."""
    if req.mode == "table":
        rules = [
            {
                "id": (r.get("id") or f"R7.{i:02d}"),
                "source": r.get("source", "").strip(),
                "target": r.get("target", "").strip(),
                "op": (r.get("op") or "COPY").strip().upper(),
                "note": r.get("note", "").strip(),
            }
            for i, r in enumerate(req.rows, 1)
            if r.get("source") or r.get("target")
        ]
    else:
        rules = dmgr.parse_mapping_text(req.text or "")

    if not rules:
        return {"ok": False, "error": "未解析到任何映射规则"}

    dmgr.save_dynamic_rules(rules)
    return {
        "ok": True,
        "parsed": rules,
        "total": len(rules),
        "invalid": [r for r in rules if r["op"] == "?"],
    }


@app.get("/api/mappings")
async def get_mappings() -> Dict[str, Any]:
    return {"ok": True, "rules": dmgr.load_dynamic_rules()}


# ---------------------------------------------------------------------------
# frontend
# ---------------------------------------------------------------------------

@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(INDEX_HTML)


if os.path.isdir(WEB_DIR):
    app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


def main() -> None:
    import uvicorn

    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()