# Примитивная база данных

Автор: Naumov Pavel. Python 3.12+, [uv](https://docs.astral.sh/uv/getting-started/installation/).

Консольная база данных: создание таблиц, добавление, выборка,
изменение и удаление записей. Данные хранятся в JSON.

## Запуск

В каталоге проекта:

```bash
uv sync
uv run database
```

Также доступна команда `uv run project`.

## Команды

```text
create_table users name:str age:int active:bool
list_tables
insert into users values ("Anna", 28, true)
select from users
update users set age=29 where name="Anna"
select from users where age=29
info users
delete from users where ID=1
y
drop_table users
y
help
exit
```

Типы: `int`, `str`, `bool`; `ID` назначается автоматически.
Строки вводятся в кавычках, `where` проверяет равенство.
Удаление требует подтверждения `y`.

Код находится в `src/primitive_db/`. Схемы сохраняются в `db_meta.json`,
записи — в `data/`. Корневой каталог данных задаёт `PRIMITIVE_DB_DIR`.
Повторные выборки кэшируются; изменения очищают кэш.

Проверка стиля: `uv run ruff check .`. Сборка пакета: `uv build`.
