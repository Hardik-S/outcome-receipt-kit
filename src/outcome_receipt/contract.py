"""Validation helpers for versioned outcome receipt contracts."""

from __future__ import annotations

from typing import Any


def _object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    if any(not isinstance(key, str) for key in value):
        raise ValueError(f"{label} keys must be strings")
    return value


def _version(value: Any, label: str) -> None:
    if isinstance(value, bool) or value != 1:
        raise ValueError(f"{label}.version must be the supported integer 1")


def _keys(value: dict[str, Any], allowed: set[str], label: str) -> None:
    unknown = set(value) - allowed
    if unknown:
        names = ", ".join(sorted(unknown))
        raise ValueError(f"{label} contains unknown key(s): {names}")


def _pointer_tokens(pointer: Any, label: str) -> list[str]:
    if not isinstance(pointer, str):
        raise ValueError(f"{label}.pointer must be a JSON Pointer string")
    if pointer == "":
        return []
    if not pointer.startswith("/"):
        raise ValueError(f"{label}.pointer must be empty or start with '/'")
    tokens: list[str] = []
    for raw in pointer[1:].split("/"):
        decoded: list[str] = []
        i = 0
        while i < len(raw):
            if raw[i] != "~":
                decoded.append(raw[i])
                i += 1
            elif i + 1 < len(raw) and raw[i + 1] in "01":
                decoded.append("~" if raw[i + 1] == "0" else "/")
                i += 2
            else:
                raise ValueError(f"{label}.pointer contains malformed '~' escape")
        tokens.append("".join(decoded))
    return tokens


def validate_contract(contract: Any) -> list[dict[str, Any]]:
    """Validate a contract and return its normalized assertion objects."""
    doc = _object(contract, "contract")
    _keys(doc, {"version", "assertions"}, "contract")
    _version(doc.get("version"), "contract")
    assertions = doc.get("assertions")
    if not isinstance(assertions, list):
        raise ValueError("contract.assertions must be an array")
    result: list[dict[str, Any]] = []
    ids: set[str] = set()
    for index, raw in enumerate(assertions):
        label = f"contract.assertions[{index}]"
        assertion = _object(raw, label)
        _keys(assertion, {"id", "event", "pointer", "equals"}, label)
        for field in ("id", "event", "pointer", "equals"):
            if field not in assertion:
                raise ValueError(f"{label}.{field} is required")
        if not isinstance(assertion["id"], str) or not assertion["id"]:
            raise ValueError(f"{label}.id must be a non-empty string")
        if assertion["id"] in ids:
            raise ValueError(f"duplicate assertion id: {assertion['id']}")
        ids.add(assertion["id"])
        if not isinstance(assertion["event"], str) or not assertion["event"]:
            raise ValueError(f"{label}.event must be a non-empty string")
        tokens = _pointer_tokens(assertion["pointer"], label)
        result.append({"id": assertion["id"], "event": assertion["event"],
                       "pointer": assertion["pointer"], "tokens": tokens,
                       "equals": assertion["equals"]})
    return result


def validate_evidence(evidence: Any) -> dict[str, dict[str, Any]]:
    """Validate evidence and index events by their unique event name."""
    doc = _object(evidence, "evidence")
    _keys(doc, {"version", "events"}, "evidence")
    _version(doc.get("version"), "evidence")
    events = doc.get("events")
    if not isinstance(events, list):
        raise ValueError("evidence.events must be an array")
    indexed: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(events):
        label = f"evidence.events[{index}]"
        event = _object(raw, label)
        name = event.get("event")
        if not isinstance(name, str) or not name:
            raise ValueError(f"{label}.event must be a non-empty string")
        if name in indexed:
            raise ValueError(f"duplicate evidence event name: {name}")
        status = event.get("status")
        if status not in ("ok", "error") or not isinstance(status, str):
            raise ValueError(f"{label}.status must be 'ok' or 'error'")
        if status == "ok":
            _keys(event, {"event", "status", "result"}, label)
            if "result" not in event:
                raise ValueError(f"{label}.result is required when status is 'ok'")
        else:
            _keys(event, {"event", "status", "error"}, label)
            if "error" in event and not isinstance(event["error"], str):
                raise ValueError(f"{label}.error must be a string")
        indexed[name] = event
    return indexed


def resolve_pointer(document: Any, tokens: list[str]) -> tuple[bool, Any]:
    """Resolve validated pointer tokens, distinguishing absent values from null."""
    current = document
    for token in tokens:
        if isinstance(current, dict):
            if token not in current:
                return False, None
            current = current[token]
        elif isinstance(current, list):
            if not token.isascii() or not token.isdigit() or (len(token) > 1 and token[0] == "0"):
                return False, None
            index = int(token)
            if index >= len(current):
                return False, None
            current = current[index]
        else:
            return False, None
    return True, current
