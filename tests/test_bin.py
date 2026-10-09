"""Smoke tests for the command-line scripts in bin/."""

import shutil
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


JSON_DIR = Path(__file__).resolve().parent / "json"


@pytest.mark.parametrize(
    "script, problem",
    [("mbsolve", "mb_solve_01.json"), ("obsolve", "ob_solve_02.json")],
)
def test_script_solves_a_problem(script, problem, tmp_path):
    """The scripts must run a whole (tiny) problem, not just print --help."""
    shutil.copy(JSON_DIR / problem, tmp_path / problem)
    result = subprocess.run(
        [sys.executable, str(BIN_DIR / script), "-f", problem, "-r"],
        capture_output=True,
        text=True,
        cwd=tmp_path,
    )
    assert result.returncode == 0, result.stderr
    assert list(tmp_path.glob("*.qu")), "expected a saved .qu result file"
