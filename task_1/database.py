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

    def get_all_students(self):
        if self.connection is None:
            raise sqlite3.ProgrammingError("Connect to the database before reading students.")

        rows = self.connection.execute(
            "SELECT student_id, name, age, course, marks FROM students ORDER BY student_id"
        ).fetchall()
        return [Student(*row) for row in rows]

    def get_student_by_id(self, student_id):
        if self.connection is None:
            raise sqlite3.ProgrammingError("Connect to the database before searching students.")

        row = self.connection.execute(
            "SELECT student_id, name, age, course, marks FROM students WHERE student_id = ?",
            (student_id,),
        ).fetchone()
        return Student(*row) if row else None

    def close(self):
        if self.connection is not None:
            self.connection.close()
            self.connection = None