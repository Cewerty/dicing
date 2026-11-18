"""
Core dice model: :class:`Dice`, :class:`DicePool` and dice mechanics (adv/dis, keep/drop, throws).

``roll()`` always returns a single ``int`` — for a die and for a pool (sum of its dice).
Individual results of a pool are available through :meth:`DicePool.roll_each`.

Examples in this module use :class:`~dicing.strategies.SeededRandomStrategy`, so every
roll shown below is reproducible and checked by doctest.

Example:
-------
    >>> from dicing import Dice, SeededRandomStrategy
    >>> d20 = Dice(1, 20, SeededRandomStrategy(42))
    >>> d20.roll()
    4
    >>> d20.check_success(15)
    False

Warning:
-------
    Creating dice with invalid sides (min >= max) raises DiceInvalidSidesError (a ValueError).

"""

from __future__ import annotations

import heapq
from abc import ABC, abstractmethod
from collections.abc import Generator
from copy import copy, deepcopy
from dataclasses import dataclass, field, replace
from typing import Final, overload

from ._compat import override
from .exceptions import (
    DiceInvalidAmountError,
    DiceInvalidSidesError,
    DiceOperationTypeError,
    InvalidDiceError,
    InvalidDiceInputError,
    NegativeThrowCountError,
)
from .strategies import (
    DefaultRandomStrategy,
    DefaultRoll,
    RandomStrategy,
    RollStrategy,
)


class Diceable(ABC):
    """Interface for dice-like clasess."""

    @abstractmethod
    def check_success(self, check: int, inserted_roll_strategy: RollStrategy | None = None) -> bool:
        """
        Check success against a target number.

        Args:
        ----
            check: Target number to beat
            inserted_roll_strategy: Optional roll strategy override

        Returns:
        -------
            bool: True if roll meets/exceeds target, False otherwise

        """
        pass

    @abstractmethod
    def roll(
        self,
        modifier: int = 0,
        inserted_roll_strategy: RollStrategy | None = None,
    ) -> int:
        """
        Roll and return a single total.

        Args:
        ----
            modifier: Added to the total once
            inserted_roll_strategy: Optional roll strategy override

        Returns:
        -------
            int: Roll total with the modifier

        """
        pass


