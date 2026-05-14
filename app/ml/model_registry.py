from __future__ import annotations

import pickle
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class ModelRegistry:
    models: dict[str, Any] = field(default_factory=dict)

    def register(self, name: str, model: Any) -> None:
        self.models[name] = model

    def has(self, name: str) -> bool:
        return name in self.models

    def get(self, name: str) -> Any:
        if name not in self.models:
            raise KeyError(f"Model not registered: {name}")
        return self.models[name]

    def load_from_file(self, name: str, path: str | Path) -> Any:
        file_path = Path(path)
        with file_path.open("rb") as file_handle:
            model = pickle.load(file_handle)
        self.register(name, model)
        return model

    def save_to_file(self, name: str, path: str | Path) -> Path:
        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with file_path.open("wb") as file_handle:
            pickle.dump(self.get(name), file_handle)
        return file_path


model_registry = ModelRegistry()
