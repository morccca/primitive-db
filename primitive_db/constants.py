"""Настройки локального хранилища."""

import os

DATA_DIR = os.environ.get("PRIMITIVE_DB_DIR", ".")
META_FILE = os.path.join(DATA_DIR, "db_meta.json")
TABLES_DIR = os.path.join(DATA_DIR, "data")
VALID_TYPES = {"int": int, "str": str, "bool": bool}