@dataclass(slots=True, frozen=True)
class Dice(Diceable):
    """
    Class for immutable dice.

    Negative sides are allowed (e.g. Fate dice ``Dice(-1, 1)``) as long as smallest < biggest.

    Attributes
    ----------
        _smallest_side (int): Smallest side of the die
        _biggest_side (int): Largest side of the die
        _randomization_strategy (RandomStrategy): Random number generation strategy
        _roll_strategy (RollStrategy): Dice rolling strategy

    Raises
    ------
        DiceInvalidSidesError: If smallest side is not less than biggest side

    """

    _smallest_side: int
    _biggest_side: int
    _randomization_strategy: Final[RandomStrategy] = field(default_factory=DefaultRandomStrategy)
    _roll_strategy: Final[RollStrategy] = field(default_factory=DefaultRoll)

    def __post_init__(self) -> None:
        """
        Initialize dice side validation.

        Raises
        ------
            DiceInvalidSidesError: When smallest side is not less than biggest side

        """
        if self.smallest_side >= self.biggest_side:
            raise DiceInvalidSidesError(
                f"Incorrect sides: smallest_side ({self._smallest_side}) "
                f"must be less than biggest_side ({self._biggest_side})."
            )

    @property
    def smallest_side(self) -> int:
        """
        Get the smallest side of the die.

        Returns:
        -------
            int: Smallest side value (read-only)

        Note:
        ----
            Value is set during instance creation

        """
        return self._smallest_side

    @property
    def biggest_side(self) -> int:
        """
        Get the largest side of the die.

        Returns:
        -------
            int: Largest side value (read-only)

        Note:
        ----
            Value is set during instance creation

        """
        return self._biggest_side

    @property
    def randomization_strategy(self) -> RandomStrategy:
        """
        Get the random number generation strategy.

        Returns:
        -------
            RandomStrategy: Randomization strategy instance

        Note:
        ----
            Value is set during instance creation

        """
        return self._randomization_strategy

    @property
    def roll_strategy(self) -> RollStrategy:
        """
        Get the dice rolling strategy.

        Returns:
        -------
            RollStrategy: Roll strategy instance

        Note:
        ----
            Value is set during instance creation

        """
        return self._roll_strategy

    @override
    def check_success(self, check: int, inserted_roll_strategy: RollStrategy | None = None) -> bool:
        """
        Check success against a target number.

        Args:
        ----
            check: Target number to beat
            inserted_roll_strategy: Optional roll strategy override

        Returns:
        -------
            bool: True if roll meets/exceeds target, False otherwise

        """
        return self.roll(inserted_roll_strategy=inserted_roll_strategy) >= check

    @override
    def roll(
        self,
        modifier: int = 0,
        inserted_roll_strategy: RollStrategy | None = None,
    ) -> int:
        """
        Roll the die with optional modifier.

        Args:
        ----
            modifier: Roll modifier to add
            inserted_roll_strategy: Optional roll strategy override

        Returns:
        -------
            int: Final roll result

        """
        if inserted_roll_strategy is None:
            return self.roll_strategy.roll(self, modifier)
        return inserted_roll_strategy.roll(self, modifier)

    def __add__(self, other: int | Diceable) -> int:
        """
        Add an integer modifier or another die to this die.

        When adding an integer, it acts as a modifier to a single roll.
        When adding another die, returns the sum of rolling both dice once.

        Args:
        ----
            other: Integer modifier or another Dice instance

        Returns:
        -------
            int: Result of the roll with modifier or sum of two dice

        Raises:
        ------
            DiceOperationTypeError: If other is neither int nor Dice

        Example:
        -------
            >>> from dicing import SeededRandomStrategy
            >>> rng = SeededRandomStrategy(42)
            >>> d6 = Dice(1, 6, rng)
            >>> d6 + 2  # d6+2
            8
            >>> d6 + Dice(1, 6, rng)  # sum of two d6 rolls
            2
            >>> d6 + DicePool([Dice(1, 4, rng), Dice(1, 4, rng)])  # d6 + 2d4
            11

        """
        if isinstance(other, int):
            return self.roll(modifier=other)
        elif isinstance(other, Diceable):
            return self.roll() + other.roll()
        else:
            raise DiceOperationTypeError(f"Cannot summarize Dice with {type(other)}")

    def __radd__(self, other: int | Diceable) -> int:
        """
        Handle right-side addition for integer modifiers.

        Enables commutative addition with integers (2 + dice).

        Args:
        ----
            other: Integer modifier

        Returns:
        -------
            int: Result of the roll with modifier

        Raises:
        ------
            DiceOperationTypeError: If other is not an integer

        Example:
        -------
            >>> from dicing import SeededRandomStrategy
            >>> d6 = Dice(1, 6, SeededRandomStrategy(42))
            >>> 2 + d6  # same as d6 + 2
            8

        """
        if isinstance(other, int):
            return self.roll(modifier=other)
        elif isinstance(other, Diceable):
            return self.roll() + other.roll()
        else:
            raise DiceOperationTypeError(f"Cannot summarize Dice with {type(other)}")

    def __sub__(self, other: int | Diceable) -> int:
        """
        Subtract an integer or another dice roll from this dice's roll result.

        This method allows subtraction of either an integer (as a modifier) from the
        result of rolling this dice, or the roll result of another dice object from
        this dice's roll result.

        Args:
        ----
            self: The Dice object being rolled.
            other: Either an integer to subtract from the roll result or another Dice
                object whose roll result will be subtracted.

        Returns:
        -------
            The result of subtracting either the integer or the other dice's roll
            from this dice's roll.

        Raises:
        ------
            DiceOperationTypeError: If the operand is neither an integer nor a Dice object.

        Examples:
        --------
            >>> from dicing import SeededRandomStrategy, d6, d20
            >>> rng = SeededRandomStrategy(42)
            >>> d6(random_strategy=rng) - 2  # d6-2
            4
            >>> d20(random_strategy=rng) - d6(random_strategy=rng)  # d20 roll minus d6 roll
            3

        """
        if isinstance(other, int):
            return self.roll(modifier=-other)
        elif isinstance(other, Diceable):
            return self.roll() - other.roll()
        else:
            raise DiceOperationTypeError(f"Cannot subtract Dice with {type(other)}")

    def __rsub__(self, other: int | Diceable) -> int:
        """
        Subtract an integer or another dice roll from this dice's roll result.

        This method allows subtraction where this dice object is the right operand,
        such as an integer minus this dice's roll or another dice's roll minus this
        dice's roll.

        Args:
        ----
            self: The Dice object being rolled.
            other: Either an integer from which this dice's roll result is subtracted,
                or another Dice object whose roll result is used as the minuend.

        Returns:
        -------
            The result of subtracting this dice's roll from either the integer or the
            other dice's roll.

        Raises:
        ------
            DiceOperationTypeError: If the operand is neither an integer nor a Dice object.

        Examples:
        --------
            >>> from dicing import SeededRandomStrategy, d6
            >>> 5 - d6(random_strategy=SeededRandomStrategy(42))  # 5 minus a d6 roll
            -1

        """
        if isinstance(other, int):
            return other - self.roll()
        elif isinstance(other, Diceable):
            return other.roll() - self.roll()
        else:
            raise DiceOperationTypeError(f"Cannot subtract Dice with {type(other)}")

    def __deepcopy__(self, memo: dict[int, object]) -> Dice:
        """
        Create a deep copy of this Dice instance.

        Handles copying of randomization and roll strategies while
        preserving the frozen and slotted nature of the class.

        Args:
        ----
            memo: Dictionary used by deepcopy to avoid infinite recursion

        Returns:
        -------
            Dice: New Dice instance with copied strategies

        Note:
        ----
            If strategy copying fails, returns the original instance

        """
        try:
            new_random_strategy = deepcopy(self._randomization_strategy, memo)
            new_roll_strategy = deepcopy(self._roll_strategy, memo)
            return replace(self, _randomization_strategy=new_random_strategy, _roll_strategy=new_roll_strategy)
        except Exception:
            return self

    def __mul__(self, other: int | Diceable) -> int:
        """
        Roll the die once and multiply the result (``d6 * 2`` — roll x 2).

        DSL rule: an integer on the right multiplies the result, an integer on the left
        is the number of dice (see ``__rmul__``).

        Args:
        ----
            other: Integer multiplier of the roll result

        Returns:
        -------
            int: Single roll result multiplied by ``other``

        Example:
        -------
            >>> from dicing import SeededRandomStrategy
            >>> Dice(1, 6, SeededRandomStrategy(42)) * 2  # one roll, doubled
            12

        """
        if isinstance(other, int):
            return self.roll() * other
        elif isinstance(other, Diceable):
            return self.roll() * other.roll()
        else:
            raise DiceOperationTypeError(f"Cannot multiply Dice with {type(other)}")

    @overload
    def __rmul__(self, other: int) -> DicePool: ...

    @overload
    def __rmul__(self, other: Diceable) -> int: ...

    def __rmul__(self, other: int | Diceable) -> DicePool | int:
        """
        Create a pool of dice when an integer is on the left (``3 * d6`` — notation 3d6).

        Args:
        ----
            other: Number of dice in the pool, or another Diceable to multiply roll results with

        Returns:
        -------
            DicePool | int: Pool of ``other`` copies of this die, or product of roll results

        Example:
        -------
            >>> d6 = Dice(1, 6)
            >>> len(3 * d6)  # three d6 dice, not rolled yet
            3

        """
        if isinstance(other, int):
            return DicePool([copy(self) for _ in range(other)])
        elif isinstance(other, Diceable):
            return self.roll() * other.roll()
        else:
            raise DiceOperationTypeError(f"Cannot multiply Dice with {type(other)}")

    def to_dict(self) -> dict[str, int]:
        """
        Serialize the Dice instance to a dictionary.

        Returns:
        -------
            dict: Dictionary representation with keys:
                - 'smallest_side': int
                - 'biggest_side': int

        Example:
        -------
            >>> d6 = Dice(1, 6)
            >>> d6.to_dict()
            {'smallest_side': 1, 'biggest_side': 6}

        Note:
        ----
            Strategy objects are not serialized as they are implementation details
            and typically not needed in API responses.

        """
        return {
            "smallest_side": self._smallest_side,
            "biggest_side": self._biggest_side,
        }

    @classmethod
    def from_dict(cls, data: dict[str, int]) -> Dice:
        """
        Create a Dice instance from a dictionary.

        Args:
        ----
            data: Dictionary with keys 'smallest_side' and 'biggest_side'

        Returns:
        -------
            Dice: New Dice instance

        Raises:
        ------
            KeyError: If required keys are missing
            TypeError: If values are not integers

        Example:
        -------
            >>> dice_data = {"smallest_side": 1, "biggest_side": 6}
            >>> d6 = Dice.from_dict(dice_data)
            >>> isinstance(d6, Dice)
            True

        """
        return cls(_smallest_side=data["smallest_side"], _biggest_side=data["biggest_side"])


