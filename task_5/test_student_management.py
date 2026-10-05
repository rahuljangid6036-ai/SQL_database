import sqlite3
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from database import Database
from main import run_application, show_course_statistics, show_student_statistics
from student import Student


class StudentAnalyticsTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        db_path = Path(self.temp_directory.name) / "test_students.db"
        self.database = Database(db_path)
        self.database.connect()
        self.database.create_table()
        records = [
            Student(1, "Riya Sharma", 20, "BCA", 91),
            Student(2, "Priya Singh", 19, "BCA", 87),
            Student(3, "Rahul Das", 21, "BCA", 82),
            Student(4, "Karan Patel", 22, "BBA", 76),
            Student(5, "Amit Kumar", 20, "BBA", 69),
        ]
        for student in records:
            self.database.add_student(student)

    def tearDown(self):
        self.database.close()
        self.temp_directory.cleanup()

    def test_scalar_aggregates_are_computed_by_sql(self):
        self.assertEqual(self.database.get_total_students(), 5)
        self.assertEqual(self.database.get_total_marks(), 405.0)
        self.assertAlmostEqual(self.database.get_average_marks(), 81.0)
        self.assertEqual(self.database.get_highest_marks(), 91.0)
        self.assertEqual(self.database.get_lowest_marks(), 69.0)

    def test_combined_course_statistics(self):
        statistics = self.database.get_course_statistics()
        self.assertEqual(statistics[0][0:2], ("BBA", 2))
        self.assertAlmostEqual(statistics[0][2], 72.5)
        self.assertEqual(statistics[0][3:], (76.0, 69.0))
        self.assertEqual(statistics[1][0:2], ("BCA", 3))
        self.assertAlmostEqual(statistics[1][2], 260 / 3)
        self.assertEqual(statistics[1][3:], (91.0, 82.0))

    def test_individual_course_aggregates(self):
        self.assertEqual(self.database.get_course_average_marks()[0], ("BBA", 72.5))
        self.assertEqual(self.database.get_course_highest_marks(), [("BBA", 76.0), ("BCA", 91.0)])
        self.assertEqual(self.database.get_course_lowest_marks(), [("BBA", 69.0), ("BCA", 82.0)])

    def test_where_filters_rows_before_grouping(self):
        statistics = self.database.get_course_average_marks_for_minimum_marks(80)
        self.assertEqual(len(statistics), 1)
        self.assertEqual(statistics[0][0], "BCA")
        self.assertAlmostEqual(statistics[0][1], 260 / 3)

    def test_having_filters_group_averages(self):
        statistics = self.database.get_courses_above_average(80)
        self.assertEqual(len(statistics), 1)
        self.assertEqual(statistics[0][0], "BCA")
        self.assertAlmostEqual(statistics[0][1], 260 / 3)

    def test_having_accepts_exact_average_boundary(self):
        self.assertEqual(self.database.get_courses_above_average(72.5)[0][0], "BBA")

    def test_rejects_invalid_having_average(self):
        with self.assertRaisesRegex(ValueError, "Minimum average must be between 0 and 100"):
            self.database.get_courses_above_average(150)

    def test_previous_crud_and_filtering_apis_remain_available(self):
        self.assertEqual(len(self.database.get_all_students()), 5)
        self.assertEqual(self.database.get_student_by_id(1).name, "Riya Sharma")
        self.assertEqual(len(self.database.get_students_by_course("BCA")), 3)
        self.assertEqual(len(self.database.search_students_by_name("ri")), 2)
        self.assertEqual(len(self.database.get_students_by_marks(80)), 3)
        self.assertEqual(len(self.database.get_top_students(3)), 3)
        self.assertEqual(
            self.database.update_student(Student(5, "Amit Kumar", 20, "BBA", 70)), 1
        )
        self.assertEqual(self.database.delete_student(5), 1)

    def test_student_statistics_screen_uses_aggregate_values(self):
        output = StringIO()
        with redirect_stdout(output):
            show_student_statistics(self.database)
        self.assertIn("Total Students      : 5", output.getvalue())
        self.assertIn("Total Marks         : 405", output.getvalue())
        self.assertIn("Average Marks       : 81.00", output.getvalue())
        self.assertIn("Highest Marks       : 91", output.getvalue())
        self.assertIn("Lowest Marks        : 69", output.getvalue())

    def test_course_statistics_screen_displays_table_and_having_results(self):
        output = StringIO()
        with patch("builtins.input", return_value="80"), redirect_stdout(output):
            show_course_statistics(self.database)
        text = output.getvalue()
        self.assertIn("Course", text)
        self.assertIn("BCA", text)
        self.assertIn("BBA", text)
        self.assertIn("Courses with average marks >= 80", text)
        self.assertIn("BCA: 86.67", text)
        self.assertNotIn("BBA: 72.50", text)

    def test_menu_contains_all_sql_py_005_options(self):
        output = StringIO()
        with patch("builtins.input", return_value="13"), redirect_stdout(output):
            run_application(self.database)
        for option in (
            "11. Student Statistics",
            "12. Course-wise Statistics",
            "13. Exit",
        ):
            self.assertIn(option, output.getvalue())


class EmptyDatabaseAnalyticsTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        db_path = Path(self.temp_directory.name) / "empty_students.db"
        self.database = Database(db_path)
        self.database.connect()
        self.database.create_table()

    def tearDown(self):
        self.database.close()
        self.temp_directory.cleanup()

    def test_empty_aggregate_results(self):
        self.assertEqual(self.database.get_total_students(), 0)
        self.assertIsNone(self.database.get_total_marks())
        self.assertIsNone(self.database.get_average_marks())
        self.assertIsNone(self.database.get_highest_marks())
        self.assertIsNone(self.database.get_lowest_marks())
        self.assertEqual(self.database.get_course_statistics(), [])
        self.assertEqual(self.database.get_courses_above_average(80), [])

    def test_empty_analytics_screens_do_not_crash(self):
        output = StringIO()
        with redirect_stdout(output):
            show_student_statistics(self.database)
        self.assertIn("Total Students      : 0", output.getvalue())
        self.assertIn("Average Marks       : N/A", output.getvalue())
        output = StringIO()
        with patch("builtins.input", return_value=""), redirect_stdout(output):
            show_course_statistics(self.database)
        self.assertIn("No course statistics found.", output.getvalue())
        self.assertIn("No courses meet this average.", output.getvalue())


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