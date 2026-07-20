import json
from pathlib import Path

import pytest

from qa_register.loader import load_register


@pytest.fixture
def sample_path() -> Path:
    return Path(__file__).parents[1] / "data" / "sample_quality_records.json"


@pytest.fixture
def sample_payload(sample_path: Path) -> dict:
    return json.loads(sample_path.read_text(encoding="utf-8"))


@pytest.fixture
def register(sample_path: Path):
    return load_register(sample_path)


@pytest.fixture
def write_payload(tmp_path: Path):
    def _write(payload: dict) -> Path:
        destination = tmp_path / "register.json"
        destination.write_text(json.dumps(payload), encoding="utf-8")
        return destination

    return _write