def adv(dices: Dice | list[Dice]) -> int:
    """
    Return the maximum roll result from a collection of dice.

    This function accepts either a single dice object or a collection of dice objects,
    rolls all dice, and returns the highest result obtained.

    Args:
    ----
        dices: An object implementing the Dice interface, or an iterable collection
               of such objects.

    Returns:
    -------
        The highest value among all dice roll results.

    Raises:
    ------
        DiceOperationTypeError: If the provided argument is not a dice object or iterable collection,
                   or if any element in the collection doesn't implement the Dice interface.

    Examples:
    --------
        >>> from dicing import SeededRandomStrategy, d6, d20
        >>> rng = SeededRandomStrategy(42)
        >>> adv(d20(random_strategy=rng))  # single die: rolled twice, best result
        4
        >>> adv([d6(random_strategy=rng), d20(random_strategy=rng)])  # best of mixed dice
        9

    """
    if isinstance(dices, Dice):
        return max(dices.roll(), dices.roll())
    dice_list = _to_dice_list(dices)
    if not dice_list:
        raise InvalidDiceInputError("Cannot compute advantage on empty dice collection")
    return max(die.roll() for die in dice_list)


def dis(dices: Dice | list[Dice]) -> int:
    """
    Return the minimum roll result from a collection of dice.

    This function accepts either a single dice object or a collection of dice objects,
    rolls all dice, and returns the lowest result obtained.

    Args:
    ----
        dices: An object implementing the Dice interface, or an iterable collection
               of such objects.

    Returns:
    -------
        The lowest value among all dice roll results.

    Raises:
    ------
        DiceOperationTypeError: If the provided argument is not a dice object or iterable collection,
                   or if any element in the collection doesn't implement the Dice interface.

    Examples:
    --------
        >>> from dicing import SeededRandomStrategy, d6, d20
        >>> rng = SeededRandomStrategy(42)
        >>> dis(d20(random_strategy=rng))  # single die: rolled twice, worst result
        1
        >>> dis([d6(random_strategy=rng), d20(random_strategy=rng)])  # worst of mixed dice
        6

    """
    if isinstance(dices, Dice):
        return min(dices.roll(), dices.roll())
    dice_list = _to_dice_list(dices)
    if not dice_list:
        raise InvalidDiceInputError("Cannot compute disadvantage on empty dice collection")
    return min(die.roll() for die in dice_list)


