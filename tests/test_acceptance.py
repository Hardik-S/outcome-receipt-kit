"""Acceptance coverage for offline, synthetic outcome receipt checks."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from outcome_receipt.evaluate import check_contract


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"


def load_example(name):
    folder = EXAMPLES / name
    return tuple(json.loads((folder / filename).read_text(encoding="utf-8"))
                 for filename in ("contract.json", "evidence.json"))


def test_public_examples_cover_pass_mismatch_error_and_missing_evidence():
    contract, evidence = load_example("passing")
    result = check_contract(contract, evidence)
    assert result[0]["status"] == "verified"
    assert set(result[0]) == {"id", "event", "pointer", "status", "expected", "observed", "message"}

    contract, evidence = load_example("mismatch-tool-error")
    results = check_contract(contract, evidence)
    assert [item["status"] for item in results] == ["mismatch", "mismatch"]
    assert results[1]["observed"]["status"] == "error"
    assert "synthetic provider failure" in results[1]["message"]

    contract, evidence = load_example("missing-event-path")
    results = check_contract(contract, evidence)
    assert [item["status"] for item in results] == ["missing_evidence", "missing_evidence"]


@pytest.mark.parametrize("key,pointer", [("a/b", "/a~1b"), ("m~n", "/m~0n")])
def test_rfc6901_escape_decoding(key, pointer):
    contract = {"version": 1, "assertions": [
        {"id": "escaped", "event": "read", "pointer": pointer, "equals": "found"}
    ]}
    evidence = {"version": 1, "events": [
        {"event": "read", "status": "ok", "result": {key: "found"}}
    ]}
    assert check_contract(contract, evidence)[0]["status"] == "verified"


@pytest.mark.parametrize("value", [False, 0, None])
def test_json_scalar_equality_is_exact(value):
    contract = {"version": 1, "assertions": [
        {"id": "scalar", "event": "read", "pointer": "/value", "equals": value}
    ]}
    evidence = {"version": 1, "events": [
        {"event": "read", "status": "ok", "result": {"value": value}}
    ]}
    assert check_contract(contract, evidence)[0]["status"] == "verified"


@pytest.mark.parametrize("expected,observed", [(False, 0), (0, False), (None, "null")])
def test_json_scalar_mismatches_are_exact(expected, observed):
    contract = {"version": 1, "assertions": [
        {"id": "scalar", "event": "read", "pointer": "/value", "equals": expected}
    ]}
    evidence = {"version": 1, "events": [
        {"event": "read", "status": "ok", "result": {"value": observed}}
    ]}
    assert check_contract(contract, evidence)[0]["status"] == "mismatch"


@pytest.mark.parametrize("contract,evidence", [
    ({"version": True, "assertions": []}, {"version": 1, "events": []}),
    ({"version": 2, "assertions": []}, {"version": 1, "events": []}),
    ({"version": 1, "assertions": [
        {"id": "x", "event": "e", "pointer": "/x~2", "equals": 1}
    ]}, {"version": 1, "events": []}),
    ({"version": 1, "assertions": [
        {"id": "x", "event": "e", "pointer": "/x", "equals": 1},
        {"id": "x", "event": "e", "pointer": "/y", "equals": 2},
    ]}, {"version": 1, "events": []}),
    ({"version": 1, "assertions": []}, {"version": 1, "events": [
        {"event": "e", "status": "ok", "result": {}},
        {"event": "e", "status": "ok", "result": {}},
    ]}),
    ({"version": 1, "assertions": []}, {"version": 1, "events": [
        {"event": "e", "status": "pending", "result": {}}
    ]}),
    ({"version": 1, "assertions": []}, {"version": 1, "events": [
        {"event": "e", "status": "ok"}
    ]}),
    ({"version": 1, "assertions": [], "extra": True}, {"version": 1, "events": []}),
    ({"version": 1, "assertions": [
        {"id": "x", "event": "e", "pointer": "/x", "equals": 1, "extra": True}
    ]}, {"version": 1, "events": []}),
    ({"version": 1, "assertions": []}, {"version": 1, "events": [], "extra": True}),
    ({"version": 1, "assertions": []}, {"version": 1, "events": [
        {"event": "e", "status": "ok", "result": {}, "extra": True}
    ]}),
])
def test_invalid_documents_are_rejected(contract, evidence):
    with pytest.raises(ValueError):
        check_contract(contract, evidence)


def run_cli(contract, evidence, output_format="text"):
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, "-m", "outcome_receipt", str(contract), str(evidence),
         "--format", output_format], cwd=ROOT, env=env, text=True,
        capture_output=True, check=False
    )


def test_cli_examples_exit_codes_and_deterministic_output():
    expected_codes = {"passing": 0, "mismatch-tool-error": 1, "missing-event-path": 2}
    for name, expected_code in expected_codes.items():
        contract, evidence = (EXAMPLES / name / "contract.json", EXAMPLES / name / "evidence.json")
        first = run_cli(contract, evidence)
        second = run_cli(contract, evidence)
        assert first.returncode == expected_code
        assert (first.stdout, first.stderr) == (second.stdout, second.stderr)
        assert first.stderr == ""

        first_json = run_cli(contract, evidence, "json")
        second_json = run_cli(contract, evidence, "json")
        assert first_json.returncode == expected_code
        assert first_json.stdout == second_json.stdout
        parsed = json.loads(first_json.stdout)
        assert set(parsed) == {"results", "summary"}


def test_cli_invalid_and_missing_files_exit_two(tmp_path):
    contract = tmp_path / "contract.json"
    evidence = tmp_path / "evidence.json"
    contract.write_text('{"version":1,"assertions":[]}', encoding="utf-8")
    evidence.write_text('{"version":9,"events":[]}', encoding="utf-8")
    assert run_cli(contract, evidence).returncode == 2
    evidence.unlink()
    assert run_cli(contract, evidence).returncode == 2


def test_cli_text_mismatch_shows_expected_and_observed_deterministically():
    contract, evidence = (EXAMPLES / "mismatch-tool-error" / "contract.json",
                          EXAMPLES / "mismatch-tool-error" / "evidence.json")
    first = run_cli(contract, evidence)
    second = run_cli(contract, evidence)

    assert first.returncode == 1
    assert first.stdout == second.stdout
    assert "SYN-42" in first.stdout
    assert "SYN-41" in first.stdout
