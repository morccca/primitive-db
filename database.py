import json
import os

from decorators import confirm_action, handle_db_errors, log_time


DATA_DIR = os.environ.get("PRIMITIVE_DB_DIR", ".")
META_FILE = os.path.join(DATA_DIR, "db_meta.json")
TABLES_DIR = os.path.join(DATA_DIR, "data")
VALID_TYPES = {"int": int, "str": str, "bool": bool}


def validate_name(name):
    """Запретить пустые имена и пути вместо имени таблицы."""
    if not isinstance(name, str) or not name.isidentifier():
        raise ValueError(f"Некорректное имя: {name}")
    return name


def load_metadata(filepath):
    """Прочитать схему; отсутствие файла означает пустую базу."""
    try:
        with open(filepath, encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}


def save_metadata(filepath, data):
    """Заменить файл только после успешной записи нового JSON."""
    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
    temporary = filepath + ".tmp"
    try:
        with open(temporary, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
        os.replace(temporary, filepath)
    finally:
        if os.path.exists(temporary):
            os.remove(temporary)


def table_path(table_name):
    """Получить путь к файлу таблицы."""
    return os.path.join(TABLES_DIR, validate_name(table_name) + ".json")


def load_table_data(table_name):
    """Загрузить строки таблицы."""
    try:
        with open(table_path(table_name), encoding="utf-8") as file:
            data = json.load(file)
        if not isinstance(data, list):
            raise ValueError("Файл таблицы должен содержать список записей")
        return data
    except FileNotFoundError:
        return []


def save_table_data(table_name, data):
    """Сохранить строки таблицы."""
    save_metadata(table_path(table_name), data)


@handle_db_errors
def create_table(metadata, table_name, columns):
    """Добавить таблицу с обязательным авто-ID."""
    validate_name(table_name)
    if table_name in metadata:
        raise ValueError(f'Таблица "{table_name}" уже существует')
    schema = {"ID": "int"}
    for column in columns:
        if column.count(":") != 1:
            raise ValueError("Столбец задаётся как имя:тип")
        name, kind = column.split(":")
        validate_name(name)
        if name in schema or kind not in VALID_TYPES:
            raise ValueError(f"Повторное имя или неизвестный тип: {column}")
        schema[name] = kind
    metadata[table_name] = schema
    return metadata


@handle_db_errors
@confirm_action("удаление таблицы")
def drop_table(metadata, table_name):
    """Удалить схему таблицы после подтверждения."""
    del metadata[table_name]
    return metadata


def validate_fields(schema, values, allow_id=True):
    """Проверить имена и точные типы, не считая bool целым числом."""
    for name, value in values.items():
        if name not in schema:
            raise KeyError(name)
        if not allow_id and name == "ID":
            raise ValueError("ID назначается автоматически и не изменяется")
        if type(value) is not VALID_TYPES[schema[name]]:
            raise ValueError(f"Столбец {name} ожидает {schema[name]}")


@handle_db_errors
@log_time
def insert(metadata, table_name, values):
    """Проверить запись и добавить её к данным таблицы."""
    schema = metadata[table_name]
    names = [name for name in schema if name != "ID"]
    if len(values) != len(names):
        raise ValueError(f"Ожидается {len(names)} значений без ID")
    record = dict(zip(names, values))
    validate_fields(schema, record, allow_id=False)
    data = load_table_data(table_name)
    record = {"ID": max((row["ID"] for row in data), default=0) + 1, **record}
    return data + [record]


def matches(row, where_clause):
    """Проверить совпадение строки с условием."""
    return all(row[key] == value for key, value in (where_clause or {}).items())


@handle_db_errors
@log_time
def select(table_data, where_clause=None):
    """Вернуть независимые копии выбранных записей."""
    return [row.copy() for row in table_data if matches(row, where_clause)]


@handle_db_errors
def update(table_data, set_clause, where_clause):
    """Обновить совпавшие записи без изменения входного списка."""
    return [
        dict(row, **set_clause) if matches(row, where_clause) else row.copy()
        for row in table_data
    ]


@handle_db_errors
@confirm_action("удаление записей")
def delete(table_data, where_clause):
    """Удалить подходящие записи после подтверждения."""
    return [row.copy() for row in table_data if not matches(row, where_clause)]
