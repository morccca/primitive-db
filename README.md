# Примитивная база данных

Консольная база данных с хранением в JSON. Поддерживает таблицы,
добавление, выборку, изменение и удаление записей.

## Запуск

Python 3.12+, uv.

```bash
uv sync
uv run database
```

Также работает `uv run project`.

## Пример

```text
create_table users name:str age:int active:bool
insert into users values ("Anna", 28, true)
select from users
update users set age=29 where name="Anna"
info users
delete from users where ID=1
y
drop_table users
y
exit
```

Типы столбцов: `int`, `str`, `bool`. ID создаётся автоматически.
Строки нужно заключать в кавычки. `where` поддерживает одно равенство.
Удаление требует подтверждения. `help` выводит список команд.

Схемы сохраняются в `db_meta.json`, записи — в `data/`.
Папку можно изменить через `PRIMITIVE_DB_DIR`.
Ошибки обрабатываются декоратором, повторные выборки кэшируются.
После изменения таблицы кэш очищается.

## Проверка

```bash
uv run ruff check .
uv run python -m unittest discover -s tests
uv build
```

[Демонстрация](docs/demo.cast)

Запустить сценарий: `uv run python scripts/demo.py`.
Посмотреть запись: `uvx asciinema play docs/demo.cast`.
Демо использует временную базу.
