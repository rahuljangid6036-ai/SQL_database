import sqlite3
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from course import Course
from database import Database
from main import run_application, transfer_student_course
from student import Student


class CourseTransferTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        db_path = Path(self.temp_directory.name) / "test_students.db"
        self.database = Database(db_path)
        self.database.connect()
        self.database.create_table()
        for course in (Course(1, "BCA"), Course(2, "BBA"), Course(3, "MCA")):
            self.database.add_course(course)
        self.database.add_student(Student(5, "Rahul", 20, 1, 82))

    def tearDown(self):
        self.database.close()
        self.temp_directory.cleanup()

    def test_successful_transfer_updates_student_and_commits_history(self):
        history_id = self.database.transfer_student_course(5, 3)

        student = self.database.get_student_by_id(5)
        history = self.database.get_student_course_history(5)
        self.assertEqual(student.course_id, 3)
        self.assertEqual(student.course_name, "MCA")
        self.assertEqual(history[0][:5], (history_id, 5, "Rahul", "BCA", "MCA"))
        self.assertIsNotNone(history[0][5])
        self.assertEqual(self.database.get_course_history(), history)
        self.assertFalse(self.database.connection.in_transaction)

    def test_invalid_student_does_not_start_transaction_or_write_history(self):
        with self.assertRaisesRegex(ValueError, "Student not found"):
            self.database.transfer_student_course(999, 3)

        self.assertFalse(self.database.connection.in_transaction)
        self.assertEqual(self.database.get_course_history(), [])
        self.assertEqual(self.database.get_student_by_id(5).course_id, 1)

    def test_invalid_course_does_not_change_student_or_history(self):
        with self.assertRaisesRegex(ValueError, "Invalid course ID"):
            self.database.transfer_student_course(5, 99)

        self.assertFalse(self.database.connection.in_transaction)
        self.assertEqual(self.database.get_student_by_id(5).course_id, 1)
        self.assertEqual(self.database.get_course_history(), [])

    def test_same_course_is_rejected_without_changes(self):
        with self.assertRaisesRegex(ValueError, "already enrolled"):
            self.database.transfer_student_course(5, 1)

        self.assertEqual(self.database.get_student_by_id(5).course_id, 1)
        self.assertEqual(self.database.get_course_history(), [])

    def test_history_insert_failure_rolls_back_student_update(self):
        self.database.connection.execute(
            """
            CREATE TRIGGER fail_history_insert
            BEFORE INSERT ON student_course_history
            BEGIN
                SELECT RAISE(ABORT, 'simulated history insert failure');
            END
            """
        )

        with self.assertRaisesRegex(sqlite3.IntegrityError, "simulated history insert failure"):
            self.database.transfer_student_course(5, 3)

        self.assertEqual(self.database.get_student_by_id(5).course_id, 1)
        self.assertEqual(self.database.get_student_course_history(5), [])
        self.assertFalse(self.database.connection.in_transaction)

    def test_explicit_begin_commit_and_rollback(self):
        self.database.begin_transaction()
        self.database.connection.execute("UPDATE students SET marks = ? WHERE student_id = ?", (90, 5))
        self.database.rollback()
        self.assertEqual(self.database.get_student_by_id(5).marks, 82)

        self.database.begin_transaction()
        self.database.connection.execute("UPDATE students SET marks = ? WHERE student_id = ?", (90, 5))
        self.database.commit()
        self.assertEqual(self.database.get_student_by_id(5).marks, 90)

    def test_course_change_cannot_bypass_transfer_history(self):
        with self.assertRaisesRegex(ValueError, "Use transfer_student_course"):
            self.database.update_student(Student(5, "Rahul", 20, 3, 82))
        self.assertEqual(self.database.get_student_by_id(5).course_id, 1)
        self.assertEqual(self.database.get_course_history(), [])

    def test_menu_transfer_reports_success_and_menu_has_history_actions(self):
        output = StringIO()
        with patch("builtins.input", side_effect=["5", "3"]), redirect_stdout(output):
            transfer_student_course(self.database)
        self.assertIn("Course transfer completed and committed.", output.getvalue())
        self.assertEqual(self.database.get_student_by_id(5).course_name, "MCA")

        output = StringIO()
        with patch("builtins.input", return_value="17"), redirect_stdout(output):
            run_application(self.database)
        for option in (
            "15. Transfer Student Course",
            "16. View Course Transfer History",
            "17. Exit",
        ):
            self.assertIn(option, output.getvalue())

    def test_all_previous_task_six_operations_remain_available(self):
        self.assertEqual(len(self.database.get_all_courses()), 3)
        self.assertEqual(self.database.get_course_by_id(1).course_name, "BCA")
        self.database.add_student(Student(6, "Priya", 21, 1, 88))
        self.assertEqual(len(self.database.get_all_students()), 2)
        self.assertEqual(self.database.get_student_by_id(6).name, "Priya")
        self.assertEqual(len(self.database.get_students_by_course("BCA")), 2)
        self.assertEqual(len(self.database.get_students_by_marks(80)), 2)
        self.assertEqual(self.database.get_total_students(), 2)
        self.assertEqual(self.database.get_total_marks(), 170.0)
        self.assertEqual(self.database.delete_student(6), 1)
        self.assertEqual(self.database.delete_course(2), 1)


class HistorySchemaTests(unittest.TestCase):
    def test_task_six_database_gets_history_table_without_losing_data(self):
        with tempfile.TemporaryDirectory() as temp_directory:
            db_path = Path(temp_directory) / "task_six_students.db"
            database = Database(db_path)
            try:
                database.connect()
                database.create_table()
                database.add_course(Course(1, "BCA"))
                database.add_student(Student(1, "Rahul", 20, 1, 82))
                database.close()

                database.connect()
                database.create_table()
                self.assertEqual(database.get_student_by_id(1).name, "Rahul")
                self.assertEqual(database.get_course_history(), [])
            finally:
                database.close()


if __name__ == "__main__":
    unittest.main()