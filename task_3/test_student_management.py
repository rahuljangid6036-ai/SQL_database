import sqlite3
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from database import Database
from main import delete_student
from student import Student


class StudentValidationTests(unittest.TestCase):
    def test_rejects_non_integer_student_id(self):
        with self.assertRaises(ValueError):
            Student("1", "Rahul", 20, "BCA", 82)

    def test_rejects_empty_name(self):
        with self.assertRaisesRegex(ValueError, "Student name cannot be empty"):
            Student(1, "  ", 20, "BCA", 82)

    def test_rejects_non_positive_age(self):
        with self.assertRaisesRegex(ValueError, "Age"):
            Student(1, "Rahul", -5, "BCA", 82)

    def test_rejects_empty_course(self):
        with self.assertRaisesRegex(ValueError, "Course"):
            Student(1, "Rahul", 20, "", 82)

    def test_rejects_marks_above_100(self):
        with self.assertRaisesRegex(ValueError, "Marks"):
            Student(1, "Rahul", 20, "BCA", 150)


class StudentDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        db_path = Path(self.temp_directory.name) / "test_students.db"
        self.database = Database(db_path)
        self.database.connect()
        self.database.create_table()

    def tearDown(self):
        self.database.close()
        self.temp_directory.cleanup()

    def test_insert_and_retrieve_student(self):
        expected = Student(6, "Karan", 20, "BCA", 85)
        self.database.add_student(expected)

        self.assertEqual(str(self.database.get_student_by_id(6)), str(expected))
        self.assertEqual(len(self.database.get_all_students()), 1)

    def test_search_missing_student_returns_none(self):
        self.assertIsNone(self.database.get_student_by_id(999))

    def test_rejects_duplicate_student_id(self):
        self.database.add_student(Student(1, "Rahul", 20, "BCA", 82))
        with self.assertRaisesRegex(ValueError, "Student ID already exists"):
            self.database.add_student(Student(1, "Priya", 21, "BCA", 88))

    def test_update_changes_fields_but_preserves_student_id(self):
        self.database.add_student(Student(3, "Amit", 20, "BCA", 82))

        affected = self.database.update_student(Student(3, "Amit", 20, "BCA", 90))

        self.assertEqual(affected, 1)
        self.assertEqual(str(self.database.get_student_by_id(3)), "ID: 3 | Name: Amit | Age: 20 | Course: BCA | Marks: 90")

    def test_update_missing_student_returns_zero(self):
        affected = self.database.update_student(Student(100, "Amit", 20, "BCA", 90))
        self.assertEqual(affected, 0)

    def test_invalid_update_does_not_change_database(self):
        self.database.add_student(Student(3, "Amit", 20, "BCA", 82))

        with self.assertRaisesRegex(ValueError, "Marks"):
            Student(3, "Amit", 20, "BCA", 150)

        self.assertEqual(self.database.get_student_by_id(3).marks, 82)

    def test_delete_returns_rowcount_for_existing_and_missing_records(self):
        self.database.add_student(Student(6, "Karan", 20, "BCA", 85))

        self.assertEqual(self.database.delete_student(6), 1)
        self.assertEqual(self.database.delete_student(100), 0)
        self.assertIsNone(self.database.get_student_by_id(6))

    def test_database_enforces_constraints_during_update(self):
        self.database.add_student(Student(3, "Amit", 20, "BCA", 82))

        with self.assertRaises(sqlite3.IntegrityError):
            self.database.connection.execute(
                "UPDATE students SET marks = ? WHERE student_id = ?",
                (150, 3),
            )
        self.database.connection.rollback()
        self.assertEqual(self.database.get_student_by_id(3).marks, 82)

    def test_delete_confirmation_cancel_keeps_record(self):
        self.database.add_student(Student(6, "Karan", 20, "BCA", 85))
        output = StringIO()

        with patch("builtins.input", side_effect=["6", "n"]), redirect_stdout(output):
            delete_student(self.database)

        self.assertIn("Deletion cancelled.", output.getvalue())
        self.assertIsNotNone(self.database.get_student_by_id(6))

    def test_delete_confirmation_yes_removes_record(self):
        self.database.add_student(Student(6, "Karan", 20, "BCA", 85))
        output = StringIO()

        with patch("builtins.input", side_effect=["6", "yes"]), redirect_stdout(output):
            delete_student(self.database)

        self.assertIn("Student deleted successfully.", output.getvalue())
        self.assertIsNone(self.database.get_student_by_id(6))

    def test_delete_missing_student_reports_not_found(self):
        output = StringIO()

        with patch("builtins.input", return_value="100"), redirect_stdout(output):
            delete_student(self.database)

        self.assertIn("Student not found.", output.getvalue())


class StudentDatabaseMigrationTests(unittest.TestCase):
    def test_migrates_existing_task_one_table_and_preserves_records(self):
        with tempfile.TemporaryDirectory() as temp_directory:
            db_path = Path(temp_directory) / "legacy_students.db"
            connection = sqlite3.connect(db_path)
            connection.execute(
                """
                CREATE TABLE students (
                    student_id INTEGER,
                    name TEXT,
                    age INTEGER,
                    course TEXT,
                    marks REAL
                )
                """
            )
            connection.execute(
                "INSERT INTO students VALUES (?, ?, ?, ?, ?)",
                (1, "Rahul", 20, "BCA", 82),
            )
            connection.commit()
            connection.close()

            database = Database(db_path)
            try:
                database.connect()
                database.create_table()
                self.assertEqual(database.get_student_by_id(1).name, "Rahul")
            finally:
                database.close()


if __name__ == "__main__":
    unittest.main()
