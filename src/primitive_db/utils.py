"""Чтение и запись JSON-файлов."""

import json
import os

from primitive_db.constants import TABLES_DIR


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
