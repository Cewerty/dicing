import pytest
from hypothesis import given
from hypothesis import strategies as st

from dicing import DiceInvalidAmountError
from dicing.dice import drop_highest_rolls, drop_lowest_rolls, keep_highest_rolls, keep_lowest_rolls

rolls_lists = st.lists(st.integers(-1000, 1000), min_size=1, max_size=50)


@st.composite
def rolls_and_keep(draw: st.DrawFn) -> tuple[list[int], int]:
    rolls = draw(rolls_lists)
    return rolls, draw(st.integers(1, len(rolls)))


@st.composite
def rolls_and_drop(draw: st.DrawFn) -> tuple[list[int], int]:
    rolls = draw(rolls_lists)
    return rolls, draw(st.integers(0, len(rolls)))


@given(rolls_and_keep())
def test_keep_matches_sorting(case: tuple[list[int], int]) -> None:
    rolls, keep = case
    assert keep_highest_rolls(rolls, keep) == sorted(rolls, reverse=True)[:keep]
    assert keep_lowest_rolls(rolls, keep) == sorted(rolls)[:keep]


@given(rolls_and_drop())
def test_drop_matches_sorting(case: tuple[list[int], int]) -> None:
    rolls, drop = case
    assert drop_highest_rolls(rolls, drop) == sorted(rolls)[: len(rolls) - drop]
    assert drop_lowest_rolls(rolls, drop) == sorted(rolls, reverse=True)[: len(rolls) - drop]


@given(rolls_and_keep())
def test_keep_and_drop_split_the_rolls(case: tuple[list[int], int]) -> None:
    rolls, n = case
    assert sum(keep_highest_rolls(rolls, n)) + sum(drop_highest_rolls(rolls, n)) == sum(rolls)
    assert sum(keep_lowest_rolls(rolls, n)) + sum(drop_lowest_rolls(rolls, n)) == sum(rolls)


@given(rolls_lists, st.one_of(st.integers(max_value=0), st.integers(min_value=51)))
def test_invalid_keep_raises(rolls: list[int], keep: int) -> None:
    with pytest.raises(DiceInvalidAmountError):
        keep_highest_rolls(rolls, keep)
    with pytest.raises(DiceInvalidAmountError):
        keep_lowest_rolls(rolls, keep)


@given(rolls_lists, st.one_of(st.integers(max_value=-1), st.integers(min_value=51)))
def test_invalid_drop_raises(rolls: list[int], drop: int) -> None:
    with pytest.raises(DiceInvalidAmountError):
        drop_highest_rolls(rolls, drop)
    with pytest.raises(DiceInvalidAmountError):
        drop_lowest_rolls(rolls, drop)
