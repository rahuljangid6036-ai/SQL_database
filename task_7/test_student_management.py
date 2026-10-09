import sqlite3
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from course import Course
from database import Database
from main import run_application
from student import Student


class CourseTransferTransactionTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.temp_directory.name) / "students.db")
        self.database.connect()
        self.database.create_table()
        for course in (Course(1, "BCA"), Course(2, "BBA"), Course(3, "MCA")):
            self.database.add_course(course)
        self.database.add_student(Student(5, "Rahul", 20, 1, 82))

    def tearDown(self):
        self.database.close()
        self.temp_directory.cleanup()

    def test_successful_transfer_updates_student_and_writes_joined_history(self):
        self.database.transfer_student_course(5, 3)
        self.assertEqual(self.database.get_student_by_id(5).course_id, 3)

        history = self.database.get_course_history()
        self.assertEqual(len(history), 1)
        record = history[0]
        self.assertEqual(record[:5], (1, 5, "Rahul", "BCA", "MCA"))
        self.assertTrue(record[5])
        self.assertEqual(self.database.get_student_course_history(5), history)

    def test_invalid_student_course_and_same_course_leave_data_unchanged(self):
        attempts = (
            (999, 3, "Student not found."),
            (5, 99, "Invalid course ID."),
            (5, 1, "already enrolled"),
        )
        for student_id, new_course_id, message in attempts:
            with self.subTest(student_id=student_id, new_course_id=new_course_id):
                with self.assertRaisesRegex(ValueError, message):
                    self.database.transfer_student_course(student_id, new_course_id)
                self.assertEqual(self.database.get_student_by_id(5).course_id, 1)
                self.assertEqual(self.database.get_course_history(), [])
                self.assertFalse(self.database.connection.in_transaction)

    def test_history_insert_failure_rolls_back_student_update(self):
        self.database.connection.execute(
            """
            CREATE TRIGGER reject_transfer_history
            BEFORE INSERT ON student_course_history
            BEGIN
                SELECT RAISE(ABORT, 'simulated history insert failure');
            END
            """
        )
        self.database.connection.commit()

        with self.assertRaisesRegex(
            sqlite3.IntegrityError, "simulated history insert failure"
        ):
            self.database.transfer_student_course(5, 3)

        self.assertEqual(self.database.get_student_by_id(5).course_id, 1)
        self.assertEqual(self.database.get_course_history(), [])
        self.assertFalse(self.database.connection.in_transaction)

    def test_update_student_logs_course_change_atomically(self):
        self.database.update_student(Student(5, "Rahul Kumar", 21, 3, 85))
        student = self.database.get_student_by_id(5)
        self.assertEqual((student.name, student.age, student.course_id, student.marks),
                         ("Rahul Kumar", 21, 3, 85.0))
        self.assertEqual(self.database.get_course_history()[0][3:5], ("BCA", "MCA"))

    def test_public_transaction_controls_commit_and_rollback(self):
        self.database.begin_transaction()
        self.database.connection.execute(
            "UPDATE students SET marks = 90 WHERE student_id = 5"
        )
        self.database.rollback()
        self.assertEqual(self.database.get_student_by_id(5).marks, 82.0)

        self.database.begin_transaction()
        self.database.connection.execute(
            "UPDATE students SET marks = 90 WHERE student_id = 5"
        )
        self.database.commit()
        self.assertEqual(self.database.get_student_by_id(5).marks, 90.0)

    def test_course_history_rows_keep_referenced_records(self):
        self.database.transfer_student_course(5, 3)
        with self.assertRaisesRegex(ValueError, "Cannot delete a student"):
            self.database.delete_student(5)
        with self.assertRaisesRegex(ValueError, "Cannot delete a course"):
            self.database.delete_course(1)

    def test_menu_exposes_transfer_and_history_and_runs_transfer(self):
        output = StringIO()
        with patch("builtins.input", side_effect=["15", "5", "3", "17"]), redirect_stdout(output):
            run_application(self.database)

        text = output.getvalue()
        self.assertIn("15. Transfer Student Course", text)
        self.assertIn("16. View Course Transfer History", text)
        self.assertIn("17. Exit", text)
        self.assertIn("Student course transferred successfully.", text)
        self.assertEqual(self.database.get_student_by_id(5).course_id, 3)
        self.assertEqual(len(self.database.get_course_history()), 1)


class RelationalDatabaseCompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.temp_directory.name) / "students.db")
        self.database.connect()
        self.database.create_table()
        self.database.add_course(Course(1, "BCA"))
        self.database.add_course(Course(2, "MCA"))
        self.database.add_student(Student(1, "Rahul", 20, 1, 82))

    def tearDown(self):
        self.database.close()
        self.temp_directory.cleanup()

    def test_repeated_schema_setup_preserves_existing_data(self):
        self.database.create_table()
        self.assertEqual(self.database.get_student_by_id(1).name, "Rahul")
        self.assertEqual(len(self.database.get_all_courses()), 2)
        self.assertEqual(self.database.get_course_history(), [])

    def test_course_join_analytics_and_student_filters_remain_available(self):
        self.assertEqual(self.database.get_students_with_courses()[0][2], "BCA")
        self.assertEqual(self.database.get_students_by_course("BCA")[0].name, "Rahul")
        self.assertEqual(self.database.get_students_by_marks(80)[0].name, "Rahul")
        self.assertEqual(self.database.get_top_students(1)[0].name, "Rahul")
        self.assertEqual(self.database.get_course_statistics()[1][0:2], ("MCA", 0))
        self.assertEqual(self.database.get_courses_without_students(), [(2, "MCA")])
        self.assertEqual(self.database.get_total_students(), 1)

    def test_transfer_rejects_non_integer_identifiers_before_transaction(self):
        for student_id, course_id in ((True, 2), (1, False)):
            with self.subTest(student_id=student_id, course_id=course_id):
                with self.assertRaises(ValueError):
                    self.database.transfer_student_course(student_id, course_id)
                self.assertFalse(self.database.connection.in_transaction)
                self.assertEqual(self.database.get_student_by_id(1).course_id, 1)


if __name__ == "__main__":
    unittest.main()
