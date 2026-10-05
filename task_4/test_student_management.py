import sqlite3
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from database import Database
from main import delete_student, filter_students_by_marks, run_application, show_top_students
from student import Student


class StudentValidationTests(unittest.TestCase):
    def test_rejects_empty_course(self):
        with self.assertRaisesRegex(ValueError, "Course cannot be empty"):
            Student(1, "Rahul", 20, "  ", 82)

    def test_rejects_marks_above_100(self):
        with self.assertRaisesRegex(ValueError, "Marks must be between 0 and 100"):
            Student(1, "Rahul", 20, "BCA", 150)


class StudentDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        db_path = Path(self.temp_directory.name) / "test_students.db"
        self.database = Database(db_path)
        self.database.connect()
        self.database.create_table()
        self.database.add_student(Student(1, "Riya Sharma", 20, "BCA", 92))
        self.database.add_student(Student(2, "Karan Patel", 21, "BBA", 75))
        self.database.add_student(Student(3, "Priya Singh", 19, "BCA", 84))
        self.database.add_student(Student(4, "Amit Kumar", 22, "BBA", 60))

    def tearDown(self):
        self.database.close()
        self.temp_directory.cleanup()

    def test_existing_crud_remains_available(self):
        self.assertEqual(len(self.database.get_all_students()), 4)
        self.assertEqual(self.database.get_student_by_id(1).name, "Riya Sharma")
        self.assertEqual(self.database.update_student(Student(4, "Amit Kumar", 22, "BBA", 65)), 1)
        self.assertEqual(self.database.get_student_by_id(4).marks, 65)
        self.assertEqual(self.database.delete_student(4), 1)
        self.assertIsNone(self.database.get_student_by_id(4))

    def test_course_filter(self):
        students = self.database.get_students_by_course("BCA")
        self.assertEqual({student.course for student in students}, {"BCA"})
        self.assertEqual(len(students), 2)

    def test_minimum_marks_filter(self):
        students = self.database.get_students_by_marks(80)
        self.assertTrue(students)
        self.assertTrue(all(student.marks >= 80 for student in students))

    def test_rejects_invalid_minimum_marks(self):
        with self.assertRaisesRegex(ValueError, "Invalid marks"):
            self.database.get_students_by_marks(150)

    def test_partial_name_search(self):
        students = self.database.search_students_by_name("ri")
        self.assertEqual({student.name for student in students}, {"Riya Sharma", "Priya Singh"})

    def test_and_condition(self):
        students = self.database.get_students_by_course_and_min_marks("BCA", 90)
        self.assertEqual([student.name for student in students], ["Riya Sharma"])

    def test_or_condition(self):
        students = self.database.get_students_by_courses("BCA", "BBA")
        self.assertEqual(len(students), 4)

    def test_marks_sort_both_directions(self):
        descending = [student.marks for student in self.database.get_students_sorted_by_marks()]
        ascending = [student.marks for student in self.database.get_students_sorted_by_marks(desc=False)]
        self.assertEqual(descending, [92, 84, 75, 60])
        self.assertEqual(ascending, [60, 75, 84, 92])

    def test_top_students_uses_limit_and_orders_highest_first(self):
        students = self.database.get_top_students(3)
        self.assertEqual(len(students), 3)
        self.assertEqual([student.marks for student in students], [92, 84, 75])

    def test_rejects_non_positive_top_count(self):
        for limit in (0, -5):
            with self.subTest(limit=limit), self.assertRaisesRegex(
                ValueError, "Number of students must be greater than 0"
            ):
                self.database.get_top_students(limit)

    def test_marks_menu_reports_invalid_minimum(self):
        with patch("builtins.input", return_value="150"):
            with self.assertRaisesRegex(ValueError, "Invalid marks"):
                filter_students_by_marks(self.database)

    def test_top_menu_reports_invalid_count(self):
        with patch("builtins.input", return_value="-5"):
            with self.assertRaisesRegex(ValueError, "Number of students must be greater than 0"):
                show_top_students(self.database)

    def test_delete_confirmation_cancel_keeps_record(self):
        with patch("builtins.input", side_effect=["1", "n"]):
            delete_student(self.database)
        self.assertIsNotNone(self.database.get_student_by_id(1))

    def test_menu_lists_all_required_options(self):
        output = StringIO()
        with patch("builtins.input", return_value="11"), redirect_stdout(output):
            run_application(self.database)
        menu = output.getvalue()
        for option in (
            "3. Search Student by ID",
            "4. Search Student by Course",
            "5. Search Student by Name",
            "6. Filter Students by Marks",
            "7. Sort Students by Marks",
            "8. Top N Students",
            "9. Update Student",
            "10. Delete Student",
            "11. Exit",
        ):
            self.assertIn(option, menu)

    def test_database_enforces_marks_constraint(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.database.connection.execute(
                "INSERT INTO students VALUES (?, ?, ?, ?, ?)",
                (5, "Test Student", 20, "BCA", 150),
            )
        self.database.connection.rollback()


class StudentDatabaseMigrationTests(unittest.TestCase):
    def test_migrates_legacy_table_and_preserves_records(self):
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