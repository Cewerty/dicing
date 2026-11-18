"""
Dice notation parser.

Parses notation strings like ``"2d6+3"``, ``"4d6kh3+1d4"`` or ``"1d20-1d4"`` into a lazy
:class:`ParsedRoll`. Nothing is rolled during parsing: every call to :meth:`ParsedRoll.roll`
makes a fresh roll of the whole expression.

The grammar lives in ``dice_grammar.lark``; :class:`DiceTransformer` walks the Lark parse tree
and delegates the actual construction to :class:`DiceTransformationEngine` (Interpreter pattern).

Supported syntax:
    - ``NdM`` / ``dM`` — N dice with M sides (N defaults to 1)
    - ``kh``, ``kl``, ``dh``, ``dl`` with an optional amount (defaults to 1), chainable: ``4d6kh3dl1``
    - ``+`` and ``-`` between dice groups and integer modifiers

Example:
-------
    >>> from dicing import SeededRandomStrategy, parse_dice_notation
    >>> roll = parse_dice_notation("2d6+3", SeededRandomStrategy(42))
    >>> len(roll.groups), roll.modifier  # nothing is rolled yet
    (1, 3)
    >>> roll.roll()  # each call is a fresh roll of the whole expression
    10
    >>> roll.roll()
    10

"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import Final

from lark import Lark, Token, Transformer, v_args
from lark.exceptions import VisitError

from ...aliases import create_dice
from ...dice import DicePool, drop_highest_rolls, drop_lowest_rolls, keep_highest_rolls, keep_lowest_rolls
from ...strategies import RandomStrategy

# A keep/drop operation: notation code ("kh", "kl", "dh", "dl") and amount.
KeepDrop = tuple[str, int]

_KEEP_DROP: Final[dict[str, Callable[[list[int], int], list[int]]]] = {
    "kh": keep_highest_rolls,
    "kl": keep_lowest_rolls,
    "dh": drop_highest_rolls,
    "dl": drop_lowest_rolls,
}


@dataclass(frozen=True, slots=True)
class GroupRoll:
    """
    Detailed result of rolling one :class:`DiceGroup`.

    Attributes
    ----------
        label: Notation of the group, e.g. ``"4d6kh3"``
        sign: ``1`` if the group is added to the total, ``-1`` if subtracted
        rolls: Every die result, in roll order
        kept: Results left after keep/drop

    """

    label: str
    sign: int
    rolls: tuple[int, ...]
    kept: tuple[int, ...]

    @property
    def dropped(self) -> tuple[int, ...]:
        """Results removed by keep/drop, in roll order."""
        remaining = Counter(self.kept)
        dropped = []
        for value in self.rolls:
            if remaining[value]:
                remaining[value] -= 1
            else:
                dropped.append(value)
        return tuple(dropped)

    @property
    def subtotal(self) -> int:
        """Signed sum of the kept results."""
        return self.sign * sum(self.kept)

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable representation."""
        return {
            "label": self.label,
            "sign": self.sign,
            "rolls": list(self.rolls),
            "kept": list(self.kept),
            "dropped": list(self.dropped),
            "subtotal": self.subtotal,
        }


