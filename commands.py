import os
import shlex

import prompt
from prettytable import PrettyTable

import database
from database import (
    META_FILE,
    load_metadata,
    load_table_data,
    save_metadata,
    save_table_data,
    table_path,
)
from decorators import create_cacher, handle_db_errors


def tokenize(command):
    """Разобрать строку, сохраняя кавычки для определения типа."""
    lexer = shlex.shlex(command, posix=False, punctuation_chars="(),=")
    lexer.whitespace_split = True
    lexer.commenters = ""
    tokens = []
    for token in lexer:
        if token and all(char in "(),=" for char in token):
            tokens.extend(token)
        else:
            tokens.append(token)
    return tokens


def parse_value(token):
    """Различить строку в кавычках, целое число и bool."""
    if len(token) >= 2 and token[0] in "\"'" and token[-1] == token[0]:
        return token[1:-1]
    if token.lower() in ("true", "false"):
        return token.lower() == "true"
    try:
        return int(token)
    except ValueError:
        raise ValueError(f"Некорректное значение: {token}. Строки нужны в кавычках")


def parse_assignments(tokens):
    """Разобрать column=value, column=value в словарь."""
    result = {}
    while tokens:
        if len(tokens) < 3 or tokens[1] != "=":
            raise ValueError("Ожидается столбец = значение")
        name, _, value = tokens[:3]
        if name in result:
            raise ValueError(f"Столбец {name} указан дважды")
        result[name] = parse_value(value)
        tokens = tokens[3:]
        if tokens:
            if tokens[0] != "," or len(tokens) == 1:
                raise ValueError("Ожидается запятая между присваиваниями")
            tokens = tokens[1:]
    if not result:
        raise ValueError("Условие не может быть пустым")
    return result


def parse_where(text):
    """Разобрать одно условие равенства."""
    result = parse_assignments(tokenize(text))
    if len(result) != 1:
        raise ValueError("Поддерживается одно условие where")
    return result


def parse_set(text):
    """Разобрать поля для обновления."""
    return parse_assignments(tokenize(text))


def parse_command(command):
    """Вернуть имя операции и её аргументы."""
    tokens = tokenize(command)
    if not tokens:
        return "empty", {}
    operation = tokens[0].lower()
    if operation in ("help", "exit", "list_tables") and len(tokens) == 1:
        return operation, {}
    if operation in ("drop_table", "info") and len(tokens) == 2:
        return operation, {"table": tokens[1]}
    if operation == "create_table" and len(tokens) >= 3:
        return operation, {"table": tokens[1], "columns": tokens[2:]}
    if operation == "insert" and len(tokens) >= 7:
        if tokens[1].lower() != "into" or tokens[3].lower() != "values":
            raise ValueError("Используйте insert into таблица values (...)")
        if tokens[4] != "(" or tokens[-1] != ")":
            raise ValueError("Значения должны быть в скобках")
        values = tokens[5:-1]
        if len(values) % 2 == 0 or any(x != "," for x in values[1::2]):
            raise ValueError("Значения нужно разделять запятыми")
        return operation, {
            "table": tokens[2],
            "values": [parse_value(x) for x in values[::2]],
        }
    if operation in ("select", "delete") and len(tokens) >= 3:
        if tokens[1].lower() != "from":
            raise ValueError("После команды ожидается from")
        where = None
        if len(tokens) > 3:
            if tokens[3].lower() != "where":
                raise ValueError("Ожидается where")
            where = parse_assignments(tokens[4:])
            if len(where) != 1:
                raise ValueError("Поддерживается одно условие where")
        if operation == "delete" and where is None:
            raise ValueError("Для удаления обязательно условие where")
        return operation, {"table": tokens[2], "where": where}
    if operation == "update" and len(tokens) >= 10:
        if tokens[2].lower() != "set":
            raise ValueError("Ожидается set")
        where_index = next(
            (i for i in range(3, len(tokens)) if tokens[i].lower() == "where"), None
        )
        if where_index is None:
            raise ValueError("Для обновления обязательно условие where")
        changes = parse_assignments(tokens[3:where_index])
        where = parse_assignments(tokens[where_index + 1 :])
        if len(where) != 1:
            raise ValueError("Поддерживается одно условие where")
        return operation, {"table": tokens[1], "changes": changes, "where": where}
    raise ValueError(f"Неизвестная команда или неверный синтаксис: {operation}")


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
        result = database.create_table(metadata, name, args["columns"])
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
        result = database.drop_table(metadata, name)
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
        database.validate_fields(schema, where)
    if operation == "info":
        print(f"Таблица: {name}")
        print("Столбцы: " + ", ".join(f"{key}:{kind}" for key, kind in schema.items()))
        print(f"Количество записей: {len(data)}")
    elif operation == "select":
        # Содержимое файла в ключе защищает от изменений другим процессом.
        version = tuple(tuple(row.items()) for row in data)
        key = (name, version, tuple((where or {}).items()))
        result = cache(key, lambda: database.select(data, where))
        if result is not None:
            table = PrettyTable(list(schema))
            for row in result:
                table.add_row([row[column] for column in schema])
            print(table)
    else:
        if operation == "insert":
            result = database.insert(metadata, name, args["values"])
        elif operation == "update":
            database.validate_fields(schema, args["changes"], allow_id=False)
            result = database.update(data, args["changes"], where)
        else:
            result = database.delete(data, where)
        if result is not None:
            save_table_data(name, result)
            cache.clear()
            if operation == "insert":
                print(f'Запись с ID={result[-1]["ID"]} добавлена в "{name}".')
            else:
                count = sum(database.matches(row, where) for row in data)
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
