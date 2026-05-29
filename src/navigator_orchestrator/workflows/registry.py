from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from navigator_orchestrator.workflows.types import WorkflowInfo


@dataclass
class WorkflowDefinition:
    name: str
    builder: Callable
    description: str
    steps: list[str]


class WorkflowRegistry:
    def __init__(self) -> None:
        self._workflows: dict[str, WorkflowDefinition] = {}

    def register(
        self,
        name: str,
        builder: Callable,
        description: str,
        steps: list[str],
    ) -> None:
        self._workflows[name] = WorkflowDefinition(
            name=name,
            builder=builder,
            description=description,
            steps=steps,
        )

    def get(self, name: str) -> WorkflowDefinition:
        try:
            return self._workflows[name]
        except KeyError:
            raise KeyError(f"Unknown workflow: {name!r}") from None

    def list_workflows(self) -> list[WorkflowInfo]:
        return [
            WorkflowInfo(name=d.name, description=d.description, steps=d.steps)
            for d in self._workflows.values()
        ]

    def names(self) -> list[str]:
        return list(self._workflows.keys())
