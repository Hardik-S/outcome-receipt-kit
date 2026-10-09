# Outcome Receipt Kit 0.1.0

Outcome Receipt Kit checks whether normalized tool-result evidence satisfies explicit postconditions. Assistant completion text does not affect the result.

## Quickstart

```sh
python -m pip install -e ".[dev]"
receipt-check examples/passing/contract.json examples/passing/evidence.json
receipt-check examples/mismatch-tool-error/contract.json examples/mismatch-tool-error/evidence.json
receipt-check examples/missing-event-path/contract.json examples/missing-event-path/evidence.json --format json
```

The three synthetic examples exit `0` (verified), `1` (mismatch or tool error), and `2` (missing evidence), respectively. Mismatch output includes expected and observed values.

## Evidence and limits

The checker compares JSON Pointer assertions against an offline, normalized evidence file. It performs no provider calls, replay, or writes. It does not authenticate who produced a tool result or prove that a response corresponds to an external state change. Public examples contain synthetic data only.

Release checks: 26 tests pass; clean Python 3.13 installation and installed CLI examples pass; GitHub Actions passes on Ubuntu and Windows with Python 3.10 and 3.13; independent review passes on commit `b739d6ee659e30584b957362f908f9e945e7f28f`.
