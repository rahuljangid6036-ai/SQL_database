import sqlite3
from pathlib import Path

from student import Student


class Database:
    def __init__(self, db_path=None):
        self.db_path = Path(db_path) if db_path else Path(__file__).with_name("student_management.db")
        self.connection = None

    def connect(self):
        self.connection = sqlite3.connect(self.db_path)
        return self.connection

    def create_table(self):
        if self.connection is None:
            raise sqlite3.ProgrammingError("Connect to the database before creating the table.")

        table_exists = self.connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'students'"
        ).fetchone()
        schema_version = self.connection.execute("PRAGMA user_version").fetchone()[0]

        if not table_exists:
            self._create_students_table("students")
        elif schema_version < 1:
            self._migrate_students_table()

        self.connection.execute("PRAGMA user_version = 1")
        self.connection.commit()

    def _create_students_table(self, table_name):
        self.connection.execute(
            f"""
            CREATE TABLE {table_name} (
                student_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                age INTEGER NOT NULL CHECK (age > 0),
                course TEXT NOT NULL,
                marks REAL NOT NULL CHECK (marks >= 0 AND marks <= 100)
            )
            """
        )

    def _migrate_students_table(self):
        try:
            self.connection.execute("BEGIN")
            self._create_students_table("students_new")
            self.connection.execute(
                """
                INSERT INTO students_new (student_id, name, age, course, marks)
                SELECT student_id, name, age, course, marks FROM students
                """
            )
            self.connection.execute("DROP TABLE students")
            self.connection.execute("ALTER TABLE students_new RENAME TO students")
        except sqlite3.Error:
            self.connection.rollback()
            raise

    def add_student(self, student):
        if self.connection is None:
            raise sqlite3.ProgrammingError("Connect to the database before adding students.")

        student.validate()
        try:
            self.connection.execute(
                """
                INSERT INTO students (student_id, name, age, course, marks)
                VALUES (?, ?, ?, ?, ?)
                """,
                (student.student_id, student.name, student.age, student.course, student.marks),
            )
            self.connection.commit()
        except sqlite3.IntegrityError as error:
            self.connection.rollback()
            if "UNIQUE constraint failed: students.student_id" in str(error):
                raise ValueError("Student ID already exists.") from error
            raise ValueError("Student data violates database constraints.") from error
        except sqlite3.Error:
            self.connection.rollback()
            raise

    def _get_students(self, query, parameters=()):
        if self.connection is None:
            raise sqlite3.ProgrammingError("Connect to the database before reading students.")

        rows = self.connection.execute(query, parameters).fetchall()
        return [Student(*row) for row in rows]

    def get_all_students(self):
        return self._get_students(
            "SELECT student_id, name, age, course, marks FROM students ORDER BY student_id"
        )

    def get_student_by_id(self, student_id):
        rows = self._get_students(
            "SELECT student_id, name, age, course, marks FROM students WHERE student_id = ?",
            (student_id,),
        )
        return rows[0] if rows else None

    def get_students_by_course(self, course):
        course = self._validate_course(course)
        return self._get_students(
            "SELECT student_id, name, age, course, marks FROM students WHERE course = ?",
            (course,),
        )

    def get_students_by_marks(self, min_marks):
        min_marks = self._validate_min_marks(min_marks)
        return self._get_students(
            "SELECT student_id, name, age, course, marks FROM students WHERE marks >= ?",
            (min_marks,),
        )

    def search_students_by_name(self, keyword):
        if not isinstance(keyword, str) or not keyword.strip():
            raise ValueError("Search keyword cannot be empty.")

        pattern = f"%{keyword.strip()}%"
        return self._get_students(
            "SELECT student_id, name, age, course, marks FROM students WHERE name LIKE ?",
            (pattern,),
        )

    def get_students_by_course_and_min_marks(self, course, min_marks):
        course = self._validate_course(course)
        min_marks = self._validate_min_marks(min_marks)
        return self._get_students(
            """
            SELECT student_id, name, age, course, marks FROM students
            WHERE course = ? AND marks >= ?
            """,
            (course, min_marks),
        )

    def get_students_by_courses(self, first_course, second_course):
        first_course = self._validate_course(first_course)
        second_course = self._validate_course(second_course)
        return self._get_students(
            """
            SELECT student_id, name, age, course, marks FROM students
            WHERE course = ? OR course = ?
            """,
            (first_course, second_course),
        )

    def get_students_sorted_by_marks(self, desc=True):
        direction = "DESC" if desc else "ASC"
        return self._get_students(
            f"SELECT student_id, name, age, course, marks FROM students ORDER BY marks {direction}"
        )

    def get_top_students(self, limit):
        if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
            raise ValueError("Number of students must be greater than 0.")

        return self._get_students(
            "SELECT student_id, name, age, course, marks FROM students ORDER BY marks DESC LIMIT ?",
            (limit,),
        )

    @staticmethod
    def _validate_course(course):
        if not isinstance(course, str) or not course.strip():
            raise ValueError("Course cannot be empty.")
        return course.strip()

    @staticmethod
    def _validate_min_marks(min_marks):
        if (
            isinstance(min_marks, bool)
            or not isinstance(min_marks, (int, float))
            or not 0 <= min_marks <= 100
        ):
            raise ValueError("Invalid marks.")
        return float(min_marks)

    def update_student(self, student):
        if self.connection is None:
            raise sqlite3.ProgrammingError("Connect to the database before updating students.")

        student.validate()
        try:
            cursor = self.connection.execute(
                """
                UPDATE students
                SET name = ?, age = ?, course = ?, marks = ?
                WHERE student_id = ?
                """,
                (student.name, student.age, student.course, student.marks, student.student_id),
            )
            self.connection.commit()
            return cursor.rowcount
        except sqlite3.IntegrityError as error:
            self.connection.rollback()
            raise ValueError("Student data violates database constraints.") from error
        except sqlite3.Error:
            self.connection.rollback()
            raise

    def delete_student(self, student_id):
        if self.connection is None:
            raise sqlite3.ProgrammingError("Connect to the database before deleting students.")

        try:
            cursor = self.connection.execute(
                "DELETE FROM students WHERE student_id = ?",
                (student_id,),
            )
            self.connection.commit()
            return cursor.rowcount
        except sqlite3.Error:
            self.connection.rollback()
            raise

    def close(self):
        if self.connection is not None:
            self.connection.close()
            self.connection = None