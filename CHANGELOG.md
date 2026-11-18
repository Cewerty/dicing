# CHANGELOG

Все заметные изменения проекта. Начиная с версий после 0.3.3 файл ведётся автоматически
[python-semantic-release](https://python-semantic-release.readthedocs.io/) по сообщениям коммитов
в формате [Conventional Commits](https://www.conventionalcommits.org/ru/) — см. [CONTRIBUTING.md](CONTRIBUTING.md).

<!-- version list -->

## v0.4.0 (2026-11-18)

### Bug Fixes

- Deepcopy кубика с некопируемой стратегией поднимает DiceCopyError
  ([`8231ec6`](https://github.com/Cewerty/dicing/commit/8231ec6352e3c160bc3ef69657555a01a252208d))

- Контекстные менеджеры сохраняют незаданные стратегии исходного кубика
  ([`352439d`](https://github.com/Cewerty/dicing/commit/352439dadce6bf75f7ff023c2a24e14e8cf9309a))

### Features

- Командная строка dicing
  ([`77f3306`](https://github.com/Cewerty/dicing/commit/77f3306e0cf3bf5abac3022ac2887b21e5290ec2))

- Переработано ядро: roll() всегда возвращает int, ленивый парсер, SeededRandomStrategy
  ([`31d9a91`](https://github.com/Cewerty/dicing/commit/31d9a91f2c7b09c87a73b84d95d5a04466dd48be))


## v0.3.3 (2025-11-06)

Последнее состояние до автоматизации релизов: история до этой версии велась без единого формата
коммитов и в changelog не переносится. Подробности — в `git log v0.3.3`.
