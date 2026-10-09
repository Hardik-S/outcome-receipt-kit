"""Evaluate a versioned outcome receipt against a contract."""

from __future__ import annotations

from typing import Any

from .contract import resolve_pointer, validate_contract, validate_evidence


def check_contract(contract: dict, evidence: dict) -> list[dict]:
    """Return one stable, assertion-ordered result for each contract assertion.

    Values are compared with JSON type-sensitive equality, so booleans are not
    accidentally treated as the integers 0 and 1.
    """
    assertions = validate_contract(contract)
    events = validate_evidence(evidence)
    results: list[dict[str, Any]] = []
    for assertion in assertions:
        event = events.get(assertion["event"])
        observed: Any = None
        if event is None:
            status = "missing_evidence"
            message = f"No evidence event named {assertion['event']!r} was provided."
        elif event["status"] == "error":
            status = "mismatch"
            observed = {"status": "error"}
            if "error" in event:
                observed["error"] = event["error"]
            message = f"Evidence event {assertion['event']!r} failed: {event.get('error', 'tool error')}"
        else:
            found, observed = resolve_pointer(event["result"], assertion["tokens"])
            if not found:
                status = "missing_evidence"
                message = f"Pointer {assertion['pointer']!r} is absent from event {assertion['event']!r}."
            elif type(observed) is not type(assertion["equals"]) or observed != assertion["equals"]:
                status = "mismatch"
                message = f"Observed value at {assertion['pointer']!r} did not equal the expected value."
            else:
                status = "verified"
                message = "Observed value matched the expected value."
        results.append({
            "id": assertion["id"],
            "event": assertion["event"],
            "pointer": assertion["pointer"],
            "status": status,
            "expected": assertion["equals"],
            "observed": observed,
            "message": message,
        })
    return results