def _to_dice_list(dices: Diceable | list[Dice]) -> list[Dice]:
    """Help to normalize input to list of Dice."""
    if isinstance(dices, Dice):
        return [dices]
    elif isinstance(dices, DicePool):
        return _to_dice_list(dices._dice_list)
    elif isinstance(dices, list):
        flat = []
        for item in dices:
            flat.extend(_to_dice_list(item))
        return flat
    if not isinstance(dices, list):
        raise InvalidDiceInputError("Input must be a Dice, DicePool or list of Dice.")
    return dices


def _validate_keep(keep: int, available: int) -> None:
    if keep <= 0:
        raise DiceInvalidAmountError(f"Cannot keep non-positive number of dice: {keep}")
    if keep > available:
        raise DiceInvalidAmountError(f"Cannot keep more dice than available: {keep} > {available}")


def _validate_drop(drop: int, available: int) -> None:
    if drop < 0:
        raise DiceInvalidAmountError(f"Cannot drop negative number of dice: {drop}")
    if drop > available:
        raise DiceInvalidAmountError(f"Cannot drop more dice than available: {drop} > {available}")


def keep_highest_rolls(rolls: list[int], keep: int) -> list[int]:
    """Keep the ``keep`` highest of already rolled values, sorted descending."""
    _validate_keep(keep, len(rolls))
    return heapq.nlargest(keep, rolls)


def keep_lowest_rolls(rolls: list[int], keep: int) -> list[int]:
    """Keep the ``keep`` lowest of already rolled values, sorted ascending."""
    _validate_keep(keep, len(rolls))
    return heapq.nsmallest(keep, rolls)


def drop_highest_rolls(rolls: list[int], drop: int) -> list[int]:
    """Drop the ``drop`` highest of already rolled values; the rest is sorted ascending."""
    _validate_drop(drop, len(rolls))
    return heapq.nsmallest(len(rolls) - drop, rolls)


def drop_lowest_rolls(rolls: list[int], drop: int) -> list[int]:
    """Drop the ``drop`` lowest of already rolled values; the rest is sorted descending."""
    _validate_drop(drop, len(rolls))
    return heapq.nlargest(len(rolls) - drop, rolls)


def kh(dices: Dice | list[Dice] | DicePool, keep: int) -> list[int]:
    """
    Keep the highest 'keep' rolls from the dice.

    Returns sorted list of kept rolls (descending). Efficient for large sets using heap.
    """
    dice_list = _to_dice_list(dices)
    _validate_keep(keep, len(dice_list))
    return keep_highest_rolls([die.roll() for die in dice_list], keep)


def kl(dices: Dice | list[Dice] | DicePool, keep: int) -> list[int]:
    """
    Keep the lowest 'keep' rolls from the dice.

    Returns sorted list of kept rolls (ascending). Efficient for large sets using heap.
    """
    dice_list = _to_dice_list(dices)
    _validate_keep(keep, len(dice_list))
    return keep_lowest_rolls([die.roll() for die in dice_list], keep)


