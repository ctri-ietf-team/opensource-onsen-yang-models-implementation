---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '87352d38-8c36-4a40-a56d-2ef552e1caee'
  PropagateID: '87352d38-8c36-4a40-a56d-2ef552e1caee'
  ReservedCode1: '4384edd3-f9d9-47d0-9954-b6db079e76d8'
  ReservedCode2: '4384edd3-f9d9-47d0-9954-b6db079e76d8'
---

# LXVPN YANG Models Mapping and Validation

> **Interactive LXVPN lossless model mapping and validation: LXSM → LXNM → device models,
> with YANG validation and end-to-end mapping consistency verification.**

## Scope and Premises

This project targets the **mapping and validation between the YANG models published in the
existing RFCs and the YANG models extended with new features in the future** within the scope
of the ONSEN work. Two premises frame everything below.

### Premise 1 — LXVPN is the umbrella; L3VPN is the first step

The framework is named **LXVPN** because it is meant to cover multiple VPN services in the
ONSEN context, not L3VPN alone. The current release implements **L3VPN as the first step**.
More services will follow, e.g. **L2VPN** and **ACaaS**.

### Premise 2 — this web page is only the visualization part of the whole experiment

The GitHub web page covers the model-mapping part: visualizing how the service model, the
network model and the device model are mapped to each other (L3SM → L3NM → device models),
together with YANG validation and mapping-consistency verification.

The complete experiment goes one step further: once the device-model configuration is
produced, it is **downloaded to real devices in the CTRI (China Telecom Research Institute)
lab and verified end-to-end, to check whether the service actually runs**. That step is
**not yet presented in the web page** — the page shows the mapping/validation stage only.

---

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

## Researcher Extensions

The page is organized as **three columns: left = model inputs, middle = mapping visualization,
right = mapping-rule definition**. The sections below follow that layout.

### 1. Left column — extend a YANG model and upload your draft

If you are a researcher and have **new extensions for a given YANG model**, the first thing
to do is **write an Internet-Draft that describes the extension**, and then upload it to the
corresponding draft box in the **left column**.

- **Service (business) model.** Write a draft describing your extension of the service model,
  named like `draft-<authurname>-onsen-XX-ext-service-yang-model` (`<authurname>` = the author
  name), and upload it to the orchestration dialog box of the business layer in the left
  column. The service model currently in use is the **L3SM RFC (RFC 8299)**.
- **Network model.** Then write a draft describing how the corresponding network model is
  extended with respect to the previous RFC, named like
  `draft-<authurname>-onsen-XX-ext-network-yang-model`, and upload it to the orchestration
  dialog box of the network layer in the left column. The network model currently in use is
  the **L3NM RFC (RFC 9182)**.
- **Device model.** The device layer (OpenConfig) has the same draft box, in case the
  extension needs a device-side counterpart.

Upload flow (handled automatically by the backend):

1. enter the **draft name** in the box;
2. click **「上传 YANG draft」(Upload YANG draft)** and pick the `.yang` file;
3. the backend compiles it with pyang → saves it to `yang/drafts/<layer>/` →
   rebuilds `yang-library.json` → reloads the yangson DataModel;
4. the left column then shows the currently active module name, and the parsed feature tree
   appears in the middle column.

### 2. Middle column — visualization of the cross-layer mapping

The middle column **visualizes the mapping relationships among the service model, the
network model and the device model** — the three-layer link for the same service instance,
with field-level highlights and causal numbering.

**The mapping shown here is driven by the mapping rules defined in the right column.** In
other words: right column = the rules (the "why"), middle column = the visualized mapping
(the "what"). Each model section also has a collapsible **「模型特征（YANG 解析）」(Model
Features, YANG-parsed)** panel showing the parameter tree parsed from the currently active
draft (containers / lists / leaves / types / descriptions, with `⊕` marking augment nodes
and their mount paths).

### 3. Right column — mapping-rule definition

This column is where **researchers define the parameter-level mapping relationships between
the YANG models of the different layers**.

The mapping relationships of all layers for **L3VPN have already been parsed** and can be
browsed as a list. When a researcher adds new features to the model RFCs at any layer, the
mapping rules can be supplied in two ways:

- **Enter the rules manually**, in the supported format — one rule per line:
  ```
  [R7.1-01:] l3sm:vpn-services/vpn-service/vpn-id -> l3nm:vpn-services/vpn-service/vpn-id (COPY) # note
  l3sm:vpn-services/vpn-service/vpn-name -> - (DROP)
  ```
  Supported operations: `COPY` / `DROP` / `DERIVE`; text after `#` is a comment. A table
  editor is also available (ID / source field / target field / operation / note).
- **Upload the deployment guidance of a service** — the backend parses the mapping rules of
  each layer out of it automatically.

Submitted rules are persisted to `mappings/dynamic-rules.json` and **take effect on the next
mapping run automatically**; dynamic rules are tagged with a `#R` batch in the trace and remain traceable.

> Path format: `l3sm:...` / `l3nm:...`; list entries can be addressed with `xxx[key=value]`;
> containers introduced via augment need the module prefix (e.g. `ietf-l3vpn-svc-research-ext:research`).

### 4. Mapping checks — and what happens when everything passes

**Gap indication.** If the mapping relationships are wrong, missing or incomplete, the web
page **displays the missing parts** — which provides concrete evidence for identifying gaps
in the IETF (查漏补缺).

**From mapping to real devices.** If all three layers of the mapping pass validation, the
resulting **device-model configuration is downloaded to real devices in the China Telecom
(CTRI) lab**, and the service is verified end-to-end to check whether it actually runs.
As stated in Premise 2, this real-device verification step is currently **outside the web
page** and will be presented later.

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

Open-sourced for LXVPN model-mapping demonstration and validation in the IETF ONSEN
context. Feedback and collaboration are welcome.

> AI生成