import pytest
from hypothesis import example, given
from hypothesis import strategies as st
from lark.exceptions import LarkError

from dicing import DiceInvalidAmountError, DiceInvalidSidesError, SeededRandomStrategy, parse_dice_notation

from .support import DROP_CODES, KEEP_CODES, Expr, MaxRandom, MinRandom, expressions

# Regressions of bugs found in the old parser, checked by every property below.
REGRESSIONS = [
    Expr("d20", 1, 0, 1, 20, 1, 20),  # used to return a raw lark Tree
    Expr("d20+5-2", 1, 3, 4, 23, 4, 23),  # used to lose the d20
    Expr("4d6kh3+1d4", 2, 0, 4, 22, 4, 22),  # used to lose the d4
    Expr("1d20-1d4", 2, 0, 0, 16, -3, 19),  # dice subtraction used to raise
    Expr("2d20kh", 1, 0, 1, 20, 1, 20),  # amount omitted used to raise TypeError
]


def with_regressions(test):  # type: ignore[no-untyped-def]
    for expr in REGRESSIONS:
        test = example(expr)(test)
    return test


@with_regressions
@given(expressions())
def test_structure_matches_notation(expr: Expr) -> None:
    parsed = parse_dice_notation(expr.text)
    assert len(parsed.groups) == expr.groups
    assert parsed.modifier == expr.modifier


@with_regressions
@given(expressions())
def test_deterministic_strategies_give_exact_totals(expr: Expr) -> None:
    assert parse_dice_notation(expr.text, MinRandom()).roll() == expr.at_min
    assert parse_dice_notation(expr.text, MaxRandom()).roll() == expr.at_max


@with_regressions
@given(expressions())
def test_random_roll_within_bounds(expr: Expr) -> None:
    assert expr.low <= parse_dice_notation(expr.text).roll() <= expr.high


@given(st.integers(1, 20), st.integers(2, 100), st.sampled_from(KEEP_CODES + DROP_CODES), st.integers(1, 5))
def test_keep_drop_more_than_available_raises(count: int, sides: int, code: str, extra: int) -> None:
    with pytest.raises(DiceInvalidAmountError):
        parse_dice_notation(f"{count}d{sides}{code}{count + extra}")


@given(st.integers(2, 100))
def test_zero_dice_raises(sides: int) -> None:
    with pytest.raises(ValueError, match="positive"):
        parse_dice_notation(f"0d{sides}")


@given(st.integers(1, 20), st.sampled_from([0, 1]))
def test_dice_with_less_than_two_sides_raises(count: int, sides: int) -> None:
    with pytest.raises(DiceInvalidSidesError):
        parse_dice_notation(f"{count}d{sides}")


@given(st.text(st.characters(exclude_characters="0123456789dkhl+- \t\n\r\f"), min_size=1))
def test_garbage_raises_lark_error(text: str) -> None:
    with pytest.raises(LarkError):
        parse_dice_notation(text)


@pytest.mark.parametrize("text", ["", "2d6+", "+3", "d", "2d", "4d6kh3kk", "1d20--1"])
def test_malformed_notation_raises_lark_error(text: str) -> None:
    with pytest.raises(LarkError):
        parse_dice_notation(text)


def test_parsed_roll_is_lazy() -> None:
    parsed = parse_dice_notation("100d100")
    assert len({parsed.roll() for _ in range(20)}) > 1


@given(expressions(), st.integers(0, 2**32))
def test_roll_detailed_breakdown_is_consistent(expr: Expr, seed: int) -> None:
    """Every die is either kept or dropped, and the detailed total equals ``roll()`` with the same seed."""
    parsed = parse_dice_notation(expr.text, SeededRandomStrategy(seed))
    result = parsed.roll_detailed()
    assert result.total == parse_dice_notation(expr.text, SeededRandomStrategy(seed)).roll()
    for group, group_result in zip(parsed.groups, result.groups, strict=True):
        assert len(group_result.rolls) == len(group.pool)
        assert sorted(group_result.kept + group_result.dropped) == sorted(group_result.rolls)
        assert group_result.sign == group.sign


@given(expressions())
def test_roll_detailed_with_max_random_shows_biggest_sides(expr: Expr) -> None:
    """With a loaded strategy every recorded roll is the biggest side of its die."""
    parsed = parse_dice_notation(expr.text, MaxRandom())
    for group, group_result in zip(parsed.groups, parsed.roll_detailed().groups, strict=True):
        assert group_result.rolls == tuple(die.biggest_side for die in group.pool)
