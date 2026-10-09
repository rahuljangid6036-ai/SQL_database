import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from config import ConfigurationError, get_database_config
from course import Course
from database import Database, DatabaseDependencyError
from main import run_application
from student import Student


class FakeCursor:
    def __init__(self, rows=(), rowcount=1):
        self.rows = list(rows)
        self.rowcount = rowcount
        self.closed = False

    def fetchone(self):
        return self.rows.pop(0) if self.rows else None

    def fetchall(self):
        rows, self.rows = self.rows, []
        return rows

    def close(self):
        self.closed = True


class FakeConnection:
    def __init__(self):
        self.calls = []
        self.course_id = 1
        self.student_exists = True
        self.history = []
        self.transaction_snapshot = None
        self.fail_history_insert = False
        self.closed = False

    def execute(self, query, parameters=()):
        normalized = " ".join(query.split())
        self.calls.append((normalized, parameters))
        if normalized == "BEGIN":
            self.transaction_snapshot = (self.course_id, list(self.history))
        elif normalized.startswith("SELECT course_id FROM students"):
            return FakeCursor([(self.course_id,)] if self.student_exists else [])
        elif normalized.startswith("SELECT 1 FROM courses"):
            return FakeCursor([(1,)] if parameters[0] in (1, 3) else [])
        elif normalized.startswith("UPDATE students SET course_id"):
            self.course_id = parameters[0]
            return FakeCursor(rowcount=1)
        elif normalized.startswith("INSERT INTO student_course_history"):
            if self.fail_history_insert:
                raise RuntimeError("simulated history insert failure")
            self.history.append(parameters)
        elif normalized == "COMMIT":
            self.transaction_snapshot = None
        elif normalized == "ROLLBACK":
            if self.transaction_snapshot is not None:
                self.course_id, self.history = self.transaction_snapshot
                self.transaction_snapshot = None
        return FakeCursor()

    def commit(self):
        return None

    def rollback(self):
        return None

    def close(self):
        self.closed = True


