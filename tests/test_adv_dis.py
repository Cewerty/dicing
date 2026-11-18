from random import randint
from dicing.dice import Dice
import pytest
from dicing.dice import adv, dis
from typing import Any


@pytest.fixture
def get_dice() -> Dice:
    return Dice(1, 4)


def test_adv_with_correct_list(get_dice: Dice) -> None:
    dice_list = [get_dice for _ in range(5)]
    assert 1 <= adv(dice_list) <= 4


def test_adv_with_correct_dice(get_dice: Dice) -> None:
    assert 1 <= adv(get_dice) <= 4


def test_adv_with_incorrect_objects() -> None:
    with pytest.raises(TypeError):
        incorrect_list: Any = [randint(1, 4) for _ in range(5)]  # deliberately wrong type
        adv(incorrect_list)


def test_adv_with_incorrect_object() -> None:
    with pytest.raises(TypeError):
        incorrect_dice: Any = 1  # deliberately wrong type
        adv(incorrect_dice)


def test_dis_with_correct_list(get_dice: Dice) -> None:
    dice_list = [get_dice for _ in range(5)]
    assert 1 <= dis(dice_list) <= 4


def test_dis_with_correct_dice(get_dice: Dice) -> None:
    assert 1 <= dis(get_dice) <= 4


def test_dis_with_incorrect_objects() -> None:
    with pytest.raises(TypeError):
        incorrect_list: Any = [randint(1, 4) for _ in range(5)]  # deliberately wrong type
        dis(incorrect_list)


def test_dis_with_incorrect_object() -> None:
    with pytest.raises(TypeError):
        incorrect_dice: Any = 1  # deliberately wrong type
        dis(incorrect_dice)
