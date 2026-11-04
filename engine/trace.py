"""Trace recording for the L3SM -> L3NM -> device mapping engine."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List


@dataclass
class TraceEntry:
    """A single mapping trace entry."""

    rule_id: str
    batch: str
    source: str
    target: str
    op: str
    value: Any = None
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d


class TraceRecorder:
    """Collects mapping trace entries in order."""

    def __init__(self) -> None:
        self._entries: List[TraceEntry] = []

    def record(
        self,
        rule_id: str,
        batch: str,
        source: str,
        target: str,
        op: str,
        value: Any = None,
        note: str = "",
    ) -> None:
        self._entries.append(
            TraceEntry(
                rule_id=rule_id,
                batch=batch,
                source=source,
                target=target,
                op=op,
                value=value,
                note=note,
            )
        )

    @property
    def entries(self) -> List[TraceEntry]:
        return self._entries

    def __len__(self) -> int:
        return len(self._entries)

    def to_json(self) -> str:
        return json.dumps(
            [e.to_dict() for e in self._entries], ensure_ascii=False, indent=2
        )

    def to_dict_list(self) -> List[Dict[str, Any]]:
        return [e.to_dict() for e in self._entries]