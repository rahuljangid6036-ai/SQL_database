import sqlite3
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from course import Course
from database import Database
from main import add_student, run_application, show_courses_without_students
from student import Student


class RelationalDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        db_path = Path(self.temp_directory.name) / "test_students.db"
        self.database = Database(db_path)
        self.database.connect()
        self.database.create_table()
        self.courses = [
            Course(1, "BCA"),
            Course(2, "BBA"),
            Course(3, "MCA"),
            Course(4, "MBA"),
        ]
        for course in self.courses:
            self.database.add_course(course)
        records = [
            Student(1, "Rahul", 20, 1, 82),
            Student(2, "Priya", 21, 1, 88),
            Student(3, "Amit", 20, 2, 76),
            Student(4, "Neha", 22, 1, 91),
            Student(5, "Rohit", 21, 2, 69),
        ]
        for student in records:
            self.database.add_student(student)

    def tearDown(self):
        self.database.close()
        self.temp_directory.cleanup()

    def test_foreign_keys_are_enabled_and_reject_invalid_course(self):
        self.assertEqual(self.database.connection.execute("PRAGMA foreign_keys").fetchone(), (1,))
        with self.assertRaisesRegex(ValueError, "Invalid course ID"):
            self.database.add_student(Student(99, "Invalid", 20, 99, 80))
        self.assertIsNone(self.database.get_student_by_id(99))

    def test_sql_foreign_key_blocks_invalid_direct_insert(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.database.connection.execute(
                "INSERT INTO students VALUES (?, ?, ?, ?, ?)",
                (99, "Invalid", 20, 99, 80),
            )
        self.database.connection.rollback()

    def test_course_crud_and_referential_integrity(self):
        self.assertEqual([course.course_name for course in self.database.get_all_courses()],
                         ["BCA", "BBA", "MCA", "MBA"])
        self.assertEqual(self.database.get_course_by_id(1).course_name, "BCA")
        with self.assertRaisesRegex(ValueError, "Cannot delete a course that has students"):
            self.database.delete_course(1)
        self.assertEqual(self.database.delete_course(3), 1)
        self.assertIsNone(self.database.get_course_by_id(3))

    def test_course_validation_and_duplicate_name(self):
        with self.assertRaisesRegex(ValueError, "Course ID must be an integer"):
            Course(True, "Invalid")
        with self.assertRaisesRegex(ValueError, "Course name cannot be empty"):
            Course(5, "  ")
        with self.assertRaisesRegex(ValueError, "Course name already exists"):
            self.database.add_course(Course(5, "BCA"))

    def test_students_are_stored_with_course_ids_and_joined_for_display(self):
        joined_rows = self.database.get_students_with_courses()
        self.assertEqual(joined_rows[0], (1, "Rahul", "BCA", 82.0))
        students = self.database.get_all_students()
        self.assertEqual(students[0].course_id, 1)
        self.assertEqual(students[0].course_name, "BCA")
        self.assertIn("Course: BCA", str(students[0]))

    def test_selected_course_filter_uses_join(self):
        students = self.database.get_students_by_course("BCA")
        self.assertEqual([student.name for student in students], ["Rahul", "Priya", "Neha"])
        self.assertTrue(all(student.course_name == "BCA" for student in students))

    def test_course_statistics_include_courses_without_students(self):
        statistics = self.database.get_course_statistics()
        self.assertEqual(statistics[0], ("BCA", 3, 87.0, 91.0, 82.0))
        self.assertEqual(statistics[1], ("BBA", 2, 72.5, 76.0, 69.0))
        self.assertEqual(statistics[2], ("MCA", 0, None, None, None))
        self.assertEqual(statistics[3], ("MBA", 0, None, None, None))

    def test_courses_without_students_uses_left_join(self):
        self.assertEqual(
            [course.course_name for course in self.database.get_courses_without_students()],
            ["MCA", "MBA"],
        )

    def test_courses_without_students_screen(self):
        output = StringIO()
        with redirect_stdout(output):
            show_courses_without_students(self.database)
        self.assertIn("MCA", output.getvalue())
        self.assertIn("MBA", output.getvalue())

    def test_previous_analytics_and_filtering_methods_remain_available(self):
        self.assertEqual(self.database.get_total_students(), 5)
        self.assertEqual(self.database.get_total_marks(), 406.0)
        self.assertAlmostEqual(self.database.get_average_marks(), 81.2)
        self.assertEqual(self.database.get_highest_marks(), 91.0)
        self.assertEqual(self.database.get_lowest_marks(), 69.0)
        self.assertEqual(len(self.database.get_students_by_marks(80)), 3)
        self.assertEqual(len(self.database.search_students_by_name("ri")), 1)
        self.assertEqual(len(self.database.get_top_students(3)), 3)
        self.assertEqual(self.database.get_courses_above_average(80), [("BCA", 87.0)])

    def test_student_update_and_delete_preserve_course_relationship(self):
        updated = Student(1, "Rahul", 20, 2, 84)
        self.assertEqual(self.database.update_student(updated), 1)
        self.assertEqual(self.database.get_student_by_id(1).course_name, "BBA")
        self.assertEqual(self.database.delete_student(1), 1)
        self.assertIsNone(self.database.get_student_by_id(1))

    def test_successful_course_transfer_updates_student_and_history(self):
        self.database.transfer_student_course(1, 3)

        student = self.database.get_student_by_id(1)
        history = self.database.get_student_course_history(1)
        self.assertEqual(student.course_id, 3)
        self.assertEqual(student.course_name, "MCA")
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0][1:5], (1, "Rahul", "BCA", "MCA"))
        self.assertEqual(self.database.get_course_history(), history)

    def test_invalid_student_course_and_same_course_do_not_change_data(self):
        initial_student = self.database.get_student_by_id(1)

        with self.assertRaisesRegex(ValueError, "Student not found"):
            self.database.transfer_student_course(999, 3)
        with self.assertRaisesRegex(ValueError, "Invalid course ID"):
            self.database.transfer_student_course(1, 99)
        with self.assertRaisesRegex(ValueError, "already enrolled"):
            self.database.transfer_student_course(1, 1)

        self.assertEqual(self.database.get_student_by_id(1).course_id, initial_student.course_id)
        self.assertEqual(self.database.get_course_history(), [])

    def test_history_insert_failure_rolls_back_student_update(self):
        self.database.connection.execute(
            """
            CREATE TRIGGER fail_course_history_insert
            BEFORE INSERT ON student_course_history
            BEGIN
                SELECT RAISE(ABORT, 'simulated history insert failure');
            END
            """
        )
        self.database.connection.commit()

        with self.assertRaisesRegex(sqlite3.IntegrityError, "simulated history insert failure"):
            self.database.transfer_student_course(1, 3)

        self.assertEqual(self.database.get_student_by_id(1).course_id, 1)
        self.assertEqual(self.database.get_student_course_history(1), [])
        self.assertFalse(self.database.connection.in_transaction)

    def test_transaction_controls_commit_and_rollback(self):
        self.database.begin_transaction()
        self.database.connection.execute(
            "UPDATE students SET course_id = 3 WHERE student_id = 1"
        )
        self.database.rollback()
        self.assertEqual(self.database.get_student_by_id(1).course_id, 1)

        self.database.begin_transaction()
        self.database.connection.execute(
            "UPDATE students SET course_id = 3 WHERE student_id = 1"
        )
        self.database.commit()
        self.assertEqual(self.database.get_student_by_id(1).course_id, 3)

    def test_menu_rejects_unknown_course_without_adding_student(self):
        output = StringIO()
        with patch("builtins.input", side_effect=["99", "Invalid", "20", "99"]), redirect_stdout(output):
            add_student(self.database)
        self.assertIn("Invalid course ID.", output.getvalue())
        self.assertEqual(self.database.get_total_students(), 5)

    def test_menu_contains_all_required_options(self):
        output = StringIO()
        with patch("builtins.input", return_value="17"), redirect_stdout(output):
            run_application(self.database)
        menu = output.getvalue()
        for option in (
            "1. Add Course",
            "2. View Courses",
            "3. Add Student",
            "4. View All Students",
            "5. Search Student",
            "6. Search Students by Course",
            "7. Search Students by Marks",
            "8. Sort Students",
            "9. Top N Students",
            "10. Update Student",
            "11. Delete Student",
            "12. Student Statistics",
            "13. Course-wise Statistics",
            "14. Courses Without Students",
            "15. Transfer Student Course",
            "16. View Course Transfer History",
            "17. Exit",
        ):
            self.assertIn(option, menu)


class LegacyMigrationTests(unittest.TestCase):
    def test_migrates_task_five_course_names_into_relational_tables(self):
        with tempfile.TemporaryDirectory() as temp_directory:
            db_path = Path(temp_directory) / "task_five_students.db"
            connection = sqlite3.connect(db_path)
            connection.execute(
                """
                CREATE TABLE students (
                    student_id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    age INTEGER NOT NULL,
                    course TEXT NOT NULL,
                    marks REAL NOT NULL
                )
                """
            )
            connection.executemany(
                "INSERT INTO students VALUES (?, ?, ?, ?, ?)",
                [(1, "Rahul", 20, "BCA", 82), (2, "Amit", 21, " BBA ", 76)],
            )
            connection.commit()
            connection.close()

            database = Database(db_path)
            try:
                database.connect()
                database.create_table()
                self.assertEqual(database.get_total_students(), 2)
                self.assertEqual(
                    [student.course_name for student in database.get_all_students()],
                    ["BCA", "BBA"],
                )
                self.assertEqual(len(database.get_all_courses()), 2)
            finally:
                database.close()


if __name__ == "__main__":
    unittest.main()