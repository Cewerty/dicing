"""Factory method with basic dice partial preset."""

from functools import partial

from ..dice import Dice
from ..strategies import DefaultRandomStrategy, DefaultRoll, RandomStrategy, RollStrategy


def create_dice(
    smallest_side: int = 1,
    biggest_side: int = 4,
    *,
    random_strategy: RandomStrategy | None = None,
    roll_strategy: RollStrategy | None = None,
) -> Dice:
    """
    Create a single die with specified parameters.

    Args:
    ----
        smallest_side(int): Smallest face value of the die
        biggest_side(int): Largest face value of the die
        random_strategy (RandomStrategy): Random number generation strategy
        roll_strategy (RollStrategy): Dice rolling strategy

    Returns:
    -------
        Configured Dice instance

    """
    if random_strategy is None:
        random_strategy = DefaultRandomStrategy()
    if roll_strategy is None:
        roll_strategy = DefaultRoll()
    return Dice(smallest_side, biggest_side, random_strategy, roll_strategy)


d4 = partial(create_dice, 1, 4)
d6 = partial(create_dice, 1, 6)
d8 = partial(create_dice, 1, 8)
d10 = partial(create_dice, 1, 10)
d10_percentages = partial(create_dice, 0, 9)
d12 = partial(create_dice, 1, 12)
d20 = partial(create_dice, 1, 20)
