# dicing — Python-библиотека кубиков для настольных RPG

[![CI](https://github.com/Cewerty/dicing/actions/workflows/ci.yaml/badge.svg)](https://github.com/Cewerty/dicing/actions/workflows/ci.yaml)
[![Coverage](https://raw.githubusercontent.com/Cewerty/dicing/python-coverage-comment-action-data/badge.svg?v=2)](https://github.com/Cewerty/dicing/tree/python-coverage-comment-action-data)
[![PyPI](https://img.shields.io/pypi/v/dicing?label=PyPI)](https://pypi.org/project/dicing/)
[![Docs](https://img.shields.io/badge/docs-GitHub%20Pages-blue)](https://cewerty.github.io/dicing/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](https://github.com/Cewerty/dicing/blob/main/LICENSE)

**English:** `dicing` is a typed, extensible dice library for tabletop RPGs: dice and dice pools, advantage/disadvantage,
keep/drop, a dice notation parser (`4d6kh3+2`), swappable roll/RNG strategies, seeded reproducible rolls and a CLI.
Install: `pip install dicing`. The documentation below is in Russian.

---

`dicing` — типизированная библиотека для бросков кубиков в настольных ролевых играх (D&D, Pathfinder и др.):
кубики и пулы кубиков, преимущество/помеха, keep/drop, разбор нотации вида `4d6kh3+2`
и подменяемые стратегии бросков и генерации случайных чисел.

## Возможности

- `Dice` — иммутабельный кубик с произвольными гранями, включая отрицательные (Fate: `Dice(-1, 1)`)
- `DicePool` — изменяемый пул кубиков (добавление, удаление, итерация, индексация)
- Алиасы стандартных кубиков: `d4`, `d6`, `d8`, `d10`, `d10_percentages` (0–9), `d12`, `d20`
- Механики: `adv` / `dis` (преимущество/помеха), `kh` / `kl` (оставить лучшие/худшие), `dh` / `dl` (отбросить лучшие/худшие)
- Разбор нотации: `parse_dice_notation("4d6kh3+2")` на грамматике [Lark](https://github.com/lark-parser/lark),
  с разбивкой результата: какие кубики выпали, какие отброшены, итог
- Командная строка: `dicing "4d6kh3+2"`
- Подменяемые стратегии броска (`DefaultRoll`, `AdvantageRoll`, `DisadvantageRoll`, `MultipleRoll`)
  и генерации чисел (`DefaultRandomStrategy` на `secrets.SystemRandom`, `PseudoRandomStrategy` на `random`)
- Контекстные менеджеры `DiceContext` / `DicePoolContext` для временной подмены стратегий
- Сериализация `to_dict()` / `from_dict()`
- Аннотации типов и `py.typed`; код проверяется `mypy`, `ty` и `ruff`

## Установка

```bash
pip install dicing
# или
uv add dicing
```

Последняя версия из `main`: `pip install git+https://github.com/Cewerty/dicing`.

Требуется Python 3.10+.

## Командная строка

После установки доступна команда `dicing` (или `python -m dicing`):

```console
$ dicing "4d6kh3+2"
4d6kh3: 6 6 1 (dropped: 1) = 13
+2
total: 15

$ dicing "1d20-1d4+3" --times 2
1d20: 11 = 11
-1d4: 2 = 2
+3
total: 12

1d20: 13 = 13
-1d4: 1 = 1
+3
total: 15

$ dicing "2d20kh" --total --times 3
19
9
16

$ dicing "4d6kh3+2" --json
{"notation": "4d6kh3+2", "groups": [{"label": "4d6kh3", "sign": 1, "rolls": [6, 1, 1, 6], "kept": [6, 6, 1], "dropped": [1], "subtotal": 13}], "modifier": 2, "total": 15}
```

| Флаг | Что делает |
| --- | --- |
| `--seed N` | воспроизводимый бросок (в примерах выше: `--seed 42`, `--seed 7`, `--seed 1`) |
| `--times N` | бросить выражение N раз |
| `--total` | вывести только итог — удобно для скриптов |
| `--json` | полный результат в JSON — для ботов и API |

Неверная нотация завершается с кодом 2 и сообщением в stderr: `dicing: error: invalid notation 'abc': ...`.

## Быстрый старт

```python
from dicing import DicePool, adv, d6, d20, kh, throws

d20().roll()                 # 1–20
d20().roll(modifier=5)       # d20 + 5
d20().check_success(15)      # True, если выпало >= 15

adv(d20())                   # преимущество: 2d20, берётся лучший

stats = DicePool([d6(), d6(), d6(), d6()])
kh(stats, 3)                 # 4d6kh3 — классическая генерация характеристик, например [6, 5, 3]
stats.roll()                 # сумма пула (4–24) — roll() всегда возвращает int
stats.roll(modifier=2)       # 4d6+2: модификатор прибавляется к сумме один раз
stats.roll_each()            # отдельные значения кубиков, например [4, 2, 6, 1]

list(throws(d6(), count=5))  # серия из 5 бросков, например [3, 5, 1, 6, 2]
```

### Нотация

```python
from dicing import parse_dice_notation

attack = parse_dice_notation("1d20+5")
attack.roll()                              # 6–25; каждый вызов — новый бросок

parse_dice_notation("4d6kh3").roll()       # 3–18
parse_dice_notation("4d6kh3+1d4").roll()   # 4–22
parse_dice_notation("1d20-1d4").roll()     # -3–19
parse_dice_notation("2d20kh").roll()       # преимущество: количество по умолчанию 1
```

Разбор ленивый: `parse_dice_notation` ничего не бросает, а возвращает `ParsedRoll` с группами кубиков
(`groups`) и числовым модификатором (`modifier`), который прибавляется к сумме один раз.

Поддерживается: `NdM` и `dM`, сложение и вычитание кубиков и чисел, модификаторы `kh`, `kl`, `dh`, `dl`
с необязательным количеством и в цепочке (`4d6kh3dl1`).

Для воспроизводимых результатов можно передать стратегию случайности, например `SeededRandomStrategy`
(см. ниже): `parse_dice_notation("2d6+3", SeededRandomStrategy(42))`.

### DSL: арифметика как в нотации

Операторы повторяют чтение нотации: число **слева** — количество кубиков, число **справа** — операция над результатом.

```python
from dicing import DicePool, d6

2 * d6()                  # DicePool из двух d6 — как «2d6», ещё не брошен
d6() * 2                  # бросок d6, умноженный на 2 (2, 4, …, 12)
d6() + 2                  # бросок d6 с модификатором +2
2 * DicePool([d6(), d6()])  # пул из четырёх d6
DicePool([d6(), d6()]) + 2  # 2d6+2: сумма пула плюс 2
DicePool([d6(), d6()]) * 3  # сумма броска пула, умноженная на 3
```

### Стратегии

```python
from dicing import AdvantageRoll, DiceContext, PseudoRandomStrategy, d20

# Временно бросать d20 с преимуществом: контекст выдаёт копию кубика,
# исходный не меняется, а незаданная стратегия (здесь — генератор) берётся от исходного
with DiceContext(d20(), replaced_roll_strategy=AdvantageRoll()) as lucky_d20:
    lucky_d20.roll()

# Подставить другой генератор случайных чисел
fast_d20 = d20(random_strategy=PseudoRandomStrategy())
```

**Воспроизводимые броски.** `SeededRandomStrategy(seed)`: одинаковый seed — одинаковая последовательность.
Один экземпляр можно передать всем кубикам выражения:

```python
from dicing import Dice, SeededRandomStrategy, parse_dice_notation

Dice(1, 20, SeededRandomStrategy(42)).roll()  # 4 — и так при каждом запуске
Dice(1, 20, SeededRandomStrategy(42)).roll()  # 4

stats = parse_dice_notation("4d6kh3+2", SeededRandomStrategy(42))
stats.roll(), stats.roll()                    # (15, 9) — та же пара при каждом запуске
```

Это используется для тестов, повторов бросков (например, в боте) и для примеров в документации:
все примеры в docstring'ах библиотеки — doctest'ы с фиксированным seed, поэтому показанные в них
результаты бросков проверяются при каждом запуске тестов.

Своя стратегия — любой класс с методом `randint(smallest, biggest) -> int` (протокол `RandomStrategy`)
или `roll(dice, modifier) -> int` (протокол `RollStrategy`); наследоваться ни от чего не нужно.

### Сериализация

```python
from dicing import DicePool, d6, d20

data = DicePool([d6(), d20()]).to_dict()
# {'dice': [{'smallest_side': 1, 'biggest_side': 6}, {'smallest_side': 1, 'biggest_side': 20}]}
DicePool.from_dict(data)  # DicePool(2 dice: [1d6, 1d20])
```

## Архитектура

- **Strategy.** Как генерировать случайные числа (`RandomStrategy`) и как бросать кубик (`RollStrategy`) —
  взаимозаменяемые алгоритмы, которые передаются в `Dice` через конструктор. Паттерн здесь оправдан тем,
  что у `RandomStrategy` есть несколько реальных реализаций с разными требованиями, и все они работают
  с одним и тем же, неизменным классом `Dice`:

  | Реализация | Зачем |
  | --- | --- |
  | `DefaultRandomStrategy` | криптостойкий `secrets.SystemRandom`: броски нельзя предсказать (по умолчанию) |
  | `PseudoRandomStrategy` | быстрый модуль `random` для массовых симуляций |
  | `SeededRandomStrategy` | воспроизводимость: doctest'ы, тесты, повтор бросков |
  | `MinRandom` / `MaxRandom` в тестах | заглушки, с которыми результат броска известен точно |

  Механика броска (`DefaultRoll`, `AdvantageRoll`, `DisadvantageRoll`, `MultipleRoll`) подменяется
  независимо от источника случайности — это вторая ось изменений того же паттерна.
- **Interpreter.** Нотация описана грамматикой Lark (`dice_grammar.lark`), а `Transformer` обходит дерево разбора
  и собирает из него ленивый `ParsedRoll`: группы кубиков со знаком и операциями keep/drop плюс модификатор.
- **Единый контракт `roll() -> int`.** И `Dice`, и `DicePool` возвращают из `roll()` одно число
  (модификатор прибавляется один раз); отдельные значения пула — `DicePool.roll_each()`.
- **Фабрика убрана.** Раньше была `DiceFactory` с мыслью о фабриках под системы (Fate, WoD).
  Убрал: системы различаются механикой интерпретации броска, а не набором кубиков,
  а наборы кубиков уже покрывают алиасы `d4`…`d20`.
- **Протоколы вместо наследования.** Стратегии описаны через `typing.Protocol`, поэтому пользовательские
  реализации подходят по форме, без зависимости от классов библиотеки.

## Ограничения и планы

- Механики систем с подсчётом успехов (World of Darkness, Shadowrun) и «взрывающиеся» кубики пока не поддерживаются.

## Разработка

```bash
uv sync --extra dev
make lint        # ruff
make typecheck-fast  # ty: быстрая проверка типов (меньше секунды), её же запускает pre-commit
make typecheck   # mypy: строгая проверка типов, её запускает CI
make test        # pytest + doctest + coverage
make smoke       # собрать wheel и проверить CLI на установленном пакете
make docs        # документация Sphinx (uv sync --extra docs): https://cewerty.github.io/dicing/
```

Правила оформления коммитов и устройство релизов — в
[CONTRIBUTING.md](https://github.com/Cewerty/dicing/blob/main/CONTRIBUTING.md).

CI (GitHub Actions) на каждый push и pull request:

- **линтинг и типы** — ruff, mypy и ty;
- **тесты** на Python 3.10, 3.11, 3.12 и 3.13; покрытие со всех версий объединяется ([python-coverage-comment-action](https://github.com/py-cov-action/python-coverage-comment-action)): оно показывается бейджем выше и комментарием в каждом pull request, внешние сервисы и токены не нужны;
- **документация** — Sphinx собирается на каждый pull request (предупреждения = ошибки) и публикуется на
  [GitHub Pages](https://cewerty.github.io/dicing/) после push в `main`;
- **сборка и smoke-тест** — wheel ставится в чистое окружение, и CLI запускается так, как его запустит
  пользователь (`scripts/cli_smoke_test.sh`). Это ловит ошибки упаковки, которые не видны юнит-тестам:
  например, если в wheel не попала грамматика `dice_grammar.lark` или точка входа `dicing`.

Релиз (`release.yaml`) запускается после зелёного CI на `main`: python-semantic-release по коммитам
в формате Conventional Commits вычисляет версию, обновляет CHANGELOG, ставит тег и создаёт GitHub Release;
затем пакет публикуется на TestPyPI, проверяется установкой оттуда и после ручного подтверждения
уходит на PyPI через Trusted Publishing.

Проверка типов разделена намеренно: [ty](https://github.com/astral-sh/ty) даёт мгновенную обратную связь
при каждом коммите, а mypy в CI остаётся надёжным gate'ом, пока ty не вышел из версии 0.0.x
(поэтому его версия закреплена точно).

`pytest` запускает и тесты из `tests/`, и doctest'ы из docstring'ов в `src/` (`--doctest-modules`
в `pyproject.toml`), поэтому примеры в документации не могут разойтись с кодом.

Тесты парсера и keep/drop написаны на [Hypothesis](https://hypothesis.readthedocs.io/): генерируются случайные
выражения вместе с ожидаемым результатом, а детерминированные стратегии (`MinRandom`, `MaxRandom`) позволяют
проверять итог броска точно, а не только по диапазону.

## Структура проекта

```text
src/dicing/
├── cli.py               # командная строка `dicing`
├── dice.py              # Dice, DicePool, adv/dis, kh/kl/dh/dl, throws
├── exceptions.py        # исключения библиотеки
├── strategies/          # стратегии броска и генерации чисел (Strategy)
├── aliases/             # d4…d20, create_dice, create_dicepool
└── utils/
    ├── parser/          # грамматика Lark и разбор нотации
    └── context_managers/
tests/                   # pytest + Hypothesis
scripts/cli_smoke_test.sh  # smoke-тест собранного wheel (CI и `make smoke`)
docs/                    # Sphinx
```

## Лицензия

[MIT](LICENSE)
