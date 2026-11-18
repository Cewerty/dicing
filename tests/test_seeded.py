from hypothesis import given
from hypothesis import strategies as st

from dicing import Dice, SeededRandomStrategy, parse_dice_notation

from .support import Expr, expressions

seeds = st.integers(0, 2**32)


@given(seeds, expressions())
def test_same_seed_reproduces_whole_expression(seed: int, expr: Expr) -> None:
    """One SeededRandomStrategy shared by all dice of an expression makes it reproducible."""
    first = parse_dice_notation(expr.text, SeededRandomStrategy(seed))
    second = parse_dice_notation(expr.text, SeededRandomStrategy(seed))
    assert [first.roll() for _ in range(3)] == [second.roll() for _ in range(3)]


@given(seeds, st.integers(-1000, 1000), st.integers(1, 1000), st.integers(1, 20))
def test_same_seed_reproduces_sequence_of_rolls(seed: int, smallest: int, gap: int, n: int) -> None:
    """Two dice with equal seeds produce the same sequence, and every roll stays within the sides."""
    first = Dice(smallest, smallest + gap, SeededRandomStrategy(seed))
    second = Dice(smallest, smallest + gap, SeededRandomStrategy(seed))
    rolls = [first.roll() for _ in range(n)]
    assert rolls == [second.roll() for _ in range(n)]
    assert all(smallest <= roll <= smallest + gap for roll in rolls)
