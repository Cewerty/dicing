"""Property-based tests for DiceContext / DicePoolContext: temporary strategy replacement on a copy."""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from dicing import AdvantageRoll, Dice, DiceContext, DicePool, DicePoolContext, SeededRandomStrategy

from .support import MaxRoll, MinRandom

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


@given(st.lists(seeded_dice(), min_size=1, max_size=6))
def test_pool_dice_inherit_their_own_strategies(seeded: list[tuple[Dice, int]]) -> None:
    """Without a replacement each die keeps its own strategies, and the original pool is not changed."""
    pool = DicePool([die for die, _ in seeded])
    strategies = [(d.randomization_strategy, d.roll_strategy) for d in pool]
    with DicePoolContext(pool) as proxy:
        assert [(d.randomization_strategy, d.roll_strategy) for d in proxy] == strategies
    assert [(d.randomization_strategy, d.roll_strategy) for d in pool] == strategies
