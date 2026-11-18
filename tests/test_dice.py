from dicing import Dice, DiceInvalidSidesError, DiceOperationTypeError, DicePool
from dicing.strategies import DefaultRoll, DisadvantageRoll, AdvantageRoll, MultipleRoll, RollStrategy
import pytest
from hypothesis import given
from hypothesis import strategies as st

from .support import MaxRandom, MaxRoll, MinRandom
from dicing.strategies import DefaultRandomStrategy, PseudoRandomStrategy, RandomStrategy


@pytest.fixture()
def create_dice() -> Dice:
    """Fixture to create a standard 20-sided die for testing."""
    return Dice(1, 20)


def test_check_random(create_dice: Dice) -> None:
    """Test that dice roll returns a value within the valid range."""
    dice_object = create_dice
    assert 1 <= dice_object.roll() <= 20


def test_dice_check_success(create_dice: Dice) -> None:
    """Test that check_success method works correctly with threshold 0."""
    assert create_dice.check_success(check=0)


sides = st.integers(-1000, 1000)


@given(sides, st.integers(1, 1000))
def test_dice_with_smallest_below_biggest_is_valid(smallest_side: int, gap: int) -> None:
    """Any smallest < biggest is valid, including negative sides (e.g. Fate dice dF = -1..1)."""
    dice = Dice(smallest_side, smallest_side + gap)
    assert smallest_side <= dice.roll() <= smallest_side + gap


@given(sides, st.integers(0, 1000))
def test_dice_with_smallest_not_below_biggest_raises(smallest_side: int, gap: int) -> None:
    """Dice constructor raises DiceInvalidSidesError when smallest side is not less than biggest side."""
    with pytest.raises(DiceInvalidSidesError):
        Dice(smallest_side, smallest_side - gap)


@given(st.integers(2, 100), st.integers(-10, 10))
def test_integer_on_the_right_multiplies_single_roll(biggest_side: int, k: int) -> None:
    """DSL: ``d * k`` is one roll multiplied by k."""
    assert Dice(1, biggest_side, MaxRandom()) * k == biggest_side * k
    assert Dice(1, biggest_side, MinRandom()) * k == k


@given(st.integers(0, 20))
def test_integer_on_the_left_is_number_of_dice(k: int) -> None:
    """DSL: ``k * d`` is a pool of k dice (notation kdN); ``k * pool`` repeats the pool."""
    pool = k * Dice(1, 6)
    assert isinstance(pool, DicePool)
    assert len(pool) == k
    assert len(k * DicePool([Dice(1, 6), Dice(1, 8)])) == 2 * k


@given(st.integers(2, 100), st.integers(1, 10), st.integers(-10, 10))
def test_pool_on_the_left_of_integer_multiplies_sum(biggest_side: int, n: int, k: int) -> None:
    """DSL: ``pool * k`` is the pool sum multiplied by k."""
    assert DicePool([Dice(1, biggest_side, MaxRandom()) for _ in range(n)]) * k == biggest_side * n * k


@given(st.integers(2, 100), st.integers(1, 10))
def test_pool_inserted_roll_strategy_applies_to_every_die(biggest_side: int, n: int) -> None:
    """DicePool.roll / roll_each apply the inserted roll strategy to every die."""
    pool = DicePool([Dice(1, biggest_side) for _ in range(n)])
    assert pool.roll_each(inserted_roll_strategy=MaxRoll()) == [biggest_side] * n
    assert pool.roll(inserted_roll_strategy=MaxRoll()) == biggest_side * n


@given(st.integers(2, 100), st.integers(1, 10), st.integers(-50, 50))
def test_pool_modifier_is_added_to_the_sum_once(biggest_side: int, n: int, k: int) -> None:
    """``2d6+3``: the modifier is added to the pool sum once, not to every die."""
    pool = DicePool([Dice(1, biggest_side, MaxRandom()) for _ in range(n)])
    total = biggest_side * n
    assert pool.roll(modifier=k) == total + k
    assert pool + k == total + k
    assert k + pool == total + k
    assert pool - k == total - k
    assert k - pool == k - total
    assert len(pool.roll_each()) == n


@given(st.integers(2, 100), st.integers(1, 10), st.integers(2, 100))
def test_pool_minus_diceable_keeps_the_sign(biggest_side: int, n: int, other_side: int) -> None:
    """``pool - d`` is the pool sum minus the other roll (not the other way round)."""
    pool = DicePool([Dice(1, biggest_side, MaxRandom()) for _ in range(n)])
    assert pool - Dice(1, other_side, MinRandom()) == biggest_side * n - 1
    assert pool - DicePool([Dice(1, other_side, MinRandom())] * n) == (biggest_side - 1) * n


@given(st.integers(2, 100), st.integers(2, 100), st.integers(1, 10))
def test_dice_operators_accept_any_diceable(side: int, other_side: int, n: int) -> None:
    """``Dice`` combines with ``Dice`` and ``DicePool`` on both sides of every operator."""
    d = Dice(1, side, MaxRandom())
    other = Dice(1, other_side, MinRandom())
    pool = DicePool([Dice(1, other_side, MinRandom()) for _ in range(n)])
    assert d + pool == side + n
    assert pool + d == n + side
    assert d - pool == side - n
    assert pool - d == n - side
    assert d * pool == side * n
    assert d * other == side
    assert d - other == side - 1


@pytest.mark.parametrize("operation", ["+", "-", "*"])
def test_dice_operators_reject_unsupported_types(operation: str) -> None:
    """Unsupported operands raise DiceOperationTypeError (a TypeError)."""
    with pytest.raises(DiceOperationTypeError):
        eval(f"Dice(1, 6) {operation} 'not a die'")  # noqa: S307


def test_fate_dice_all_faces_reachable() -> None:
    """Test that a Fate die (dF) produces exactly the faces -1, 0 and +1."""
    fate = Dice(-1, 1)
    assert {fate.roll() for _ in range(500)} == {-1, 0, 1}


@pytest.mark.parametrize(
    "inserted_strategy",
    [
        (DefaultRoll()),
        (DisadvantageRoll()),
        (AdvantageRoll()),
        (MultipleRoll(times=1)),
    ],
)
def test_dice_roll_with_inserted_strategy(inserted_strategy: RollStrategy, create_dice: Dice) -> None:
    """
    Test that dice roll works correctly with various roll strategies.

    Args:
        inserted_strategy: The roll strategy to test
        create_dice: Fixture providing a Dice instance

    Verifies that all strategy types produce valid roll results within expected range.
    """
    assert 1 <= create_dice.roll(inserted_roll_strategy=inserted_strategy) <= 20


@pytest.mark.parametrize("random_strategy", [(DefaultRandomStrategy()), (PseudoRandomStrategy())])
def test_create_dice_with_different_random_strategies(random_strategy: RandomStrategy) -> None:
    """
    Test that Dice works correctly with different randomization strategies.

    Args:
        random_strategy: The randomization strategy to test

    Ensures that both default and pseudo-random strategies produce valid results.
    """
    dice_object = Dice(1, 20, random_strategy)
    assert 1 <= dice_object.roll() <= 20
