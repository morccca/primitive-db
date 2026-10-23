"""Разбор ограниченного SQL-подобного синтаксиса без eval."""

import shlex


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
