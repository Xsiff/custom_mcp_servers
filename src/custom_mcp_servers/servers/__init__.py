"""Definitions for the MCP servers bundled with this project."""

from __future__ import annotations

import importlib
import pkgutil

from ..server_spec import ServerSpec


def discover() -> tuple[ServerSpec, ...]:
    """Discover server definitions without a core-code registry."""
    specs: list[ServerSpec] = []
    for module_info in pkgutil.iter_modules(__path__):
        if module_info.name.startswith("_"):
            continue
        module = importlib.import_module(f"{__name__}.{module_info.name}")
        spec = getattr(module, "SPEC", None)
        if isinstance(spec, ServerSpec):
            specs.append(spec)
    return tuple(sorted(specs, key=lambda spec: spec.name))


def find(name: str) -> ServerSpec | None:
    return next((spec for spec in discover() if spec.name == name), None)
