from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class WorkflowResult:
    status: str  # "awaiting_input" | "complete" | "error" | "cancelled"
    thread_id: str
    step: str | None = None
    prompt: str | None = None
    data: dict[str, Any] | None = None
    editable_fields: list[str] | None = None
    options: list[dict[str, Any]] | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"status": self.status, "thread_id": self.thread_id}
        if self.step is not None:
            d["step"] = self.step
        if self.prompt is not None:
            d["prompt"] = self.prompt
        if self.data is not None:
            d["data"] = self.data
        if self.editable_fields is not None:
            d["editable_fields"] = self.editable_fields
        if self.options is not None:
            d["options"] = self.options
        return d


@dataclass
class WorkflowInfo:
    name: str
    description: str
    steps: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "description": self.description, "steps": self.steps}
