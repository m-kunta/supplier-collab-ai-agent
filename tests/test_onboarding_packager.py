import io
import zipfile
import yaml
import pytest
from unittest.mock import patch
from pathlib import Path

from src.onboarding_packager import generate_onboarding_pack


def _read_zip(buf: io.BytesIO) -> dict[str, bytes]:
    """Return {name: content} for every file in the zip."""
    buf.seek(0)
    with zipfile.ZipFile(buf) as zf:
        return {name: zf.read(name) for name in zf.namelist()}


# ---------------------------------------------------------------------------
# Basic structure
# ---------------------------------------------------------------------------

def test_returns_bytesio(tmp_path, monkeypatch):
    monkeypatch.chdir(Path(__file__).parent.parent)  # repo root
    result = generate_onboarding_pack("Northstar Foods Co", "VEN001")
    assert isinstance(result, io.BytesIO)


def test_zip_contains_instructions(tmp_path, monkeypatch):
    monkeypatch.chdir(Path(__file__).parent.parent)
    files = _read_zip(generate_onboarding_pack("Northstar Foods Co", "VEN001"))
    assert "instructions.md" in files
    content = files["instructions.md"].decode()
    assert "Northstar Foods Co" in content
    assert "VEN001" in content


def test_zip_contains_csv_templates(tmp_path, monkeypatch):
    monkeypatch.chdir(Path(__file__).parent.parent)
    files = _read_zip(generate_onboarding_pack("Northstar Foods Co", "VEN001"))
    template_files = [k for k in files if k.startswith("templates/")]
    assert len(template_files) > 0


def test_csv_templates_have_header_row(tmp_path, monkeypatch):
    monkeypatch.chdir(Path(__file__).parent.parent)
    files = _read_zip(generate_onboarding_pack("Northstar Foods Co", "VEN001"))
    for name, content in files.items():
        if name.startswith("templates/") and name.endswith(".csv"):
            text = content.decode()
            lines = [l for l in text.splitlines() if l.strip()]
            assert len(lines) == 1, f"{name} should have exactly 1 header row"
            assert "," in text or len(text.strip()) > 0


def test_zip_is_seeked_to_zero(tmp_path, monkeypatch):
    monkeypatch.chdir(Path(__file__).parent.parent)
    buf = generate_onboarding_pack("Northstar Foods Co", "VEN001")
    assert buf.tell() == 0


# ---------------------------------------------------------------------------
# Graceful handling of missing schemas dir
# ---------------------------------------------------------------------------

def test_handles_missing_schemas_dir(tmp_path, monkeypatch):
    """Should still produce a valid zip with instructions when schemas/ doesn't exist."""
    monkeypatch.chdir(tmp_path)  # tmp_path has no data/schemas/
    result = generate_onboarding_pack("ACME Corp", "VEN999")
    files = _read_zip(result)
    assert "instructions.md" in files
    # No templates expected since schemas dir is absent
    assert not any(k.startswith("templates/") for k in files)
