"""Консольный цикл и вызовы операций базы данных."""

import os

import prompt
from prettytable import PrettyTable

from primitive_db import core
from primitive_db.constants import META_FILE
from primitive_db.decorators import create_cacher, handle_db_errors
from primitive_db.parser import parse_command
from primitive_db.utils import (
    load_metadata,
    load_table_data,
    save_metadata,
    save_table_data,
    table_path,
)


def print_help():
    """Показать поддерживаемые команды."""
    print("""create_table <таблица> <столбец:тип> ...
list_tables
drop_table <таблица>
insert into <таблица> values ("строка", 28, true)
select from <таблица> [where <столбец> = <значение>]
update <таблица> set <столбец> = <значение> where <столбец> = <значение>
delete from <таблица> where <столбец> = <значение>
info <таблица>
help
exit""")


@handle_db_errors
def execute(command, cache):
    """Выполнить одну команду; False означает выход."""
    operation, args = parse_command(command)
    if operation == "exit":
        return False
    if operation == "empty":
        return True
    if operation == "help":
        print_help()
        return True
    metadata = load_metadata(META_FILE)
    if operation == "list_tables":
        print("\n".join(f"- {name}" for name in sorted(metadata)) or "Таблиц нет")
        return True
    name = args["table"]
    if operation == "create_table":
        result = core.create_table(metadata, name, args["columns"])
        if result is not None:
            save_table_data(name, [])
            save_metadata(META_FILE, result)
            cache.clear()
            columns = ", ".join(f"{key}:{kind}" for key, kind in result[name].items())
            print(f'Таблица "{name}" успешно создана со столбцами: {columns}')
        return True
    if name not in metadata:
        raise KeyError(name)
    if operation == "drop_table":
        result = core.drop_table(metadata, name)
        if result is not None:
            save_metadata(META_FILE, result)
            if os.path.exists(table_path(name)):
                os.remove(table_path(name))
            cache.clear()
            print(f'Таблица "{name}" успешно удалена.')
        return True
    data = load_table_data(name)
    schema = metadata[name]
    where = args.get("where")
    if where:
        core.validate_fields(schema, where)
    if operation == "info":
        print(f"Таблица: {name}")
        print("Столбцы: " + ", ".join(f"{key}:{kind}" for key, kind in schema.items()))
        print(f"Количество записей: {len(data)}")
    elif operation == "select":
        # Содержимое файла в ключе защищает от изменений другим процессом.
        version = tuple(tuple(row.items()) for row in data)
        key = (name, version, tuple((where or {}).items()))
        result = cache(key, lambda: core.select(data, where))
        if result is not None:
            table = PrettyTable(list(schema))
            for row in result:
                table.add_row([row[column] for column in schema])
            print(table)
    else:
        if operation == "insert":
            result = core.insert(metadata, name, args["values"])
        elif operation == "update":
            core.validate_fields(schema, args["changes"], allow_id=False)
            result = core.update(data, args["changes"], where)
        else:
            result = core.delete(data, where)
        if result is not None:
            save_table_data(name, result)
            cache.clear()
            if operation == "insert":
                print(f'Запись с ID={result[-1]["ID"]} добавлена в "{name}".')
            else:
                count = sum(core.matches(row, where) for row in data)
                print(f"Операция {operation} выполнена. Записей: {count}")
    return True


def run():
    """Читать команды до exit или завершения стандартного ввода."""
    print("Примитивная база данных. help — справка, exit — выход.")
    cache = create_cacher()
    while True:
        try:
            command = prompt.string("Введите команду: ")
            if execute(command, cache) is False:
                break
        except (EOFError, KeyboardInterrupt):
            print("\nВыход.")
            break
