"""
Command-line interface: ``dicing "4d6kh3+2"``.

Shows every die, which dice were dropped by keep/drop and the total.

Example:
-------
    >>> main(["4d6kh3+2", "--seed", "42"])
    4d6kh3: 6 6 1 (dropped: 1) = 13
    +2
    total: 15
    0
    >>> main(["4d6kh3+2", "--seed", "42", "--total"])
    15
    0

"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence

from lark.exceptions import LarkError

from . import __version__
from .strategies import SeededRandomStrategy
from .utils.parser import GroupRoll, RollResult, parse_dice_notation

EXIT_OK = 0
EXIT_INVALID_NOTATION = 2


def _positive_int(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError(f"must be a positive integer, got {value}")
    return number


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dicing",
        description="Roll dice written in TRPG notation, e.g. 4d6kh3+2, 1d20+5, 2d20kh, 1d20-1d4.",
    )
    parser.add_argument("notation", help="dice notation, e.g. '4d6kh3+2'")
    parser.add_argument("--seed", type=int, help="seed for reproducible rolls")
    parser.add_argument("--times", type=_positive_int, default=1, metavar="N", help="roll the expression N times")
    output = parser.add_mutually_exclusive_group()
    output.add_argument("--total", action="store_true", help="print only the total")
    output.add_argument("--json", action="store_true", help="print the full result as JSON")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def _format_group(group: GroupRoll) -> str:
    sign = "-" if group.sign < 0 else ""
    kept = " ".join(map(str, group.kept))
    dropped = f" (dropped: {' '.join(map(str, group.dropped))})" if group.dropped else ""
    return f"{sign}{group.label}: {kept}{dropped} = {sum(group.kept)}"


def _format_result(result: RollResult) -> str:
    lines = [_format_group(group) for group in result.groups]
    if result.modifier:
        lines.append(f"{result.modifier:+d}")
    lines.append(f"total: {result.total}")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    """
    Run the CLI.

    Args:
    ----
        argv: Command-line arguments without the program name; ``sys.argv[1:]`` if None

    Returns:
    -------
        int: Exit code — 0 on success, 2 on invalid notation or arguments

    """
    args = _build_parser().parse_args(argv)
    random_strategy = SeededRandomStrategy(args.seed) if args.seed is not None else None
    try:
        parsed = parse_dice_notation(args.notation, random_strategy)
    except (LarkError, ValueError) as error:
        message = str(error).strip().splitlines()[0] if str(error).strip() else type(error).__name__
        print(f"dicing: error: invalid notation {args.notation!r}: {message}", file=sys.stderr)
        return EXIT_INVALID_NOTATION

    results = [parsed.roll_detailed() for _ in range(args.times)]
    if args.json:
        payloads = [{"notation": args.notation, **result.to_dict()} for result in results]
        print(json.dumps(payloads[0] if args.times == 1 else payloads))
    elif args.total:
        print("\n".join(str(result.total) for result in results))
    else:
        print("\n\n".join(_format_result(result) for result in results))
    return EXIT_OK
