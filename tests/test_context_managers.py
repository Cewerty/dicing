"""Property-based tests for DiceContext / DicePoolContext: temporary strategy replacement on a copy."""

from __future__ import annotations

from types import TracebackType

import pytest
from hypothesis import given
from hypothesis import strategies as st

from dicing._compat import override
from dicing import AdvantageRoll, Dice, DiceContext, DicePool, DicePoolContext, SeededRandomStrategy
from dicing.utils.context_managers import BaseDiceContextManager

from .support import MaxRandom, MaxRoll, MinRandom

sides = st.integers(-100, 100)
gaps = st.integers(1, 100)
seeds = st.integers(0, 2**32)


@st.composite
def dice(draw: st.DrawFn) -> Dice:
    """Any valid die (negative sides included) with the default strategies."""
    smallest = draw(sides)
    return Dice(smallest, smallest + draw(gaps))


@st.composite
def seeded_dice(draw: st.DrawFn) -> tuple[Dice, int]:
    """A die with a SeededRandomStrategy and the seed used for it."""
    smallest, seed = draw(sides), draw(seeds)
    return Dice(smallest, smallest + draw(gaps), SeededRandomStrategy(seed)), seed


pools = st.lists(dice(), min_size=1, max_size=6).map(DicePool)


class Boom(Exception):
    """Exception raised inside a `with` block."""


# --- DiceContext -------------------------------------------------------------------------------


@given(dice())
def test_proxy_keeps_the_sides(die: Dice) -> None:
    """The proxy is a die with the same sides as the original one."""
    with DiceContext(die, replaced_rng_strategy=MaxRandom()) as proxy:
        assert (proxy.smallest_side, proxy.biggest_side) == (die.smallest_side, die.biggest_side)
        assert proxy is not die


@given(dice())
def test_replaced_rng_strategy_is_used_inside_the_block(die: Dice) -> None:
    """Inside `with` the proxy rolls with the replaced random strategy."""
    with DiceContext(die, replaced_rng_strategy=MaxRandom()) as proxy:
        assert proxy.roll() == die.biggest_side
    with DiceContext(die, replaced_rng_strategy=MinRandom()) as proxy:
        assert proxy.roll() == die.smallest_side


@given(dice())
def test_original_die_is_not_changed(die: Dice) -> None:
    """The context works on a copy: the strategies of the original die stay the same objects."""
    rng, roll = die.randomization_strategy, die.roll_strategy
    with DiceContext(die, replaced_rng_strategy=MaxRandom(), replaced_roll_strategy=MaxRoll()):
        pass
    assert die.randomization_strategy is rng
    assert die.roll_strategy is roll
    assert die.smallest_side <= die.roll() <= die.biggest_side


@given(seeded_dice())
def test_not_replaced_rng_strategy_is_inherited(seeded: tuple[Dice, int]) -> None:
    """Replacing only the roll strategy keeps the seed: rolls inside `with` stay reproducible."""
    die, seed = seeded
    reference = Dice(die.smallest_side, die.biggest_side, SeededRandomStrategy(seed), AdvantageRoll())
    with DiceContext(die, replaced_roll_strategy=AdvantageRoll()) as proxy:
        assert [proxy.roll() for _ in range(5)] == [reference.roll() for _ in range(5)]


@given(dice())
def test_not_replaced_roll_strategy_is_inherited(die: Dice) -> None:
    """Replacing only the random strategy keeps the roll strategy of the original die."""
    die = Dice(die.smallest_side, die.biggest_side, _roll_strategy=MaxRoll())
    with DiceContext(die, replaced_rng_strategy=MinRandom()) as proxy:
        assert proxy.roll_strategy is die.roll_strategy


def test_exception_is_propagated_and_proxy_is_released() -> None:
    """`__exit__` never swallows exceptions and drops the proxy."""
    context = DiceContext(Dice(1, 20))
    with pytest.raises(Boom), context:
        raise Boom
    assert context.proxy_dice is None


# --- DicePoolContext ---------------------------------------------------------------------------


@given(pools)
def test_pool_proxy_keeps_size_and_sides(pool: DicePool) -> None:
    """Every die of the proxy pool has the sides of the matching original die."""
    with DicePoolContext(pool, replaced_rng_strategy=MaxRandom()) as proxy:
        assert [(d.smallest_side, d.biggest_side) for d in proxy] == [(d.smallest_side, d.biggest_side) for d in pool]


@given(pools)
def test_pool_replaced_rng_strategy_applies_to_every_die(pool: DicePool) -> None:
    """With a replaced random strategy every die shows its biggest side; `roll()` is their sum."""
    with DicePoolContext(pool, replaced_rng_strategy=MaxRandom()) as proxy:
        assert proxy.roll_each() == [d.biggest_side for d in pool]
        assert proxy.roll() == sum(d.biggest_side for d in pool)


@given(st.lists(seeded_dice(), min_size=1, max_size=6))
def test_pool_dice_inherit_their_own_strategies(seeded: list[tuple[Dice, int]]) -> None:
    """Without a replacement each die keeps its own strategies, and the original pool is not changed."""
    pool = DicePool([die for die, _ in seeded])
    strategies = [(d.randomization_strategy, d.roll_strategy) for d in pool]
    with DicePoolContext(pool) as proxy:
        assert [(d.randomization_strategy, d.roll_strategy) for d in proxy] == strategies
    assert [(d.randomization_strategy, d.roll_strategy) for d in pool] == strategies


def test_pool_exception_is_propagated_and_proxy_is_released() -> None:
    """`__exit__` never swallows exceptions and drops the proxy pool."""
    context = DicePoolContext(DicePool([Dice(1, 6), Dice(1, 8)]))
    with pytest.raises(Boom), context:
        raise Boom
    assert context.proxy_pool is None


# --- Extension point ---------------------------------------------------------------------------


class RecordingContext(BaseDiceContextManager):
    """Subclass that records the calls of the hooks."""

    def __init__(self, die: Dice) -> None:
        super().__init__(die)
        self.calls: list[tuple[str, type[BaseException] | None]] = []

    @override
    def on_enter(self) -> None:
        self.calls.append(("enter", None))

    @override
    def on_exit(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.calls.append(("exit", exc_type))


def test_hooks_are_called_in_order_with_the_exception_type() -> None:
    """`on_enter` runs after the proxy is created, `on_exit` gets the exception of the block."""
    context = RecordingContext(Dice(1, 20))
    with context as proxy:
        assert context.proxy_dice is proxy
    with pytest.raises(Boom), context:
        raise Boom
    assert context.calls == [("enter", None), ("exit", None), ("enter", None), ("exit", Boom)]
