"""Shared low-level types for the ported agent loop.

Ported from huggingface/tau ``tau_agent/types.py`` v0.4.1 (MIT), unmodified.
"""

from __future__ import annotations

# Pydantic needs PEP 695 named recursive aliases for JSON-like values.
type JSONPrimitive = str | int | float | bool | None
type JSONValue = JSONPrimitive | list[JSONValue] | dict[str, JSONValue]
type JSONObject = dict[str, JSONValue]
