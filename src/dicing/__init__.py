"""
dicing — typed, extensible dice library for tabletop RPGs.

Everything listed in ``__all__`` is the public API and can be imported directly::

    from dicing import d6, d20, DicePool, adv, kh, parse_dice_notation
"""

from importlib.metadata import PackageNotFoundError, version

from .aliases import create_dice, create_dicepool, d4, d6, d8, d10, d10_percentages, d12, d20
from .dice import Dice, Diceable, DicePool, adv, dh, dis, dl, get_rolls, kh, kl, throws
from .exceptions import (
    DiceCopyError,
    DiceInvalidAmountError,
    DiceInvalidSidesError,
    DiceOperationTypeError,
    InvalidDiceError,
    InvalidDiceInputError,
    NegativeThrowCountError,
)
from .strategies import (
    AdvantageRoll,
    DefaultRandomStrategy,
    DefaultRoll,
    DisadvantageRoll,
    MultipleRoll,
    PseudoRandomStrategy,
    RandomStrategy,
    RollStrategy,
    SeededRandomStrategy,
)
from .utils.context_managers import DiceContext, DicePoolContext
from .utils.parser import DiceGroup, GroupRoll, ParsedRoll, RollResult, parse_dice_notation

try:
    __version__ = version("dicing")
except PackageNotFoundError:  # pragma: no cover - running from a source tree without installation
    __version__ = "0.0.0"

__all__ = [
    "AdvantageRoll",
    "DefaultRandomStrategy",
    "DefaultRoll",
    "Dice",
    "DiceContext",
    "DiceCopyError",
    "DiceGroup",
    "DiceInvalidAmountError",
    "DiceInvalidSidesError",
    "DiceOperationTypeError",
    "DicePool",
    "DicePoolContext",
    "Diceable",
    "DisadvantageRoll",
    "GroupRoll",
    "InvalidDiceError",
    "InvalidDiceInputError",
    "MultipleRoll",
    "NegativeThrowCountError",
    "ParsedRoll",
    "PseudoRandomStrategy",
    "RandomStrategy",
    "RollResult",
    "RollStrategy",
    "SeededRandomStrategy",
    "__version__",
    "adv",
    "create_dice",
    "create_dicepool",
    "d4",
    "d6",
    "d8",
    "d10",
    "d10_percentages",
    "d12",
    "d20",
    "dh",
    "dis",
    "dl",
    "get_rolls",
    "kh",
    "kl",
    "parse_dice_notation",
    "throws",
]
