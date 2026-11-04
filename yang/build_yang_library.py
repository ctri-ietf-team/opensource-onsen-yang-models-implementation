#!/usr/bin/env python3
"""Build yang-library.json from the local YANG modules using pyang.

The generated file follows the ietf-yang-library modules-state format
required by yangson's DataModel.from_file().
"""
import json
import os
import sys

from pyang import context
from pyang.repository import FileRepository

HERE = os.path.dirname(os.path.abspath(__file__))

MODULES = [
    "ietf-yang-types",
    "ietf-inet-types",
    "ietf-schedule",
    "ietf-l3vpn-svc",
    "ietf-l3vpn-ntw",
    "ietf-l3vpn-svc-dynamic-ext",
    "ietf-l3vpn-ntw-ext",
]


def main() -> int:
    repo = FileRepository(HERE)
    ctx = context.Context(repo)
    for name in MODULES:
        path = os.path.join(HERE, name + ".yang")
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        ctx.add_module(name, text)

    modules_state = {
        "ietf-yang-library:modules-state": {
            "module-set-id": "l3vpn-mapping-core-subset",
            "module": [],
        }
    }
    for name in MODULES:
        mod = ctx.get_module(name)
        if mod is None:
            print(f"ERROR: module {name} not found", file=sys.stderr)
            return 1
        rev = mod.search_one("revision")
        revision = rev.arg if rev is not None else "1970-01-01"
        entry = {
            "name": name,
            "revision": revision,
            "namespace": mod.search_one("namespace").arg,
            "prefix": mod.search_one("prefix").arg,
            "conformance-type": "implement",
            "feature": [],
        }
        for feat in mod.search("feature"):
            entry["features"].append(feat.arg)
        modules_state["ietf-yang-library:modules-state"]["module"].append(entry)

    out = os.path.join(HERE, "yang-library.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(modules_state, f, indent=2, ensure_ascii=False)
    print(f"Wrote {out} with {len(MODULES)} modules")
    return 0


if __name__ == "__main__":
    sys.exit(main())