@dataclass(frozen=True, slots=True)
class RollResult:
    """
    Detailed result of rolling a whole :class:`ParsedRoll`.

    Attributes
    ----------
        groups: Results of every dice group
        modifier: Sum of the integer terms

    """

    groups: tuple[GroupRoll, ...]
    modifier: int

    @property
    def total(self) -> int:
        """Final result: signed subtotals of all groups plus the modifier."""
        return sum(group.subtotal for group in self.groups) + self.modifier

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable representation."""
        return {
            "groups": [group.to_dict() for group in self.groups],
            "modifier": self.modifier,
            "total": self.total,
        }


@dataclass(frozen=True, slots=True)
class DiceGroup:
    """
    One dice term of an expression, e.g. ``4d6kh3`` or the ``1d4`` in ``1d20-1d4``.

    Attributes
    ----------
        pool: Dice of the group
        keep_drop: Keep/drop operations applied to the rolls in order
        sign: ``1`` if the group is added to the total, ``-1`` if subtracted

    Raises
    ------
        DiceInvalidAmountError: If keep/drop amounts don't fit the number of dice (e.g. ``4d6kh5``)

    """

    pool: DicePool
    keep_drop: tuple[KeepDrop, ...] = ()
    sign: int = 1

    def __post_init__(self) -> None:
        """Validate the sign and keep/drop amounts without rolling the dice."""
        if self.sign not in {1, -1}:
            raise ValueError(f"Sign must be 1 or -1, got {self.sign}")
        self._apply_keep_drop([0] * len(self.pool))

    def _apply_keep_drop(self, rolls: list[int]) -> list[int]:
        for code, amount in self.keep_drop:
            rolls = _KEEP_DROP[code](rolls, amount)
        return rolls

    def label(self) -> str:
        """
        Return the notation of the group without its sign.

        Example:
        -------
            >>> from dicing import parse_dice_notation
            >>> [group.label() for group in parse_dice_notation("4d6kh3dl1 - d20").groups]
            ['4d6kh3dl1', '1d20']

        """
        sides = Counter(die.biggest_side for die in self.pool)
        dice = "+".join(f"{count}d{side}" for side, count in sides.items())
        return dice + "".join(f"{code}{amount}" for code, amount in self.keep_drop)

    def roll_detailed(self) -> GroupRoll:
        """Roll the group and return every result together with the kept ones."""
        rolls = self.pool.roll_each()
        return GroupRoll(self.label(), self.sign, tuple(rolls), tuple(self._apply_keep_drop(rolls)))

    def roll(self) -> list[int]:
        """Roll the group and return the kept rolls (sign is not applied)."""
        return list(self.roll_detailed().kept)

    def negated(self) -> DiceGroup:
        """Return the same group with the opposite sign."""
        return replace(self, sign=-self.sign)


@dataclass(frozen=True, slots=True)
class ParsedRoll:
    """
    Lazy result of parsing dice notation.

    Attributes
    ----------
        groups: Dice groups of the expression
        modifier: Sum of all integer terms, added to the total once

    """

    groups: tuple[DiceGroup, ...] = ()
    modifier: int = 0

    def roll_detailed(self) -> RollResult:
        """
        Roll every group and return the full breakdown: all rolls, kept and dropped dice, total.

        Example:
        -------
            >>> from dicing import SeededRandomStrategy, parse_dice_notation
            >>> result = parse_dice_notation("4d6kh3+2", SeededRandomStrategy(42)).roll_detailed()
            >>> group = result.groups[0]
            >>> group.label, group.rolls, group.kept, group.dropped
            ('4d6kh3', (6, 1, 1, 6), (6, 6, 1), (1,))
            >>> result.total
            15

        """
        return RollResult(tuple(group.roll_detailed() for group in self.groups), self.modifier)

    def roll(self) -> int:
        """Roll every group and return the total: signed sums of kept rolls plus the modifier."""
        return self.roll_detailed().total


class DiceTransformationEngine:
    """Builds :class:`ParsedRoll` objects from values extracted by :class:`DiceTransformer`."""

    def __init__(self, random_strategy: RandomStrategy | None = None) -> None:
        """
        Initialize the engine.

        Args:
        ----
            random_strategy: Random strategy for every created die; library default if None

        """
        self._random_strategy = random_strategy

    def process_dice_expr(self, count: int | None, sides: int, keep_drop: list[KeepDrop]) -> ParsedRoll:
        """
        Build a single dice group such as ``4d6kh3``.

        Raises
        ------
            ValueError: If the number of dice is not positive
            DiceInvalidSidesError: If the die has fewer than 2 sides
            DiceInvalidAmountError: If keep/drop amounts don't fit the number of dice

        """
        count = 1 if count is None else count
        if count < 1:
            raise ValueError(f"Number of dice must be positive, got {count}")
        pool = DicePool([create_dice(1, sides, random_strategy=self._random_strategy) for _ in range(count)])
        return ParsedRoll((DiceGroup(pool, tuple(keep_drop)),), 0)

    @staticmethod
    def process_modifier(value: int) -> ParsedRoll:
        """Build an integer term such as the ``3`` in ``2d6+3``."""
        return ParsedRoll((), value)

    def process_expr(self, items: list[ParsedRoll | str]) -> ParsedRoll:
        """
        Combine ``[term, op, term, op, term, ...]`` into one roll.

        ``+`` appends the right term; ``-`` appends it with negated dice groups and subtracts its modifier.

        Raises
        ------
            TypeError: If the items don't alternate between terms and operators

        """
        result = self._expect_roll(items[0])
        for operator, item in zip(items[1::2], items[2::2], strict=True):
            term = self._expect_roll(item)
            if operator == "+":
                result = ParsedRoll(result.groups + term.groups, result.modifier + term.modifier)
            elif operator == "-":
                negated = tuple(group.negated() for group in term.groups)
                result = ParsedRoll(result.groups + negated, result.modifier - term.modifier)
            else:
                raise TypeError(f"Unknown operator: {operator!r}")
        return result

    @staticmethod
    def _expect_roll(item: object) -> ParsedRoll:
        if not isinstance(item, ParsedRoll):
            raise TypeError(f"Expected a parsed term, got {item!r}")
        return item


def _amount(value: Token | None) -> int:
    return 1 if value is None else int(value)


class DiceTransformer(Transformer[Token, ParsedRoll]):
    """Lark transformer: turns parse tree nodes into values and passes them to the engine."""

    def __init__(self, random_strategy: RandomStrategy | None = None) -> None:
        """
        Initialize the transformer and its engine.

        Args:
        ----
            random_strategy: Random strategy for every created die; library default if None

        """
        super().__init__()
        self.engine = DiceTransformationEngine(random_strategy)

    def start(self, items: list[ParsedRoll]) -> ParsedRoll:
        """Return the parsed expression."""
        return items[0]

    def expr(self, items: list[ParsedRoll | str]) -> ParsedRoll:
        """Combine terms joined by ``+`` / ``-``."""
        return self.engine.process_expr(items)

    def dice_expr(self, items: list[int | KeepDrop | None]) -> ParsedRoll:
        """Build a dice group from ``[count | None, sides, *keep_drop]``."""
        count, sides, *keep_drop = items
        if not isinstance(sides, int) or (count is not None and not isinstance(count, int)):
            raise TypeError(f"Unexpected dice expression items: {items!r}")
        return self.engine.process_dice_expr(count, sides, [mod for mod in keep_drop if isinstance(mod, tuple)])

    @v_args(inline=True)
    def modifier(self, value: Token) -> ParsedRoll:
        """Build an integer term."""
        return self.engine.process_modifier(int(value))

    @v_args(inline=True)
    def count(self, value: Token) -> int:
        """Return the number of dice."""
        return int(value)

    @v_args(inline=True)
    def sides(self, value: Token) -> int:
        """Return the number of sides."""
        return int(value)

    @v_args(inline=True)
    def add(self) -> str:
        """Return the ``+`` operator."""
        return "+"

    @v_args(inline=True)
    def sub(self) -> str:
        """Return the ``-`` operator."""
        return "-"

    @v_args(inline=True)
    def keep_highest(self, value: Token | None) -> KeepDrop:
        """Return ``("kh", amount)``."""
        return ("kh", _amount(value))

    @v_args(inline=True)
    def keep_lowest(self, value: Token | None) -> KeepDrop:
        """Return ``("kl", amount)``."""
        return ("kl", _amount(value))

    @v_args(inline=True)
    def drop_highest(self, value: Token | None) -> KeepDrop:
        """Return ``("dh", amount)``."""
        return ("dh", _amount(value))

    @v_args(inline=True)
    def drop_lowest(self, value: Token | None) -> KeepDrop:
        """Return ``("dl", amount)``."""
        return ("dl", _amount(value))


_PARSER: Final = Lark.open("dice_grammar.lark", rel_to=__file__, parser="lalr", maybe_placeholders=True)


def parse_dice_notation(notation: str, random_strategy: RandomStrategy | None = None) -> ParsedRoll:
    """
    Parse dice notation into a lazy :class:`ParsedRoll`.

    Args:
    ----
        notation: Notation string, e.g. ``"2d6+3"``, ``"4d6kh3+1d4"``, ``"1d20-1d4"``
        random_strategy: Random strategy for every die of the expression; library default if None.
            Passing a deterministic strategy makes the result reproducible (useful in tests).

    Returns:
    -------
        ParsedRoll: Expression that can be rolled any number of times

    Raises:
    ------
        lark.exceptions.LarkError: If the string doesn't match the notation grammar
        ValueError: If the expression is invalid (e.g. ``0d6``, ``1d1``, ``4d6kh5``)

    Example:
    -------
        >>> from dicing import SeededRandomStrategy
        >>> parse_dice_notation("4d6kh3", SeededRandomStrategy(42)).roll()
        13
        >>> parse_dice_notation("1d20+5-1d4", SeededRandomStrategy(42)).roll()
        8

    """
    tree = _PARSER.parse(notation)
    try:
        return DiceTransformer(random_strategy).transform(tree)
    except VisitError as error:
        # Lark wraps exceptions raised inside transformer callbacks; surface the original one.
        raise error.orig_exc from None
