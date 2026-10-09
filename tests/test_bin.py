"""Smoke tests for the command-line scripts in bin/."""

import subprocess
import sys
from pathlib import Path

import pytest

BIN_DIR = Path(__file__).resolve().parent.parent / "bin"


@pytest.mark.parametrize("script", ["mbsolve", "obsolve"])
def test_help_exits_zero(script):
    result = subprocess.run(
        [sys.executable, str(BIN_DIR / script), "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "usage" in result.stdout.lower()
