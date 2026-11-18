"""
Strategies of the Strategy pattern (GoF) used by :class:`~dicing.Dice`.

A die delegates two independent decisions to interchangeable objects:

- **where random numbers come from** — :class:`RandomStrategy`:
  :class:`DefaultRandomStrategy` (cryptographically strong, default),
  :class:`PseudoRandomStrategy` (fast ``random`` module),
  :class:`SeededRandomStrategy` (reproducible — for tests, replays and documentation);
- **how a roll is made** — :class:`RollStrategy`:
  :class:`DefaultRoll`, :class:`AdvantageRoll`, :class:`DisadvantageRoll`, :class:`MultipleRoll`.

Both are ``typing.Protocol`` s, so any object with a matching method works — no inheritance needed.

Example:
-------
    The same ``Dice`` class, without any changes, works with every source of randomness::

        >>> from dicing import Dice, DefaultRandomStrategy, PseudoRandomStrategy, SeededRandomStrategy
        >>> 1 <= Dice(1, 20, DefaultRandomStrategy()).roll() <= 20  # secure, unpredictable
        True
        >>> 1 <= Dice(1, 20, PseudoRandomStrategy()).roll() <= 20  # fast, unpredictable
        True
        >>> Dice(1, 20, SeededRandomStrategy(7)).roll()  # reproducible
        11
        >>> Dice(1, 20, SeededRandomStrategy(7)).roll()  # same seed -> same roll
        11

    A user-defined strategy plugs in the same way, e.g. a loaded die for a test::

        >>> class AlwaysMax:
        ...     def randint(self, smallest: int, biggest: int) -> int:
        ...         return biggest
        >>> Dice(1, 20, AlwaysMax()).roll()
        20

    The roll mechanics are swapped independently of the randomness::

        >>> from dicing import AdvantageRoll, DisadvantageRoll
        >>> d20 = Dice(1, 20, SeededRandomStrategy(7))
        >>> d20.roll(inserted_roll_strategy=AdvantageRoll())  # best of two
        11
        >>> d20.roll(inserted_roll_strategy=DisadvantageRoll())  # worst of two
        2

"""

from __future__ import annotations

import random
from secrets import SystemRandom
from typing import TYPE_CHECKING, ClassVar, Protocol
from weakref import WeakValueDictionary

from .._compat import override

if TYPE_CHECKING:
    from ..dice import Dice


class RandomStrategy(Protocol):
    """Protocol for random number generation strategies."""

    def randint(self, smallest: int, biggest: int) -> int:
        """
        Generate a random integer between smallest and biggest (inclusive).

        Args:
            smallest: Lower bound (inclusive)
            biggest: Upper bound (inclusive)

        Returns:
            Random integer in range [smallest, biggest]

        """


class DefaultRandomStrategy:
    """Cryptographically strong random number strategy using system RNG."""

    def __init__(self) -> None:
        """Initialize the strategy with a secure random number generator."""
        self._systemRandom: SystemRandom = SystemRandom()

    def randint(self, smallest: int, biggest: int) -> int:
        """
        Generate a cryptographically strong random integer.

        Args:
            smallest: Lower bound (inclusive)
            biggest: Upper bound (inclusive)

        Returns:
            Secure random integer in range [smallest, biggest]

        """
        return self._systemRandom.randint(a=smallest, b=biggest)


class PseudoRandomStrategy:
    """Standard pseudo-random number strategy using Python's random module."""

    def randint(self, smallest: int, biggest: int) -> int:
        """
        Generate a pseudo-random integer.

        Args:
            smallest: Lower bound (inclusive)
            biggest: Upper bound (inclusive)

        Returns:
            Pseudo-random integer in range [smallest, biggest]

        Note:
            Not suitable for cryptographic purposes

        """
        return random.randint(smallest, biggest)  # noqa: S311


class SeededRandomStrategy:
    """
    Reproducible pseudo-random strategy: the same seed gives the same sequence of numbers.

    Each instance owns its own generator, so it doesn't affect (and isn't affected by)
    the global ``random`` state. Share one instance between dice to make a whole pool
    or parsed expression reproducible. Not suitable for cryptographic purposes.
    """

    def __init__(self, seed: int | str | bytes) -> None:
        """
        Initialize the strategy with a private generator.

        Args:
            seed: Seed of the generator

        """
        self._random = random.Random(seed)  # noqa: S311

    def randint(self, smallest: int, biggest: int) -> int:
        """
        Return the next number of the seeded sequence.

        Args:
            smallest: Lower bound (inclusive)
            biggest: Upper bound (inclusive)

        Returns:
            Integer in range [smallest, biggest]

        """
        return self._random.randint(smallest, biggest)


