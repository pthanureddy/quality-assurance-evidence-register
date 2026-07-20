import json
import sys

import pytest

from qa_register.cli import main


def test_validate_command_prints_kpis(sample_path, monkeypatch, capsys):
    monkeypatch.setattr(
        sys,
        "argv",
        ["qa-register", "validate", "--input", str(sample_path)],
    )
    assert main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["projects_total"] == 2


def test_generate_command_writes_bundle(sample_path, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "qa-register",
            "generate",
            "--input",
            str(sample_path),
            "--output",
            str(tmp_path),
        ],
    )
    assert main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["rows"]["jira_action_handoff.csv"] == 5
    assert (tmp_path / "quality_summary.json").is_file()


def test_generate_requires_output(sample_path, monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        ["qa-register", "generate", "--input", str(sample_path)],
    )
    with pytest.raises(SystemExit, match="--output is required"):
        main()
