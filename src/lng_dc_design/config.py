from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib


@dataclass(slots=True)
class CitationNode:
    path: str
    source_id: str
    description: str


@dataclass(slots=True)
class ProjectConfig:
    path: Path
    raw: dict
    values: dict
    citations: dict[str, CitationNode]


def _unwrap(node: object, path: tuple[str, ...], citations: dict[str, CitationNode]) -> object:
    if isinstance(node, dict):
        if "value" in node and "source_id" in node:
            dotted = ".".join(path)
            citations[dotted] = CitationNode(
                path=dotted,
                source_id=str(node["source_id"]),
                description=str(node.get("description", "")),
            )
            return node["value"]
        return {key: _unwrap(value, path + (key,), citations) for key, value in node.items()}
    if isinstance(node, list):
        return [_unwrap(item, path, citations) for item in node]
    return node


def load_config(path: str | Path) -> ProjectConfig:
    config_path = Path(path).resolve()
    with config_path.open("rb") as handle:
        raw = tomllib.load(handle)
    citations: dict[str, CitationNode] = {}
    values = _unwrap(raw, tuple(), citations)
    return ProjectConfig(path=config_path, raw=raw, values=values, citations=citations)