class PostgreSQLLayerTests(unittest.TestCase):
    def setUp(self):
        self.database = Database({"host": "localhost", "port": 5432, "dbname": "test"})
        self.database.connection = FakeConnection()

    def test_query_helpers_use_separate_parameters_and_close_cursors(self):
        cursor = FakeCursor([(1,)])
        calls = []

        def execute(query, parameters=()):
            calls.append((query, parameters))
            return cursor

        self.database.connection.execute = execute
        self.assertEqual(self.database.fetch_one("SELECT %s", ("safe value",)), (1,))
        self.assertEqual(calls, [("SELECT %s", ("safe value",))])
        self.assertTrue(cursor.closed)

    def test_create_tables_use_postgresql_types_and_relations(self):
        self.database.create_tables()
        statements = [
            statement
            for statement, _ in self.database.connection.calls
            if statement.startswith("CREATE TABLE")
        ]
        self.assertIn("course_id SERIAL PRIMARY KEY", statements[0])
        self.assertIn("marks NUMERIC(5, 2)", statements[1])
        self.assertIn("history_id SERIAL PRIMARY KEY", statements[2])
        self.assertIn("REFERENCES courses(course_id)", statements[1])
        self.assertIn("REFERENCES students(student_id)", statements[2])

    def test_transfer_commits_update_and_history_together(self):
        self.database.transfer_student_course(5, 3)
        self.assertEqual(self.database.connection.course_id, 3)
        self.assertEqual(self.database.connection.history, [(5, 1, 3)])
        update = next(
            call for call in self.database.connection.calls
            if call[0].startswith("UPDATE students SET course_id")
        )
        self.assertEqual(update[1], (3, 5))
        self.assertEqual(
            [call[0] for call in self.database.connection.calls if call[0] in ("BEGIN", "COMMIT")],
            ["BEGIN", "COMMIT"],
        )

    def test_history_insert_failure_rolls_back_update(self):
        self.database.connection.fail_history_insert = True
        with self.assertRaisesRegex(RuntimeError, "simulated history insert failure"):
            self.database.transfer_student_course(5, 3)
        self.assertEqual(self.database.connection.course_id, 1)
        self.assertEqual(self.database.connection.history, [])
        self.assertEqual(
            [call[0] for call in self.database.connection.calls if call[0] in ("BEGIN", "ROLLBACK")],
            ["BEGIN", "ROLLBACK"],
        )
        self.assertFalse(self.database._transaction_active)

    def test_invalid_transfer_inputs_rollback_without_changes(self):
        for student_id, course_id, message in (
            (999, 3, "Student not found"),
            (5, 99, "Invalid course ID"),
            (5, 1, "already enrolled"),
        ):
            with self.subTest(student_id=student_id, course_id=course_id):
                self.database.connection.student_exists = student_id == 5
                with self.assertRaisesRegex(ValueError, message):
                    self.database.transfer_student_course(student_id, course_id)
                self.assertEqual(self.database.connection.course_id, 1)
                self.assertEqual(self.database.connection.history, [])
                self.assertFalse(self.database._transaction_active)

    def test_student_and_course_validation(self):
        with self.assertRaisesRegex(ValueError, "Marks must be between 0 and 100"):
            Student(1, "Name", 20, 1, float("nan"))
        with self.assertRaisesRegex(ValueError, "Course name cannot be empty"):
            Course(None, " ")

    def test_missing_driver_reports_install_instructions(self):
        database = Database({"host": "localhost"})
        with patch("database.importlib.import_module", side_effect=ImportError):
            with self.assertRaisesRegex(DatabaseDependencyError, "pip install -r requirements.txt"):
                database.connect()

    def test_menu_displays_postgresql_crud_and_transaction_options(self):
        from contextlib import redirect_stdout
        from io import StringIO
        from unittest.mock import patch

        output = StringIO()
        with patch("builtins.input", return_value="17"), redirect_stdout(output):
            run_application(self.database)
        for option in (
            "1. Add Course",
            "3. Add Student",
            "10. Update Student",
            "11. Delete Student",
            "15. Transfer Student Course",
            "16. View Course Transfer History",
            "17. Exit",
        ):
            self.assertIn(option, output.getvalue())


class ConfigurationTests(unittest.TestCase):
    def test_config_reads_environment_and_converts_port(self):
        environment = {
            "DB_HOST": "db.example",
            "DB_PORT": "5544",
            "DB_NAME": "school",
            "DB_USER": "student_app",
            "DB_PASSWORD": "local-test-secret",
        }
        with patch.dict(os.environ, environment, clear=True), patch(
            "config.Path.with_name", return_value=Path("Z:\\missing.env")
        ):
            config = get_database_config()
        self.assertEqual(config["host"], "db.example")
        self.assertEqual(config["port"], 5544)
        self.assertEqual(config["dbname"], "school")
        self.assertEqual(config["user"], "student_app")
        self.assertEqual(config["password"], "local-test-secret")

    def test_missing_password_fails_with_actionable_message(self):
        with patch.dict(os.environ, {}, clear=True), patch(
            "config.Path.with_name", return_value=Path("Z:\\missing.env")
        ):
            with self.assertRaisesRegex(ConfigurationError, "DB_PASSWORD is required"):
                get_database_config()

    def test_env_file_does_not_override_process_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            env_path = Path(directory) / ".env"
            env_path.write_text("DB_HOST=file-host\nDB_PASSWORD=file-secret\n", encoding="utf-8")
            with patch("config.Path.with_name", return_value=env_path), patch.dict(
                os.environ, {"DB_HOST": "process-host", "DB_PASSWORD": "process-secret"}, clear=True
            ):
                config = get_database_config()
            self.assertEqual(config["host"], "process-host")
            self.assertEqual(config["password"], "process-secret")


if __name__ == "__main__":
    unittest.main()
