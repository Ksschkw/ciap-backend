from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy.inspection import inspect


def model_to_dict(instance: Any) -> dict[str, Any]:
    mapper = inspect(instance).mapper
    return {attribute.key: getattr(instance, attribute.key) for attribute in mapper.column_attrs}


def models_to_dicts(instances: Sequence[Any]) -> list[dict[str, Any]]:
    return [model_to_dict(instance) for instance in instances]