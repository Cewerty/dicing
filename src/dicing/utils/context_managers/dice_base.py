"""Base module for dice roller context managers."""

from abc import ABC, abstractmethod
from contextlib import AbstractContextManager
from types import TracebackType
from typing import Literal

from ..._compat import override
from ...dice import Dice, DicePool
from ...strategies import RandomStrategy, RollStrategy


def _proxy(die: Dice, rng_strategy: RandomStrategy | None, roll_strategy: RollStrategy | None) -> Dice:
    """Copy of ``die`` with the given strategies; a strategy that is None is taken from ``die``."""
    return Dice(
        die.smallest_side,
        die.biggest_side,
        rng_strategy if rng_strategy is not None else die.randomization_strategy,
        roll_strategy if roll_strategy is not None else die.roll_strategy,
    )


class BaseDiceContextManager(AbstractContextManager[Dice], ABC):
    """Base context manager for dice operations with strategy replacement."""

    def __init__(
        self,
        initial_dice: Dice,
        replaced_rng_strategy: RandomStrategy | None = None,
        replaced_roll_strategy: RollStrategy | None = None,
    ) -> None:
        """
        Initialize the context manager with dice and optional strategies.

        Args:
        ----
            initial_dice: The original dice instance to proxy
            replaced_rng_strategy: Optional RNG strategy to temporarily use (None keeps the die's own)
            replaced_roll_strategy: Optional roll strategy to temporarily use (None keeps the die's own)

        """
        self.initial_dice = initial_dice
        # None means "not replaced": the proxy inherits the strategy of the original die
        self.temp_rng_strategy = replaced_rng_strategy
        self.temp_roll_strategy = replaced_roll_strategy
        self.proxy_dice: Dice | None = None

    @override
    def __enter__(self) -> Dice:
        """
        Enter the context and create a proxy dice with temporary strategies.

        Returns
        -------
            A proxy dice instance with the temporary strategies applied

        """
        self.proxy_dice = _proxy(self.initial_dice, self.temp_rng_strategy, self.temp_roll_strategy)
        self.on_enter()
        return self.proxy_dice

    @override
    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> Literal[False]:
        """
        Exit the context and clean up the proxy dice.

        Args:
        ----
            exc_type: Exception type if an exception was raised
            exc_value: Exception value if an exception was raised
            traceback: Traceback if an exception was raised

        Returns:
        -------
            False to not suppress any exceptions

        """
        self.on_exit(exc_type, exc_value, traceback)
        self.proxy_dice = None
        return False

    @abstractmethod
    def on_enter(self) -> None:
        """Abstract method called when entering the context."""
        pass

    @abstractmethod
    def on_exit(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """
        Abstract method called when exiting the context.

        Args:
        ----
            exc_type: Exception type if an exception was raised
            exc_value: Exception value if an exception was raised
            traceback: Traceback if an exception was raised

        """
        pass


class DiceContext(BaseDiceContextManager):
    """Simple dice context manager with no additional behavior."""

    @override
    def on_enter(self) -> None:
        """No-op implementation for context entry."""
        pass

    @override
    def on_exit(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """
        No-op implementation for context exit.

        Args:
        ----
            exc_type: Exception type if an exception was raised
            exc_value: Exception value if an exception was raised
            traceback: Traceback if an exception was raised

        """
        pass


class BaseDicePoolContextManager(AbstractContextManager[DicePool], ABC):
    """Base context manager for dice pool operations with strategy replacement."""

    def __init__(
        self,
        initial_pool: DicePool,
        replaced_rng_strategy: RandomStrategy | None = None,
        replaced_roll_strategy: RollStrategy | None = None,
    ) -> None:
        """
        Initialize the context manager with dice pool and optional strategies.

        Args:
        ----
            initial_pool: The original dice pool instance to proxy
            replaced_rng_strategy: Optional RNG strategy to temporarily use for all dice (None keeps each die's own)
            replaced_roll_strategy: Optional roll strategy to temporarily use for all dice (None keeps each die's own)

        """
        self.initial_pool = initial_pool
        # None means "not replaced": the proxy inherits the strategy of the original die
        self.temp_rng_strategy = replaced_rng_strategy
        self.temp_roll_strategy = replaced_roll_strategy
        self.proxy_pool: DicePool | None = None

    @override
    def __enter__(self) -> DicePool:
        """
        Enter the context and create a proxy dice pool with temporary strategies.

        Returns
        -------
            A proxy dice pool instance with all dice using temporary strategies

        """
        proxy_dice_list = [_proxy(die, self.temp_rng_strategy, self.temp_roll_strategy) for die in self.initial_pool]
        self.proxy_pool = DicePool(proxy_dice_list)
        self.on_enter()
        return self.proxy_pool

    @override
    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> Literal[False]:
        """
        Exit the context and clean up the proxy dice pool.

        Args:
        ----
            exc_type: Exception type if an exception was raised
            exc_value: Exception value if an exception was raised
            traceback: Traceback if an exception was raised

        Returns:
        -------
            False to not suppress any exceptions

        """
        self.on_exit(exc_type, exc_value, traceback)
        self.proxy_pool = None
        return False

    @abstractmethod
    def on_enter(self) -> None:
        """Abstract method called when entering the context."""
        pass

    @abstractmethod
    def on_exit(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """
        Abstract method called when exiting the context.

        Args:
        ----
            exc_type: Exception type if an exception was raised
            exc_value: Exception value if an exception was raised
            traceback: Traceback if an exception was raised

        """
        pass


class DicePoolContext(BaseDicePoolContextManager):
    """Simple dice pool context manager with no additional behavior."""

    @override
    def on_enter(self) -> None:
        """No-op implementation for context entry."""
        pass

    @override
    def on_exit(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """
        No-op implementation for context exit.

        Args:
        ----
            exc_type: Exception type if an exception was raised
            exc_value: Exception value if an exception was raised
            traceback: Traceback if an exception was raised

        """
        pass
