# Outcome Receipt Kit

`receipt-check` compares explicit postconditions with normalized tool-result evidence. It reports each assertion as `verified`, `mismatch`, or `missing_evidence`; assistant completion text is never read.

## Install and run

Python 3.10 or newer is required. From the repository root:

```sh
python -m pip install -e ".[dev]"
receipt-check examples/passing/contract.json examples/passing/evidence.json
receipt-check examples/mismatch-tool-error/contract.json examples/mismatch-tool-error/evidence.json
receipt-check examples/missing-event-path/contract.json examples/missing-event-path/evidence.json --format json
```

The passing example exits `0`. The mismatch/tool-error example exits `1`. The missing-evidence example exits `2`. Use `--format json` for a deterministic machine-readable report.

## Contract and evidence

A contract names the event to inspect, a JSON Pointer into its result, and the exact JSON value expected:

```json
{
  "version": 1,
  "assertions": [
    {"id": "issue-created", "event": "create_issue", "pointer": "/id", "equals": "SYN-42"}
  ]
}
```

Normalized evidence records the event outcome and result:

```json
{
  "version": 1,
  "events": [
    {"event": "create_issue", "status": "ok", "result": {"id": "SYN-42"}}
  ]
}
```

A missing event or pointer is `missing_evidence`; an error event or unequal value is `mismatch`. Contracts and evidence reject unknown fields, duplicate assertion IDs or event names, and malformed JSON Pointers.

## Exit codes

- `0`: every asserted postcondition is verified.
- `1`: at least one observed value differs or a tool result reports an error.
- `2`: invalid input or missing evidence prevents verification.

## Scope and limits

This is an offline comparison utility for already-normalized evidence. It does not call a provider, replay a tool, adapt live provider formats, authenticate who produced evidence, or prove that a tool response corresponds to a real external state change. Examples contain synthetic data only. Runtime dependencies are from the Python standard library.
