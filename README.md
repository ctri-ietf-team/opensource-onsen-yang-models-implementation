---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '4846aa9c-8fe7-4bbd-9735-9b5a1a7eedfc'
  PropagateID: '4846aa9c-8fe7-4bbd-9735-9b5a1a7eedfc'
  ReservedCode1: '8be4e946-2ee9-4c99-875f-448aee77ee7a'
  ReservedCode2: '8be4e946-2ee9-4c99-875f-448aee77ee7a'
---

# L3VPN YANG Models Mapping and Validation

> An interactive lab that performs **lossless model mapping** across three layers:
> **L3SM (service model, RFC 8299) → L3NM (network model, RFC 9182) → device models (OpenConfig)**,
> with YANG validation and end-to-end mapping consistency verification.

Single-package deployment: **backend** (FastAPI + mapping rule engine + YANG validation)
and **frontend** (mapping visualization page) in one folder. The Windows portable build
bundles a Python 3.11 runtime with all dependencies, so the target machine needs
**no Python installation, no dependency setup, and no network access** — just unzip
and double-click, like any ordinary Windows application.

## Repository Layout

```
l3vpn-mapping-app/
├── start.bat           # one-click launcher (Windows, just double-click)
├── start.sh            # one-click launcher (Linux / macOS, needs Python installed)
├── app.py              # backend entry (FastAPI: API + WebSocket + frontend hosting)
├── draft_manager.py    # draft upload / feature parsing / mapping definitions / dynamic rules
├── engine/             # mapping rule engine (45 built-in rules + trace + lossless metrics)
├── yang/               # YANG assets (7 modules + yang-library.json + drafts/ upload dir)
├── mappings/           # researcher-defined mapping rules (dynamic-rules.json)
├── web/
│   └── lab-page1.html  # frontend page (port-adaptive + researcher extension UI)
└── runtime/            # bundled Windows Python 3.11 runtime + all dependencies (do not delete)
```

## Quick Start (Windows)

1. Copy / unzip the whole folder to any location (Chinese characters and spaces in the path are fine);
2. Double-click `start.bat`;
3. About 3 seconds after the window shows `URL: http://127.0.0.1:8000`, the browser opens automatically.

> No Python installation, no network access, no configuration required.
> Closing the launcher window stops the service.
> A **中文 / EN** language toggle is available at the top right of the page for demos.

### Linux / macOS (requires Python 3.10+)
```bash
bash start.sh        # installs dependencies automatically on first run (needs network)
```

### Manual start (any platform)
```bash
python3 -m uvicorn app:app --host 127.0.0.1 --port 8000
# then open http://127.0.0.1:8000 in a browser
```

## Using the Lab

1. On page load, the frontend connects via WebSocket and triggers a **real-engine** mapping demo automatically;
2. The left column shows the L3SM input (editable); click **「开始映射」(Start Mapping)** to re-run;
3. Mapping pushes trace events in real time: source-field highlight → rule-hit pulse → target-field write;
4. The metrics bar updates live: **coverage / round-trip diff / traceability**;
5. If the backend is unavailable (e.g. the frontend is copied alone), the page automatically falls back to its built-in simulation engine.

## Researcher Extensions (C1)

### 1. Draft upload (left column)

Each model layer (service L3SM / network L3NM / device OpenConfig) has its own draft box:

- enter a **draft name** (e.g. `draft-research-ext-00`);
- click **「上传 YANG draft」(Upload YANG draft)** and pick a `.yang` file;
- the backend then compiles it with pyang → saves it to `yang/drafts/<layer>/` →
  rebuilds `yang-library.json` → reloads the yangson DataModel;
- the left column shows the currently active module name after a successful upload.

### 2. Model feature tree (middle column)

Each model section has a collapsible **「模型特征（YANG 解析）」(Model Features, YANG-parsed)** panel:

- shows the parameter tree parsed from the current draft (containers / lists / leaves / types / descriptions);
- refreshes automatically after a new draft is uploaded — new parameters appear immediately;
- augment nodes are marked with `⊕` together with their mount path.

### 3. Mapping-rule definition (right column)

The **「映射关系定义（研究人员）」(Mapping Definition, researcher)** panel accepts two input styles:

- **draft text**: one rule per line, e.g.
  ```
  [R7.1-01:] l3sm:vpn-services/vpn-service/vpn-id -> l3nm:vpn-services/vpn-service/vpn-id (COPY) # note
  l3sm:vpn-services/vpn-service/vpn-name -> - (DROP)
  ```
  Supported operations: `COPY` / `DROP` / `DERIVE`; text after `#` is a comment.
- **table**: add rows dynamically (ID / source field / target field / operation / note).

Submitted rules are persisted to `mappings/dynamic-rules.json` and **take effect on the next
mapping run automatically**; dynamic rules are tagged with a `#R` batch in the trace and remain traceable.

> Path format: `l3sm:...` / `l3nm:...`; list entries can be addressed with `xxx[key=value]`;
> containers introduced via augment need the module prefix (e.g. `ietf-l3vpn-svc-research-ext:research`).

## Ports and Configuration

| Env var  | Default    | Description                       |
|----------|------------|-----------------------------------|
| `PORT`   | `8000`     | service port                      |
| `HOST`   | `127.0.0.1` | listen address (start.sh)        |

The frontend is port-adaptive: it reads the port from the page URL, so changing the port never requires frontend changes.

## API

| Method | Path | Description                                       |
|--------|------|---------------------------------------------------|
| GET  | `/`       | frontend page                              |
| GET  | `/health` | health check (includes dynamic rule count) |
| POST | `/api/map`| L3SM input (RFC 7951) → L3NM + device models + trace + metrics |
| WS   | `/ws/trace` | real-time trace events during mapping     |
| GET  | `/api/models` | feature trees of the three model layers + current drafts |
| POST | `/api/draft/upload` | upload a YANG draft (multipart)     |
| GET  | `/api/drafts` | list of uploaded drafts                     |
| POST | `/api/mapping/define` | define mapping rules (text / table) |
| GET  | `/api/mappings` | list of defined mapping rules             |

## Lossless Metrics (TC-MAP-001~003)

| Metric        | Target | Measured |
|---------------|--------|----------|
| Coverage      | 100%   | 100%     |
| Round-trip diff | =0   | =0       |
| Traceability  | 100%   | 100%     |
| L3NM validation | valid | valid   |

## Dependencies

- **Windows portable build**: zero setup (bundled `runtime/`, Python 3.11 + all dependencies included)
- **Running from source (any platform)**: Python ≥ 3.10, then:

```bash
python3 -m pip install --user -r requirements.txt
```

Dependency list: fastapi / uvicorn (service), yangson (instance validation), pyang (YANG compilation),
python-multipart (draft upload), wsproto (WebSocket real-time trace).

## Engine Self-Test (optional)

```bash
python3 -m engine.cli   # 3 TCs all PASS, writes .tmp/mapping-report.json
```

## Author

**Cancan Huang** (China Telecom) — <huangcanc@chinatelecom.cn>

Open-sourced for L3VPN model-mapping demonstration and validation in the IETF ONSEN
context. Feedback and collaboration are welcome.

> AI生成