import sqlite3
import tempfile
import unittest
from pathlib import Path

from database import Database
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

        self.database.add_student(Student(2, "Amit", 20, "BBA", 76))
        self.assertEqual(len(self.database.get_all_students()), 2)

    def test_database_enforces_primary_key_not_null_and_check_constraints(self):
        invalid_rows = [
            (1, None, 20, "BCA", 82),
            (1, "Rahul", None, "BCA", 82),
            (1, "Rahul", 20, None, 82),
            (1, "Rahul", 20, "BCA", None),
            (1, "Rahul", -5, "BCA", 82),
            (1, "Rahul", 20, "BCA", 150),
        ]
        insert_sql = "INSERT INTO students VALUES (?, ?, ?, ?, ?)"

        for row in invalid_rows:
            with self.subTest(row=row), self.assertRaises(sqlite3.IntegrityError):
                self.database.connection.execute(insert_sql, row)
                self.database.connection.rollback()

        self.database.connection.execute(insert_sql, (1, "Rahul", 20, "BCA", 82))
        with self.assertRaises(sqlite3.IntegrityError):
            self.database.connection.execute(insert_sql, (1, "Priya", 21, "BCA", 88))
        self.database.connection.rollback()


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
                with self.assertRaises(sqlite3.IntegrityError):
                    database.connection.execute(
                        "INSERT INTO students VALUES (?, ?, ?, ?, ?)",
                        (1, "Priya", 21, "BCA", 88),
                    )
            finally:
                database.close()


if __name__ == "__main__":
    unittest.main()