class RollStrategy(Protocol):
    """Protocol for dice rolling strategies."""

    def roll(self, dice: Dice, modifier: int = 0) -> int:
        """
        Execute a dice roll with optional modifier.

        Args:
            dice: Dice instance to roll
            modifier: Modifier to add to the result (default 0)

        Returns:
            Result of the dice roll with modifier applied

        """


class DefaultRoll:
    """Standard single-die rolling strategy."""

    def roll(self, dice: Dice, modifier: int = 0) -> int:
        """
        Roll a single die and apply modifier.

        Args:
            dice: Dice instance to roll
            modifier: Modifier to add to the result

        Returns:
            Single die roll result + modifier

        """
        return (dice.randomization_strategy.randint(dice.smallest_side, dice.biggest_side)) + modifier


class DisadvantageRoll:
    """Roll strategy that takes the lowest of two dice rolls."""

    def roll(self, dice: Dice, modifier: int = 0) -> int:
        """
        Roll two dice and take the lowest result.

        Args:
            dice: Dice instance to roll
            modifier: Modifier to add to the result

        Returns:
            Lowest roll result + modifier

        """
        first_roll = dice.randomization_strategy.randint(dice.smallest_side, dice.biggest_side)
        second_roll = dice.randomization_strategy.randint(dice.smallest_side, dice.biggest_side)
        return min(first_roll, second_roll) + modifier


class AdvantageRoll:
    """Roll strategy that takes the highest of two dice rolls."""

    def roll(self, dice: Dice, modifier: int = 0) -> int:
        """
        Roll two dice and take the highest result.

        Args:
            dice: Dice instance to roll
            modifier: Modifier to add to the result

        Returns:
            Highest roll result + modifier

        """
        first_roll = dice.randomization_strategy.randint(dice.smallest_side, dice.biggest_side)
        second_roll = dice.randomization_strategy.randint(dice.smallest_side, dice.biggest_side)
        return max(first_roll, second_roll) + modifier


class MultipleRoll:
    """Roll strategy for multiple dice with instance caching."""

    __slots__ = ("__weakref__", "_times")
    _instances: ClassVar[WeakValueDictionary[int, MultipleRoll]] = WeakValueDictionary()
    _times: int

    @override
    def __hash__(self) -> int:
        """
        Generate a hash value based on the number of rolls.

        Returns:
            Hash value of the times attribute

        Note:
            Supports usage in hashable collections (dicts, sets).

        """
        return hash(self.times)

    @override
    def __eq__(self, other: object) -> bool:
        """
        Compare instances for equality based on roll count.

        Args:
            other: Another instance to compare with

        Returns:
            True if both are MultipleRoll instances with same times value

        Note:
            Enables value-based comparison instead of instance identity.

        """
        if not isinstance(other, MultipleRoll):
            raise NotImplementedError
        return isinstance(other, MultipleRoll) and other.times == self.times

    def __new__(cls, times: int = 1) -> MultipleRoll:
        """
        Create or retrieve a cached instance for the specified number of rolls.

        Args:
            times: Number of dice to roll

        Returns:
            Cached or new MultipleRoll instance

        Example:
            >>> a = MultipleRoll(3)
            >>> b = MultipleRoll(3)
            >>> a is b
            True

        """
        if times in cls._instances:
            return cls._instances[times]
        self = object.__new__(cls)
        object.__setattr__(self, "_times", times)
        cls._instances[times] = self
        return self

    @classmethod
    def clear_instances(cls) -> None:
        """
        Clear all cached instances of the class.

        Note:
            Useful for resetting the instance cache during runtime.

        """
        cls._instances.clear()

    @property
    def times(self) -> int:
        """
        Get the number of dice to roll.

        Returns:
            Number of dice (read-only)

        """
        return self._times

    def roll(self, dice: Dice, modifier: int = 0) -> int:
        """
        Roll multiple dice and sum the results.

        Args:
            dice: Dice instance to roll
            modifier: Modifier to add to the total

        Returns:
            Sum of all dice rolls + modifier

        Example:
            >>> from dicing import Dice, SeededRandomStrategy
            >>> d6 = Dice(1, 6, SeededRandomStrategy(42))
            >>> MultipleRoll(3).roll(d6)  # the same die rolled 3 times and summed, like 3d6
            8

        """
        return (
            sum(dice.randomization_strategy.randint(dice.smallest_side, dice.biggest_side) for _ in range(self.times))
            + modifier
        )