def dh(dices: Dice | list[Dice] | DicePool, drop: int) -> list[int]:
    """
    Drop the highest 'drop' rolls from the dice (equivalent to keep lowest n-drop).

    Returns sorted list of remaining rolls (ascending). Handles drop=0 (all rolls) and drop=n (empty).
    """
    dice_list = _to_dice_list(dices)
    _validate_drop(drop, len(dice_list))
    return drop_highest_rolls([die.roll() for die in dice_list], drop)


def dl(dices: Dice | list[Dice] | DicePool, drop: int) -> list[int]:
    """
    Drop the lowest 'drop' rolls from the dice (equivalent to keep highest n-drop).

    Returns sorted list of remaining rolls (descending). Handles drop=0 (all rolls) and drop=n (empty).
    """
    dice_list = _to_dice_list(dices)
    _validate_drop(drop, len(dice_list))
    return drop_lowest_rolls([die.roll() for die in dice_list], drop)


def throws(dice: Diceable, count: int = 1, roll_modificator: int = 0) -> Generator[int, None, None]:
    """
    Generate a sequence of dice roll results for a specified number of throws.

    This function takes a single dice object, rolls it the specified number of times,
    and yields each roll result with an optional modifier applied.

    Args:
    ----
        dice: An object implementing the Dice interface, with a roll method.
        count: The number of times to roll the dice (default: 1).
        roll_modificator: An integer to add to each roll result (default: 0).

    Yields:
    ------
        The result of each dice roll, with the modifier applied.

    Raises:
    ------
        NegativeThrowCountError: If the count of throws is negative.
        InvalidDiceError: If the provided dice argument does not implement the Dice interface.

    Examples:
    --------
        >>> from dicing import DicePool, SeededRandomStrategy, d6, d20
        >>> rng = SeededRandomStrategy(42)
        >>> list(throws(d6(random_strategy=rng), count=3))  # three rolls of a d6
        [6, 1, 1]
        >>> list(throws(d20(random_strategy=rng), count=2, roll_modificator=3))  # two d20+3
        [12, 11]
        >>> list(throws(DicePool([d6(random_strategy=rng), d6(random_strategy=rng)]), count=2))  # 2d6 twice
        [4, 7]

    """
    if not isinstance(dice, Diceable):
        raise InvalidDiceError("Provided argument does not implement the Dice interface.")
    if count < 0:
        raise NegativeThrowCountError("Cannot roll a die a negative number of times.")
    while count > 0:
        yield dice.roll(modifier=roll_modificator)
        count -= 1


def get_rolls(d: Diceable) -> list[int]:
    """
    Roll and return individual results: one value for a die, one per die for a pool.

    Args:
    ----
        d: Diceable instance to roll

    Returns:
    -------
        list[int]: List of roll results

    Example:
    -------
        >>> from dicing import DicePool, SeededRandomStrategy, d6
        >>> rng = SeededRandomStrategy(42)
        >>> get_rolls(d6(random_strategy=rng))
        [6]
        >>> get_rolls(DicePool([d6(random_strategy=rng), d6(random_strategy=rng)]))
        [1, 1]

    """
    if isinstance(d, DicePool):
        return d.roll_each()
    return [d.roll()]


