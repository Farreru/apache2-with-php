"""Shared helpers for the Apache runner scripts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.yml"


def parse_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Config {path} not found")

    data: dict[str, Any] = {}
    stack: list[tuple[dict[str, Any], int]] = [(data, -1)]

    def parse_scalar(value: str) -> Any:
        value = value.strip()
        if not value:
            return ""
        if value.lower() in {"true", "false"}:
            return value.lower() == "true"
        if value.isdigit():
            return int(value)
        return value

    with path.open() as fh:
        for raw in fh:
            stripped = raw.rstrip("\n")
            if not stripped.strip() or stripped.lstrip().startswith("#"):
                continue
            indent = len(raw) - len(raw.lstrip())
            line = raw[indent:].rstrip("\n")
            key, sep, value = line.partition(":")
            if not sep:
                raise ValueError(f"Expected ':' in line: {line}")
            key = key.strip()
            value = value.strip()
            while stack and indent <= stack[-1][1]:
                stack.pop()
            parent = stack[-1][0]
            if value == "":
                new_dict: dict[str, Any] = {}
                parent[key] = new_dict
                stack.append((new_dict, indent))
            else:
                parent[key] = parse_scalar(value)
    return data


def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
