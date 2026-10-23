# Примитивная база данных

Консольная база данных с таблицами и хранением записей в JSON.
Требуется Python 3.12+.

## Запуск

```bash
python3 -m pip install -r requirements.txt
python3 main.py
```

`main.py` — запуск, `commands.py` — разбор и выполнение команд,
`database.py` — операции с таблицами и сохранение JSON,
`decorators.py` — обработка ошибок, подтверждение удаления и кэш.

## Ввод и вывод

Введите команды:

```text
create_table users name:str age:int
insert into users values ("Anna", 28)
select from users
```

Результат выборки:

```text
+----+------+-----+
| ID | name | age |
+----+------+-----+
| 1  | Anna |  28 |
+----+------+-----+
```

Изменение и удаление:

```text
update users set age=29 where ID=1
delete from users where ID=1
y
drop_table users
y
exit
```

Типы: `int`, `str`, `bool`. Строки — в кавычках, `ID` создаётся сам.
Удаление требует подтверждения `y`. Справка: `help`.
Также доступны `list_tables` и `info users`.
Схемы хранятся в `db_meta.json`, записи — в `data/`.
Другой каталог данных задаётся переменной `PRIMITIVE_DB_DIR`.
