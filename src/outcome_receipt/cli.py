"""Command line interface for offline outcome receipt checks."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from outcome_receipt.evaluate import check_contract


STATUSES = ("verified", "mismatch", "missing_evidence")


def _read_document(path: str) -> dict[str, Any]:
    try:
        with Path(path).open("r", encoding="utf-8") as source:
            document = json.load(source)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{path}: {exc}") from None
    if not isinstance(document, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return document


def _summary(results: list[dict[str, Any]]) -> dict[str, int]:
    return {status: sum(result.get("status") == status for result in results) for status in STATUSES}


def _render_text(results: list[dict[str, Any]], summary: dict[str, int]) -> str:
    lines = []
    for result in results:
        line = (
            f"{result['status']} {result['id']} ({result['event']} {result['pointer']}): "
            f"{result['message']}"
        )
        if result["status"] == "mismatch":
            for key in ("expected", "observed"):
                if key in result:
                    value = json.dumps(
                        result[key], ensure_ascii=False, sort_keys=True, separators=(",", ":")
                    )
                    line += f" {key}={value}"
        lines.append(line)
    lines.append(
        "Summary: "
        + ", ".join(f"{status}={summary[status]}" for status in STATUSES)
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="receipt-check")
    parser.add_argument("contract", help="path to the contract JSON document")
    parser.add_argument("evidence", help="path to the evidence JSON document")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)

    try:
        contract = _read_document(args.contract)
        evidence = _read_document(args.evidence)
        results = check_contract(contract, evidence)
        if not isinstance(results, list) or any(not isinstance(item, dict) for item in results):
            raise ValueError("checker returned an invalid findings value")
        if any(result.get("status") not in STATUSES for result in results):
            raise ValueError("checker returned an unknown finding status")
    except (OSError, ValueError) as exc:
        print(f"receipt-check: {exc}", file=sys.stderr)
        return 2

    summary = _summary(results)
    if args.format == "json":
        print(json.dumps({"results": results, "summary": summary}, ensure_ascii=False, indent=2))
    else:
        print(_render_text(results, summary))

    if summary["missing_evidence"]:
        return 2
    return 1 if summary["mismatch"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
