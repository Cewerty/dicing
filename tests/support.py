"""Shared test doubles and Hypothesis strategies."""

from __future__ import annotations

from dataclasses import dataclass

from hypothesis import strategies as st

from dicing import Dice


class MaxRandom:
    """Random strategy that always returns the biggest side."""

    def randint(self, smallest: int, biggest: int) -> int:
        """Return the biggest side."""
        return biggest


class MinRandom:
    """Random strategy that always returns the smallest side."""

    def randint(self, smallest: int, biggest: int) -> int:
        """Return the smallest side."""
        return smallest


class MaxRoll:
    """Roll strategy that always returns the biggest side plus the modifier."""

    def roll(self, dice: Dice, modifier: int = 0) -> int:
        """Return the biggest side plus the modifier."""
        return dice.biggest_side + modifier


@dataclass(frozen=True)
class Expr:
    """
    Generated notation together with everything a correct parser must produce for it.

    ``at_min`` / ``at_max`` — total when every die shows its smallest / biggest side;
    ``low`` / ``high`` — bounds of any real roll (differ from at_min/at_max once dice are subtracted).
    """

    text: str
    groups: int
    modifier: int
    at_min: int
    at_max: int
    low: int
    high: int

    def combine(self, operator: str, other: Expr, space: str = "") -> Expr:
        """Join two expressions with ``+`` or ``-`` and derive the expected values."""
        text = f"{self.text}{space}{operator}{space}{other.text}"
        if operator == "+":
            return Expr(
                text,
                self.groups + other.groups,
                self.modifier + other.modifier,
                self.at_min + other.at_min,
                self.at_max + other.at_max,
                self.low + other.low,
                self.high + other.high,
            )
        return Expr(
            text,
            self.groups + other.groups,
            self.modifier - other.modifier,
            self.at_min - other.at_min,
            self.at_max - other.at_max,
            self.low - other.high,
            self.high - other.low,
        )


KEEP_CODES = ("kh", "kl")
DROP_CODES = ("dh", "dl")


@st.composite
def dice_terms(draw: st.DrawFn) -> Expr:
    """Single dice group like ``d20``, ``4d6kh3``, ``2d20kh`` or ``6d8dl2kh3``."""
    count = draw(st.integers(1, 20))
    sides = draw(st.integers(2, 100))
    text = ("" if count == 1 and draw(st.booleans()) else str(count)) + f"d{sides}"

    kept = count
    for _ in range(draw(st.integers(0, 2))):
        code = draw(st.sampled_from(KEEP_CODES + DROP_CODES))
        if code in KEEP_CODES:
            amount = draw(st.integers(1, kept))
            kept = amount
        else:
            amount = draw(st.integers(0, kept - 1))
            kept -= amount
        text += code + ("" if amount == 1 and draw(st.booleans()) else str(amount))

    return Expr(text, groups=1, modifier=0, at_min=kept, at_max=kept * sides, low=kept, high=kept * sides)


def modifier_terms() -> st.SearchStrategy[Expr]:
    """Integer term like the ``3`` in ``2d6+3``."""
    return st.integers(0, 100).map(lambda v: Expr(str(v), 0, v, v, v, v, v))


@st.composite
def expressions(draw: st.DrawFn) -> Expr:
    """1..4 dice/integer terms joined by ``+``/``-``, with or without spaces."""
    terms = draw(st.lists(st.one_of(dice_terms(), modifier_terms()), min_size=1, max_size=4))
    space = draw(st.sampled_from(["", " "]))
    result = terms[0]
    for term in terms[1:]:
        result = result.combine(draw(st.sampled_from("+-")), term, space)
    return result
