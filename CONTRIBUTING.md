# Как вносить изменения

## Окружение

```bash
uv sync --extra dev
pre-commit install   # ставит и pre-commit-хуки (ruff, ty), и commit-msg-хук (commitizen)
```

Основные команды — в [Makefile](Makefile):

| Команда | Что делает |
| --- | --- |
| `make lint` | ruff |
| `make typecheck-fast` | ty — быстрая проверка типов, её же запускает pre-commit |
| `make typecheck` | mypy — строгая проверка типов, её запускает CI |
| `make test` | pytest + doctest'ы + покрытие |
| `make smoke` | собрать wheel и проверить CLI на установленном пакете |
| `make release-check` | проверить историю релизов и показать, какой будет следующая версия |

## Сообщения коммитов

Проект использует [Conventional Commits](https://www.conventionalcommits.org/ru/). По сообщениям коммитов
автоматически вычисляется следующая версия и пишется [CHANGELOG](CHANGELOG.md), поэтому формат важен.

```text
<тип>: <описание>

[необязательное тело]

[необязательный футер, например BREAKING CHANGE: ...]
```

Описание можно писать по-русски: `fix: исправлен разбор нотации d20+5-2`.

| Тип | Когда | Влияние на версию |
| --- | --- | --- |
| `feat` | новая возможность | minor: 0.3.3 → 0.4.0 |
| `fix` | исправление ошибки | patch: 0.3.3 → 0.3.4 |
| `perf` | ускорение без изменения поведения | patch |
| `feat!` / `fix!` или футер `BREAKING CHANGE:` | несовместимое изменение API | **пока версия 0.x — minor**; 1.0.0 выпускается вручную, когда API стабилизируется |
| `docs`, `refactor`, `test`, `chore`, `ci`, `style`, `build` | всё остальное | релиз не выпускается, в CHANGELOG не попадает |

Формат проверяется дважды: локально хуком `commit-msg` (commitizen) и в CI для каждого pull request.

## Как выходит релиз

Релизы полностью автоматические ([`.github/workflows/release.yaml`](.github/workflows/release.yaml)):

1. Push в `main` → CI (линтинг, типы, тесты на Python 3.10–3.13, smoke-тест wheel).
2. Если CI зелёный, python-semantic-release смотрит на коммиты после последнего тега. Если среди них есть
   `feat`/`fix`/`perf`, он поднимает версию в `pyproject.toml`, обновляет `uv.lock` и `CHANGELOG.md`,
   делает коммит `chore(release): X.Y.Z`, ставит тег `vX.Y.Z` и создаёт GitHub Release со сборкой.
3. Пакет публикуется на **TestPyPI**, ставится оттуда в чистое окружение и проверяется smoke-тестом CLI.
4. Публикация на **PyPI** ждёт ручного подтверждения (environment `pypi` в GitHub) — версию на PyPI
   нельзя перезалить, поэтому последний шаг остаётся за человеком.

Публикация идёт через [Trusted Publishing](https://docs.pypi.org/trusted-publishers/) (OIDC) —
API-токены PyPI в репозитории не хранятся.

Перед релизом скрипт [`scripts/ci/validate_release_history.py`](scripts/ci/validate_release_history.py)
проверяет, что последний тег версии есть в истории `main`: если историю переписали и тегнутый коммит
потерялся, релиз останавливается, а не выпускает неправильную версию.
