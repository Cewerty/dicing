"""
Regression contract of the dice value objects that the notation parser is built on.

Every operator is checked against plain integer arithmetic on deterministic dice (``MaxRandom``:
a die always shows its biggest side, a pool — the sum of the biggest sides). If one of these
tests fails, the message points at the broken operator instead of a wrong total in the parser.
"""

from __future__ import annotations

import operator
from collections.abc import Callable
from typing import Any, TypeAlias

import pytest
from hypothesis import given
from hypothesis import strategies as st

from dicing import (
    Dice,
    DiceInvalidAmountError,
    DiceOperationTypeError,
    DicePool,
    InvalidDiceError,
    InvalidDiceInputError,
    NegativeThrowCountError,
    adv,
    dh,
    dis,
    dl,
    kh,
    kl,
    throws,
)
from .support import MaxRandom

sides = st.integers(-50, 50)
gaps = st.integers(1, 50)
ints = st.integers(-100, 100)


@st.composite
def fixed_dice(draw: st.DrawFn) -> Dice:
    """A die that always shows its biggest side."""
    smallest = draw(sides)
    return Dice(smallest, smallest + draw(gaps), MaxRandom())


fixed_pools = st.lists(fixed_dice(), min_size=1, max_size=5).map(DicePool)
Diceable: TypeAlias = Dice | DicePool
diceables: st.SearchStrategy[Diceable] = st.one_of(fixed_dice(), fixed_pools)


def untyped(x: object) -> Any:  # noqa: ANN401
    """Hide a deliberately wrong argument from the type checkers."""
    return x


def value(x: Diceable) -> int:
    """The value a deterministic die or pool always rolls."""
    return x.biggest_side if isinstance(x, Dice) else sum(d.biggest_side for d in x)


ADD_SUB = [pytest.param(operator.add, id="+"), pytest.param(operator.sub, id="-")]
ALL_OPS = [*ADD_SUB, pytest.param(operator.mul, id="*")]


# --- Diceable op int / int op Diceable ---------------------------------------------------------


@pytest.mark.parametrize("op", ALL_OPS)
@given(x=diceables, k=ints)
def test_diceable_op_int_is_rolled_value_op_int(op: Callable[[object, object], object], x: Diceable, k: int) -> None:
    """``d + k``, ``d - k``, ``d * k`` (and the same for a pool): roll once, then plain arithmetic."""
    assert op(x, k) == op(value(x), k)


@pytest.mark.parametrize("op", ADD_SUB)
@given(x=diceables, k=ints)
def test_int_op_diceable_is_int_op_rolled_value(op: Callable[[object, object], object], x: Diceable, k: int) -> None:
    """``k + d`` and ``k - d``: the sign follows the left operand."""
    assert op(k, x) == op(k, value(x))


@given(x=diceables, k=st.integers(0, 10))
def test_int_times_diceable_repeats_the_dice(x: Diceable, k: int) -> None:
    """``k * d`` / ``k * pool`` is notation (kdN): a pool with the dice repeated k times, not rolled."""
    pool = k * x
    assert isinstance(pool, DicePool)
    dice = [x] if isinstance(x, Dice) else list(x)
    assert [(d.smallest_side, d.biggest_side) for d in pool] == [(d.smallest_side, d.biggest_side) for d in dice] * k


# --- Diceable op Diceable ----------------------------------------------------------------------


@pytest.mark.parametrize("op", ALL_OPS)
@given(left=diceables, right=diceables)
def test_diceable_op_diceable_is_rolled_values(
    op: Callable[[object, object], object], left: Diceable, right: Diceable
) -> None:
    """Any combination of dice and pools on both sides: both are rolled, the sign follows the left operand."""
    assert op(left, right) == op(value(left), value(right))


@pytest.mark.parametrize(
    ("reflected", "op"),
    [
        pytest.param("__radd__", operator.add, id="radd"),
        pytest.param("__rsub__", operator.sub, id="rsub"),
        pytest.param("__rmul__", operator.mul, id="rmul"),
    ],
)
@given(x=diceables, other=diceables)
def test_reflected_operator_with_diceable_puts_other_on_the_left(
    reflected: str, op: Callable[[int, int], int], x: Diceable, other: Diceable
) -> None:
    """``x.__rsub__(other)`` means ``other - x``: the reflected methods keep the operand order."""
    assert getattr(x, reflected)(other) == op(value(other), value(x))


