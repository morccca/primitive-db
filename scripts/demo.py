"""Полный сценарий БД во временной папке, без изменения рабочих данных."""

import os
import tempfile
from unittest.mock import patch


def main():
    with tempfile.TemporaryDirectory() as directory:
        os.environ["PRIMITIVE_DB_DIR"] = directory
        from primitive_db.decorators import create_cacher
        from primitive_db.engine import execute

        cache = create_cacher()
        print("Демонстрация на временной базе. Команды выполняются программой.")
        commands = [
            "create_table users name:str age:int active:bool",
            "list_tables",
            'insert into users values ("Anna Maria", 28, true)',
            "select from users",
            'update users set age=29 where name="Anna Maria"',
            "select from users where age=29",
            "info users",
            'insert into users values ("Wrong", "not an integer", true)',
            "delete from users where ID=1",
            "select from users",
            "drop_table users",
            "list_tables",
        ]

        def confirm(message):
            print(message + "y")
            return "y"

        for command in commands:
            print("\n> " + command, flush=True)
            with patch("builtins.input", side_effect=confirm):
                execute(command, cache)


if __name__ == "__main__":
    main()
