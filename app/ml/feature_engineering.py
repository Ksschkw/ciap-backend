from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def _flatten(prefix: str, value: Any, output: dict[str, float]) -> None:
    if isinstance(value, bool):
        output[prefix] = float(int(value))
    elif isinstance(value, (int, float)):
        output[prefix] = float(value)
    elif isinstance(value, Mapping):
        for key, nested_value in value.items():
            nested_prefix = f"{prefix}.{key}" if prefix else str(key)
            _flatten(nested_prefix, nested_value, output)
    elif isinstance(value, list):
        output[f"{prefix}.count" if prefix else "count"] = float(len(value))


def extract_numeric_features(source: Mapping[str, Any]) -> dict[str, float]:
    features: dict[str, float] = {}
    for key, value in source.items():
        _flatten(str(key), value, features)
    return features
