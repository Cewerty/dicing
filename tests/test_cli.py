import json
import subprocess
import sys

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from dicing import SeededRandomStrategy, parse_dice_notation
from dicing.cli import EXIT_INVALID_NOTATION, EXIT_OK, main

from .support import Expr, expressions

seeds = st.integers(0, 2**32)
# capsys is function-scoped; it is reset manually inside each example
capsys_settings = settings(suppress_health_check=[HealthCheck.function_scoped_fixture])


def run(capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[int, str, str]:
    capsys.readouterr()
    code = main(list(argv))
    out, err = capsys.readouterr()
    return code, out, err


@capsys_settings
@given(expressions(), seeds)
def test_total_matches_library(capsys: pytest.CaptureFixture[str], expr: Expr, seed: int) -> None:
    """``--total`` prints exactly what the library rolls with the same seed."""
    code, out, _ = run(capsys, expr.text, "--seed", str(seed), "--total")
    assert code == EXIT_OK
    assert int(out) == parse_dice_notation(expr.text, SeededRandomStrategy(seed)).roll()


@capsys_settings
@given(expressions(), seeds)
def test_json_is_consistent(capsys: pytest.CaptureFixture[str], expr: Expr, seed: int) -> None:
    """``--json`` totals add up and every die is either kept or dropped."""
    code, out, _ = run(capsys, expr.text, "--seed", str(seed), "--json")
    assert code == EXIT_OK
    payload = json.loads(out)
    assert payload["notation"] == expr.text
    assert len(payload["groups"]) == expr.groups
    assert payload["total"] == sum(group["subtotal"] for group in payload["groups"]) + payload["modifier"]
    for group in payload["groups"]:
        assert sorted(group["kept"] + group["dropped"]) == sorted(group["rolls"])


@capsys_settings
@given(expressions(), seeds)
def test_same_seed_same_output(capsys: pytest.CaptureFixture[str], expr: Expr, seed: int) -> None:
    """Human-readable output is reproducible with a seed and ends with the total."""
    first = run(capsys, expr.text, "--seed", str(seed))
    second = run(capsys, expr.text, "--seed", str(seed))
    assert first == second
    assert first[1].rstrip().splitlines()[-1].startswith("total: ")


@capsys_settings
@given(st.integers(1, 10))
def test_times_rolls_n_times(capsys: pytest.CaptureFixture[str], times: int) -> None:
    """``--times N`` gives N results in every output mode."""
    assert len(run(capsys, "2d6+1", "--times", str(times), "--total")[1].split()) == times
    payload = json.loads(run(capsys, "2d6+1", "--times", str(times), "--json")[1])
    assert len(payload) == times if times > 1 else isinstance(payload, dict)


@pytest.mark.parametrize("notation", ["abc", "4d6kh5", "0d6", "1d1", "2d6+"])
def test_invalid_notation_exits_with_2(capsys: pytest.CaptureFixture[str], notation: str) -> None:
    code, out, err = run(capsys, notation)
    assert code == EXIT_INVALID_NOTATION
    assert out == ""
    assert err.startswith("dicing: error: invalid notation")


@pytest.mark.parametrize("argv", [["1d6", "--total", "--json"], ["1d6", "--times", "0"], []])
def test_invalid_arguments_exit_with_2(argv: list[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(argv)
    assert exit_info.value.code == 2  # noqa: PLR2004


def test_python_dash_m_entry_point() -> None:
    """``python -m dicing`` runs the same CLI."""
    completed = subprocess.run(  # noqa: S603
        [sys.executable, "-m", "dicing", "4d6kh3+2", "--seed", "42", "--total"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == EXIT_OK
    assert completed.stdout.strip() == str(parse_dice_notation("4d6kh3+2", SeededRandomStrategy(42)).roll())
