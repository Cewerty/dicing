"""Custom exceptions for the dicing library, tailored for TRPG dice mechanics."""


class DiceInvalidSidesError(ValueError):
    """
    Raised when dice sides are invalid (min >= max).

    Sides may be negative (e.g. Fate dice with faces -1..1), but min must be less than max.

    """

    pass


class DiceOperationTypeError(TypeError):
    """
    Raised when invalid types are used in dice operations (e.g., d6 + 'string').

    In TRPG formulas like '2d6 + 3', operands must be ints or Dice.

    """

    pass


class InvalidDiceInputError(TypeError):
    """
    Raised when input to functions isn't Dice or iterable of Dice.

    For TRPG mechanics like advantage rolls, input must be valid dice.
    """

    pass


class InvalidDiceError(TypeError):
    """
    Raised when input to throws isn't a valid Dice object.

    In TRPG, throws require a proper dice object.

    """

    pass


class NegativeThrowCountError(ValueError):
    """
    Raised when throw count is negative.

    In TRPG, you can't throw a dice a negative number of times.

    """

    pass


class DiceInvalidAmountError(ValueError):
    """
    Raised for invalid keep or drop amounts in TRPG dice operations.

    In mechanics like '4d6 drop lowest', amounts must be non-negative and <= number of dice.
    """

    pass


class DiceCopyError(TypeError):
    """
    Raised when ``copy.deepcopy`` of a die fails because one of its strategies can't be copied.

    A deep copy must not share state with the original: silently returning the same die would
    make two "independent" dice consume one random generator.
    """

    pass