# --- unsupported operands ----------------------------------------------------------------------


@pytest.mark.parametrize("method", ["__add__", "__radd__", "__sub__", "__rsub__", "__mul__", "__rmul__"])
@pytest.mark.parametrize("x", [Dice(1, 6), DicePool([Dice(1, 6), Dice(1, 8)])], ids=["Dice", "DicePool"])
@pytest.mark.parametrize("bad", ["4", 1.5, None, [1]], ids=["str", "float", "None", "list"])
def test_unsupported_operand_raises_dice_operation_type_error(x: Diceable, method: str, bad: object) -> None:
    """Every operator rejects non-int, non-dice operands with DiceOperationTypeError (a TypeError)."""
    with pytest.raises(DiceOperationTypeError):
        getattr(x, method)(bad)


def test_pool_index_must_be_int_or_slice() -> None:
    """``pool["0"]`` is a TypeError, as for a list."""
    with pytest.raises(TypeError):
        DicePool([Dice(1, 6)])[untyped("0")]


# --- mechanics on dice: kh / kl / dh / dl, adv / dis, throws, check_success --------------------


@given(st.lists(fixed_dice(), min_size=1, max_size=8), st.data())
def test_keep_drop_on_dice_match_sorting_of_the_rolls(dice: list[Dice], data: st.DataObject) -> None:
    """``kh``/``kl``/``dh``/``dl`` roll every die once and keep/drop like sorting the results."""
    rolls = [d.biggest_side for d in dice]
    keep = data.draw(st.integers(1, len(dice)))
    drop = data.draw(st.integers(0, len(dice)))
    for source in (dice, DicePool(dice)):
        assert kh(source, keep) == sorted(rolls, reverse=True)[:keep]
        assert kl(source, keep) == sorted(rolls)[:keep]
        assert dh(source, drop) == sorted(rolls)[: len(rolls) - drop]
        assert dl(source, drop) == sorted(rolls, reverse=True)[: len(rolls) - drop]


@pytest.mark.parametrize("mechanic", [kh, kl])
def test_keep_more_dice_than_available_is_rejected(mechanic: Callable[[list[Dice], int], list[int]]) -> None:
    """Keeping more dice than there are (``2d6kh3``) is an error, not a silent short list."""
    with pytest.raises(DiceInvalidAmountError):
        mechanic([Dice(1, 6), Dice(1, 6)], 3)


@pytest.mark.parametrize("mechanic", [adv, dis])
def test_advantage_on_empty_collection_is_rejected(mechanic: Callable[[list[Dice]], int]) -> None:
    """Advantage/disadvantage of nothing is an error."""
    with pytest.raises(InvalidDiceInputError):
        mechanic([])


@pytest.mark.parametrize("mechanic", [adv, dis])
def test_advantage_rejects_non_dice_input(mechanic: Callable[[object], int]) -> None:
    """Only dice, pools and lists of them are accepted."""
    with pytest.raises(InvalidDiceInputError):
        mechanic("d20")


@given(x=diceables, count=st.integers(0, 5), k=ints)
def test_throws_rolls_count_times_with_the_modifier(x: Diceable, count: int, k: int) -> None:
    """``throws`` yields exactly ``count`` rolls, each with the modifier added once."""
    assert list(throws(x, count, k)) == [value(x) + k] * count


def test_throws_rejects_bad_input() -> None:
    """A negative count and a non-dice argument are errors."""
    with pytest.raises(NegativeThrowCountError):
        list(throws(Dice(1, 6), -1))
    with pytest.raises(InvalidDiceError):
        list(throws(untyped("d6"), 1))


@given(pool=fixed_pools, delta=st.integers(-5, 5))
def test_pool_check_success_compares_the_sum(pool: DicePool, delta: int) -> None:
    """A pool succeeds when its sum reaches the target."""
    target = value(pool) + delta
    assert pool.check_success(target) is (value(pool) >= target)