class DicePool(Diceable):  # noqa: PLR0904 — a collection type: roll API + list-like and arithmetic operators
    """
    Class for mutable dice pools.

    Represents a collection of Dice objects, allowing dynamic addition and removal.
    Provides a unified interface similar to Dice for rolling and operations.

    Attributes:
    ----------
        _dice_list (list[Dice]): List of Dice instances in the pool

    Raises:
    ------
        InvalidDiceInputError: If invalid items are added during initialization

    Example:
    -------
        A pool of three d6 (3d6)::

            >>> from dicing import SeededRandomStrategy, d6
            >>> rng = SeededRandomStrategy(42)
            >>> pool = DicePool([d6(random_strategy=rng) for _ in range(3)])
            >>> pool.roll()  # sum of the dice
            8
            >>> pool.roll(modifier=2)  # 3d6+2: the modifier is added to the sum once
            13
            >>> pool.roll_each()  # individual results
            [2, 2, 6]

    Note:
    ----
        DicePool is mutable, allowing addition/removal of dice after creation.

    """

    __slots__: tuple[str] = ("_dice_list",)

    def __init__(self, dices: list[Dice] | Dice) -> None:
        """
        Initialize the dice pool with given dice.

        Args:
        ----
            dices: Single Dice or list of Dice to include in the pool

        Raises:
        ------
            InvalidDiceInputError: If input contains invalid items

        Example:
        -------
            >>> from dicing.aliases import d6
            >>> pool = DicePool(d6())  # Single die pool
            >>> len(pool._dice_list) == 1
            True
            >>> pool = DicePool([d6(), d6()])
            >>> len(pool._dice_list) == 2
            True

        """
        self._dice_list = [dice for dice in _to_dice_list(dices)]

    @override
    def check_success(self, check: int, inserted_roll_strategy: RollStrategy | None = None) -> bool:
        """
        Check success against a target number for the pool sum.

        Rolls all dice in the pool, sums the results, and checks against the target.

        Args:
        ----
            check: Target number to beat
            inserted_roll_strategy: Optional roll strategy override for all dice

        Returns:
        -------
            bool: True if sum meets/exceeds target, False otherwise

        """
        return self.roll(inserted_roll_strategy=inserted_roll_strategy) >= check

    @override
    def roll(
        self,
        modifier: int = 0,
        inserted_roll_strategy: RollStrategy | None = None,
    ) -> int:
        """
        Roll all dice and return the sum plus the modifier (``2d6+3``).

        Args:
        ----
            modifier: Added to the sum once (not to each die)
            inserted_roll_strategy: Optional roll strategy override for all dice

        Returns:
        -------
            int: Sum of all dice plus the modifier

        """
        return sum(self.roll_each(inserted_roll_strategy)) + modifier

    def roll_each(self, inserted_roll_strategy: RollStrategy | None = None) -> list[int]:
        """
        Roll all dice and return the individual results.

        Args:
        ----
            inserted_roll_strategy: Optional roll strategy override for all dice

        Returns:
        -------
            list[int]: One result per die, in pool order

        """
        return [dice.roll(inserted_roll_strategy=inserted_roll_strategy) for dice in self._dice_list]

    def add_dice(self, added_dice: Dice) -> None:
        """
        Add one or more dice to the pool.

        Args:
        ----
            added_dice: Single Dice or list of Dice to add

        Raises:
        ------
            InvalidDiceInputError: If added items are invalid

        Example:
        -------
            >>> from dicing.aliases import d6
            >>> pool = DicePool(d6())
            >>> pool.add_dice(d6())
            >>> len(pool._dice_list) == 2
            True

        """
        self._dice_list.append(added_dice)

    def remove_dice(self, dice_to_remove: Dice) -> None:
        """
        Remove specified dice from the pool.

        Removes the first occurrence of the matching dice.

        Args:
        ----
            dice_to_remove: Single Diceable or list of Diceable to remove

        Raises:
        ------
            ValueError: If item not found in the pool
            InvalidDiceInputError: If input is invalid

        Example:
        -------
            >>> from dicing.aliases import d6
            >>> pool = DicePool([d6(), d6()])
            >>> dice = pool._dice_list[0]
            >>> pool.remove_dice(dice)
            >>> len(pool._dice_list) == 1
            True

        """
        self._dice_list.remove(dice_to_remove)

    def remove_dice_by_index(self, index_of_dice: int) -> None:
        """
        Remove dice from the pool by index.

        Args:
        ----
            index_of_dice: Index of the dice to remove (0-based)

        Raises:
        ------
            IndexError: If index is out of range

        Example:
        -------
            >>> from dicing.aliases import d6
            >>> pool = DicePool([d6(), d6()])
            >>> pool.remove_dice_by_index(0)
            >>> len(pool._dice_list) == 1
            True

        """
        self._dice_list.pop(index_of_dice)

    def __add__(self, other: int | Diceable) -> int:
        """
        Roll the pool and add an integer modifier or another Diceable's roll (``2d6+2``, ``2d6+1d4``).

        Args:
        ----
            other: Integer modifier (added to the sum once) or another Diceable

        Returns:
        -------
            int: Pool sum plus the modifier or the other roll

        Raises:
        ------
            DiceOperationTypeError: If other is neither int nor Diceable

        Example:
        -------
            >>> from dicing import SeededRandomStrategy, d4, d6
            >>> rng = SeededRandomStrategy(42)
            >>> pool = DicePool([d6(random_strategy=rng), d6(random_strategy=rng)])
            >>> pool + 2  # 2d6+2
            9
            >>> pool + d4(random_strategy=rng)  # 2d6+1d4
            10

        """
        if isinstance(other, int):
            return self.roll(modifier=other)
        elif isinstance(other, Diceable):
            return self.roll() + other.roll()
        else:
            raise DiceOperationTypeError(f"Cannot summarize Dice with {type(other)}")

    def __radd__(self, other: int | Diceable) -> int:
        """
        Handle ``other + pool``; addition is commutative, see :meth:`__add__`.

        Example:
        -------
            >>> from dicing import SeededRandomStrategy, d6
            >>> rng = SeededRandomStrategy(42)
            >>> 2 + DicePool([d6(random_strategy=rng), d6(random_strategy=rng)])  # same as 2d6+2
            9

        """
        return self.__add__(other)

    def __sub__(self, other: int | Diceable) -> int:
        """
        Roll the pool and subtract an integer or another Diceable's roll (``2d6-1``, ``2d6-1d4``).

        Args:
        ----
            other: Integer (subtracted from the sum once) or another Diceable

        Returns:
        -------
            int: Pool sum minus the integer or the other roll

        Raises:
        ------
            DiceOperationTypeError: If other is neither int nor Diceable

        Example:
        -------
            >>> from dicing import SeededRandomStrategy, d4, d6
            >>> rng = SeededRandomStrategy(42)
            >>> pool = DicePool([d6(random_strategy=rng), d6(random_strategy=rng)])
            >>> pool - 2  # 2d6-2
            5
            >>> pool - d4(random_strategy=rng)  # 2d6-1d4
            4

        """
        if isinstance(other, int):
            return self.roll(modifier=-other)
        elif isinstance(other, Diceable):
            return self.roll() - other.roll()
        else:
            raise DiceOperationTypeError(f"Cannot subtract Dice with {type(other)}")

    def __rsub__(self, other: int | Diceable) -> int:
        """
        Handle ``other - pool``: the pool sum is subtracted from ``other``.

        Raises:
        ------
            DiceOperationTypeError: If other is neither int nor Diceable

        Example:
        -------
            >>> from dicing import SeededRandomStrategy, d6
            >>> rng = SeededRandomStrategy(42)
            >>> 10 - DicePool([d6(random_strategy=rng), d6(random_strategy=rng)])
            3

        """
        if isinstance(other, int):
            return other - self.roll()
        elif isinstance(other, Diceable):
            return other.roll() - self.roll()
        else:
            raise DiceOperationTypeError(f"Cannot subtract Dice with {type(other)}")

    def __mul__(self, other: int | Diceable) -> int:
        """
        Roll the pool once and multiply the sum (``pool * 2`` — sum x 2).

        DSL rule: an integer on the right multiplies the result, on the left it repeats the pool.

        Args:
        ----
            other: Integer multiplier or Diceable whose roll multiplies the sum

        Returns:
        -------
            int: Multiplied pool sum

        Raises:
        ------
            DiceOperationTypeError: If other is neither int nor Diceable

        Example:
        -------
            >>> from dicing import SeededRandomStrategy, d6
            >>> rng = SeededRandomStrategy(42)
            >>> DicePool([d6(random_strategy=rng), d6(random_strategy=rng)]) * 2  # (2d6) x 2
            14

        """
        if isinstance(other, int):
            return self.roll() * other
        elif isinstance(other, Diceable):
            return self.roll() * other.roll()
        else:
            raise DiceOperationTypeError(f"Cannot multiply Dice with {type(other)}")

    @overload
    def __rmul__(self, other: int) -> DicePool: ...

    @overload
    def __rmul__(self, other: Diceable) -> int: ...

    def __rmul__(self, other: int | Diceable) -> DicePool | int:
        """
        Repeat the pool when an integer is on the left (``2 * pool`` — twice as many dice).

        Args:
        ----
            other: Number of pool repetitions, or Diceable to multiply roll results with

        Returns:
        -------
            DicePool | int: New pool with the dice repeated ``other`` times, or product of rolls

        Raises:
        ------
            DiceOperationTypeError: If other is neither int nor Diceable

        Example:
        -------
            >>> from dicing import d6
            >>> print(2 * DicePool([d6(), d6()]))  # not rolled yet
            DicePool(4 dice: [4d6])

        """
        if isinstance(other, int):
            return DicePool([copy(dice) for _ in range(other) for dice in self._dice_list])
        elif isinstance(other, Diceable):
            return other.roll() * self.roll()
        else:
            raise DiceOperationTypeError(f"Cannot multiply Dice with {type(other)}")

    def __iter__(self) -> Generator[Dice, None, None]:
        """
        Iterate over dice in the pool.

        Yields each Dice instance in the pool sequentially.

        Yields:
        ------
            Dice: Individual dice from the pool

        Example:
        -------
            >>> from dicing.aliases import d6
            >>> pool = DicePool([d6(), d6()])
            >>> for die in pool:
            ...     isinstance(die, Dice)
            True
            True

        """
        yield from self._dice_list

    def __len__(self) -> int:
        """
        Get the number of dice in the pool.

        Returns:
        -------
            int: Count of dice in the pool

        Example:
        -------
            >>> from dicing.aliases import d6
            >>> pool = DicePool([d6(), d6(), d6()])
            >>> len(pool)
            3

        """
        return len(self._dice_list)

    def __getitem__(self, index: int | slice) -> Dice | list[Dice]:
        """
        Get dice at specified index or slice.

        Supports both single index access and slicing operations.

        Args:
        ----
            index: Position of dice to retrieve (int) or slice range

        Returns:
        -------
            Dice | list[Dice]: Single die for int index, list of dice for slices

        Raises:
        ------
            IndexError: If index is out of range
            TypeError: If index is not int or slice

        Examples:
        --------
            >>> from dicing.aliases import d6, d20
            >>> pool = DicePool([d6(), d20(), d6()])
            >>> isinstance(pool[0], Dice)
            True
            >>> len(pool[1:3])
            2

        """
        if isinstance(index, int | slice):
            return self._dice_list[index]
        else:
            raise TypeError(f"Indices must be integers or slices, not {type(index).__name__}")

    def __contains__(self, item: Dice) -> bool:
        """
        Check if a specific die exists in the pool.

        Uses identity comparison (is) rather than value equality.

        Args:
        ----
            item: Dice instance to check for membership

        Returns:
        -------
            bool: True if die exists in pool, False otherwise

        Example:
        -------
            >>> from dicing.aliases import d6
            >>> die = d6()
            >>> pool = DicePool([die, d6()])
            >>> die in pool
            True

        """
        return item in self._dice_list

    @override
    def __repr__(self) -> str:
        """
        Get unambiguous string representation of the dice pool.

        Shows class name and contained dice in a reconstructible format.

        Returns:
        -------
            str: Developer-friendly representation

        Example:
        -------
            >>> from dicing.aliases import d6
            >>> pool = DicePool([d6(), d6()])
            >>> repr(pool)
            'DicePool([Dice(_smallest_side=1, _biggest_side=6, ...), Dice(_smallest_side=1, _biggest_side=6, ...)])'

        """
        dice_reprs = [repr(die) for die in self._dice_list]
        return f"{self.__class__.__name__}([{', '.join(dice_reprs)}])"

    @override
    def __str__(self) -> str:
        """
        Get human-readable string representation of the dice pool.

        Shows dice count and side configurations in a compact format.

        Returns:
        -------
            str: User-friendly representation

        Example:
        -------
            >>> from dicing.aliases import d6, d20
            >>> pool = DicePool([d6(), d20(), d6()])
            >>> str(pool)
            'DicePool(3 dice: [1d6, 1d20, 1d6])'

        """
        dice_notation = []
        current_die = None
        count = 0

        for die in self._dice_list:
            if (
                current_die
                and die._smallest_side == current_die._smallest_side
                and die._biggest_side == current_die._biggest_side
            ):
                count += 1
            else:
                if current_die:
                    dice_notation.append(
                        f"{count}d{current_die._biggest_side}" if count > 1 else f"1d{current_die._biggest_side}"
                    )
                current_die = die
                count = 1

        if current_die:
            dice_notation.append(
                f"{count}d{current_die._biggest_side}" if count > 1 else f"1d{current_die._biggest_side}"
            )

        return f"DicePool({len(self._dice_list)} dice: [{', '.join(dice_notation)}])"

    def to_dict(self) -> dict[str, list[dict[str, int]]]:
        """
        Serialize the DicePool instance to a dictionary.

        Returns:
        -------
            dict: Dictionary representation with key:
                - 'dice': list of serialized Dice dictionaries

        Example:
        -------
            >>> from dicing.aliases import d6, d20
            >>> pool = DicePool([d6(), d20()])
            >>> pool_dict = pool.to_dict()
            >>> len(pool_dict["dice"]) == 2
            True
            >>> pool_dict["dice"][0]["biggest_side"] == 6
            True

        """
        return {"dice": [die.to_dict() for die in self._dice_list]}

    @classmethod
    def from_dict(cls, data: dict[str, list[dict[str, int]]]) -> DicePool:
        """
        Create a DicePool instance from a dictionary.

        Args:
        ----
            data: Dictionary with key 'dice' containing list of Dice dictionaries

        Returns:
        -------
            DicePool: New DicePool instance

        Raises:
        ------
            KeyError: If required keys are missing
            TypeError: If values have incorrect types

        Example:
        -------
            >>> dice_data = {
            ...     "dice": [
            ...         {"smallest_side": 1, "biggest_side": 6},
            ...         {"smallest_side": 1, "biggest_side": 20},
            ...     ]
            ... }
            >>> print(DicePool.from_dict(dice_data))
            DicePool(2 dice: [1d6, 1d20])

        """
        dice_list = [Dice.from_dict(die_data) for die_data in data["dice"]]
        return cls(dice_list)
