# Release review — Outcome Receipt Kit v0.1

**Verdict: BLOCK** for commit `61bbc74174be5a7eeefb42aa91344d94321765cf`.

## Blocking finding

The version validator accepts JSON decimal values such as `1.0` as the supported integer version `1`. In `src/outcome_receipt/contract.py:16-18`, `_version` rejects booleans and compares `value != 1`, but does not enforce an integer type. Both contract and evidence pass through this function (`contract.py:56,87`).

Reproduction from a temporary copy with the installed CLI:

```powershell
receipt-check float-contract.json float-evidence.json --format json
```

Inputs used: a contract with `"version": 1.0` and one assertion expecting `/v` to equal `1`, plus evidence with `"version": 1.0` and result `{ "v": 1 }`. The CLI returned a `verified` finding and exit code `0`. This contradicts the validator's stated “supported integer 1” rule and allows malformed versioned documents to be treated as valid. Reject non-integer version values explicitly and add coverage for decimal versions in both documents.

## Checks that passed

- Exact checkout: `HEAD` was `61bbc74174be5a7eeefb42aa91344d94321765cf`; the requested commit changes only `.github/workflows/tests.yml`.
- `python -m pytest` on Windows / Python 3.13.1: **23 passed**.
- README clean-install examples were installed from a temporary repository copy into a temporary virtual environment. Installed CLI outcomes matched the documented exits: passing example `0`, mismatch/tool-error example `1`, missing-event/path example `2`. Repository status remained clean during these checks.
- GitHub Actions run [37944572119](https://github.com/Hardik-S/outcome-receipt-kit/actions/runs/37944572119) for this exact SHA completed successfully. All four jobs passed: Ubuntu and Windows with Python 3.10 and 3.13. The workflow grants `contents: read` and uses no secrets or provider calls (`.github/workflows/tests.yml:8-25`).
- Status handling and exit codes match the README: tool error is `mismatch`; absent event/path is `missing_evidence`; missing evidence takes exit `2`, otherwise mismatch exits `1`, and all verified exits `0` (`src/outcome_receipt/evaluate.py:22-41`, `src/outcome_receipt/cli.py:79-81`).
- JSON Pointer decoding handles `~0` and `~1`, list indices are restricted to ASCII decimal indices without leading zeroes, and absent paths are distinguished from present `null` (`src/outcome_receipt/contract.py:28-49,115-132`).
- Text and JSON output are repeatable for the fixtures; assertion order and summary status order are fixed (`src/outcome_receipt/evaluate.py:11-18`, `src/outcome_receipt/cli.py:28-51,73-77`; `tests/test_acceptance.py:118-134`).
- Runtime code reads input documents and emits output without provider/network calls or writes. The README clearly limits claims to already-normalized evidence and says it does not authenticate the source or prove an external state change (`README.md:3,50-52`). Public examples are synthetic (`README.md:52`; `examples/`).

## Non-blocking coverage notes

The 23 tests cover pass, mismatch, tool error, missing event/path, malformed `~` escapes, unknown keys, duplicate identifiers/events, strict scalar equality, CLI exits, and repeatable output (`tests/test_acceptance.py:24-155`). Add focused cases for JSON array-pointer indices and for absent versus explicit `null` if those edge semantics are part of the intended public contract. These are coverage gaps; code inspection did not reveal a defect in those paths.

## Follow-up review — commit `b739d6ee659e30584b957362f908f9e945e7f28f`

**Revised verdict: PASS.** The initial BLOCK above remains as the historical review of `61bbc74174be5a7eeefb42aa91344d94321765cf`; this follow-up resolves its decimal-version finding.

- `src/outcome_receipt/contract.py:16-18` now requires `type(value) is int` and `value == 1`. The shared validator is called for both contract and evidence versions (`contract.py:56,87`), so JSON `1.0` is rejected in either position; booleans remain rejected as well.
- Regression cases cover decimal contract and evidence versions independently (`tests/test_acceptance.py:91-94`). The existing `test_invalid_documents_are_rejected` parametrized test asserts each raises `ValueError` (`tests/test_acceptance.py:122-124`).
- Pointer boundary coverage now verifies `/items/1`, distinguishes a present `null` from an absent pointer, and expects statuses `verified`, `verified`, `missing_evidence` in order (`tests/test_acceptance.py:52-66`).
- `python -m pytest` on Windows / Python 3.13.1: **26 passed**.
- GitHub Actions run [37945447065](https://github.com/Hardik-S/outcome-receipt-kit/actions/runs/37945447065) for this exact SHA completed successfully. All four jobs passed: Ubuntu and Windows with Python 3.10 and 3.13, including editable install and `python -m pytest`.
- GitHub annotated the run with non-blocking maintenance notices: the `ubuntu-latest` image is scheduled to migrate to Ubuntu 26 on 2026-10-19, and `actions/checkout@v4` / `actions/setup-python@v5` were forced to Node.js 24 because Node.js 20 is deprecated. These did not fail any matrix job.

The previous review's passing findings on status semantics, JSON Pointer decoding, output/exit-code determinism, synthetic fixtures, offline/read-only runtime behavior, README limits, and clean-install quickstart remain applicable: this follow-up changes only version validation and its tests, leaving those reviewed surfaces untouched.
