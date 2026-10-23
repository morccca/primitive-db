"""Полный цикл CLI, сохранение и ошибки парсинга."""

import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from primitive_db import core
from primitive_db.decorators import create_cacher
from primitive_db.parser import parse_command


class DatabaseTests(unittest.TestCase):
    def run_cli(self, directory, commands):
        env = {**os.environ, "PRIMITIVE_DB_DIR": directory}
        result = subprocess.run(
            [sys.executable, "-m", "primitive_db.main"],
            input=commands,
            text=True,
            capture_output=True,
            env=env,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def test_full_cycle_and_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            output = self.run_cli(
                directory,
                "\n".join(
                    [
                        "create_table users name:str age:int active:bool",
                        'insert into users values ("Anna, Maria", 28, false)',
                        "select from users where age = 28",
                        'update users set age=29 where name="Anna, Maria"',
                        "select from users where age=29",
                        "exit",
                        "",
                    ]
                ),
            )
            self.assertIn("Anna, Maria", output)
            path = os.path.join(directory, "data", "users.json")
            with open(path) as file:
                self.assertEqual(
                    json.load(file),
                    [{"ID": 1, "name": "Anna, Maria", "age": 29, "active": False}],
                )
            output = self.run_cli(directory, "select from users\nexit\n")
            self.assertIn("Anna, Maria", output)
            self.run_cli(directory, "delete from users where ID=1\nn\nexit\n")
            with open(path) as file:
                self.assertEqual(len(json.load(file)), 1)
            self.run_cli(
                directory,
                "delete from users where ID=1\ny\ndrop_table users\ny\nexit\n",
            )
            self.assertFalse(os.path.exists(path))

    def test_id_after_delete_and_invalid_type(self):
        with tempfile.TemporaryDirectory() as directory:
            self.run_cli(
                directory,
                "\n".join(
                    [
                        "create_table t age:int",
                        "insert into t values (10)",
                        "insert into t values (20)",
                        "insert into t values (30)",
                        "delete from t where ID=2",
                        "y",
                        "insert into t values (40)",
                        "insert into t values (true)",
                        'update t set age="bad" where ID=1',
                        "exit",
                        "",
                    ]
                ),
            )
            with open(os.path.join(directory, "data", "t.json")) as file:
                data = json.load(file)
            self.assertEqual([row["ID"] for row in data], [1, 3, 4])
            self.assertEqual(data[0]["age"], 10)

    def test_quoted_values_and_invalid_commands(self):
        _, args = parse_command('insert into t values ("a,b = (c)", false, -2)')
        self.assertEqual(args["values"], ["a,b = (c)", False, -2])
        for command in [
            "delete from t",
            "select from t where",
            "insert into t values (1,)",
            "update t set age=3",
            "nonsense",
        ]:
            with self.assertRaises(ValueError, msg=command):
                parse_command(command)

    def test_cache_clears(self):
        cache = create_cacher()
        self.assertEqual(cache("a", lambda: 1), 1)
        self.assertEqual(cache("a", lambda: 2), 1)
        cache.clear()
        self.assertEqual(cache("a", lambda: 2), 2)

    def test_validation_and_cancel(self):
        with redirect_stdout(io.StringIO()):
            self.assertIsNone(core.create_table({}, "../escape", ["x:int"]))
            self.assertIsNone(core.create_table({}, "t", ["x:float"]))
            schema = {"t": {"ID": "int"}}
            with patch("builtins.input", return_value="n"):
                self.assertIsNone(core.drop_table(schema, "t"))
            self.assertIn("t", schema)


if __name__ == "__main__":
    unittest.main()
