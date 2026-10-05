import sqlite3
from pathlib import Path

from course import Course
from student import Student


class Database:
    def __init__(self, db_path=None):
        self.db_path = Path(db_path) if db_path else Path(__file__).with_name("student_management.db")
        self.connection = None

    def connect(self):
        self.connection = sqlite3.connect(self.db_path)
        self.connection.execute("PRAGMA foreign_keys = ON")
        return self.connection

    def _require_connection(self, action):
        if self.connection is None:
            raise sqlite3.ProgrammingError(f"Connect to the database before {action}.")

    def create_course_table(self):
        self._require_connection("creating tables")
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS courses (
                course_id INTEGER PRIMARY KEY,
                course_name TEXT NOT NULL UNIQUE
            )
            """
        )

    def create_table(self):
        self._require_connection("creating tables")
        self.create_course_table()
        table_exists = self.connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'students'"
        ).fetchone()
        if not table_exists:
            self._create_students_table("students")
        else:
            columns = {
                row[1] for row in self.connection.execute("PRAGMA table_info(students)").fetchall()
            }
            if "course_id" not in columns:
                self._migrate_legacy_students()

        self.create_history_table()
        self.connection.execute("PRAGMA user_version = 3")
        self.connection.commit()

    def _create_students_table(self, table_name):
        self.connection.execute(
            f"""
            CREATE TABLE {table_name} (
                student_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                age INTEGER NOT NULL CHECK (age > 0),
                course_id INTEGER NOT NULL,
                marks REAL NOT NULL CHECK (marks >= 0 AND marks <= 100),
                FOREIGN KEY (course_id) REFERENCES courses(course_id)
            )
            """
        )

    def _migrate_legacy_students(self):
        try:
            self.connection.execute("BEGIN")
            self.connection.execute(
                """
                INSERT OR IGNORE INTO courses (course_name)
                SELECT DISTINCT TRIM(course)
                FROM students
                WHERE course IS NOT NULL AND TRIM(course) <> ''
                """
            )
            self._create_students_table("students_new")
            self.connection.execute(
                """
                INSERT INTO students_new (student_id, name, age, course_id, marks)
                SELECT s.student_id, s.name, s.age, c.course_id, s.marks
                FROM students AS s
                INNER JOIN courses AS c ON TRIM(s.course) = c.course_name
                """
            )
            old_count = self.connection.execute("SELECT COUNT(*) FROM students").fetchone()[0]
            new_count = self.connection.execute("SELECT COUNT(*) FROM students_new").fetchone()[0]
            if old_count != new_count:
                raise sqlite3.IntegrityError("Some legacy students have no valid course name.")
            self.connection.execute("DROP TABLE students")
            self.connection.execute("ALTER TABLE students_new RENAME TO students")
        except sqlite3.Error:
            self.connection.rollback()
            raise

    def create_history_table(self):
        self._require_connection("creating the course history table")
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS student_course_history (
                history_id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                old_course_id INTEGER NOT NULL,
                new_course_id INTEGER NOT NULL,
                changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES students(student_id),
                FOREIGN KEY (old_course_id) REFERENCES courses(course_id),
                FOREIGN KEY (new_course_id) REFERENCES courses(course_id)
            )
            """
        )

    def add_course(self, course):
        self._require_connection("adding courses")
        course.validate()
        try:
            self.connection.execute(
                "INSERT INTO courses (course_id, course_name) VALUES (?, ?)",
                (course.course_id, course.course_name),
            )
            self.connection.commit()
        except sqlite3.IntegrityError as error:
            self.connection.rollback()
            if "UNIQUE constraint failed: courses.course_id" in str(error):
                raise ValueError("Course ID already exists.") from error
            if "UNIQUE constraint failed: courses.course_name" in str(error):
                raise ValueError("Course name already exists.") from error
            raise ValueError("Course data violates database constraints.") from error
        except sqlite3.Error:
            self.connection.rollback()
            raise

    def get_all_courses(self):
        self._require_connection("reading courses")
        rows = self.connection.execute(
            "SELECT course_id, course_name FROM courses ORDER BY course_id"
        ).fetchall()
        return [Course(*row) for row in rows]

    def get_course_by_id(self, course_id):
        self._require_connection("searching courses")
        row = self.connection.execute(
            "SELECT course_id, course_name FROM courses WHERE course_id = ?",
            (course_id,),
        ).fetchone()
        return Course(*row) if row else None

    def delete_course(self, course_id):
        self._require_connection("deleting courses")
        try:
            cursor = self.connection.execute("DELETE FROM courses WHERE course_id = ?", (course_id,))
            self.connection.commit()
            return cursor.rowcount
        except sqlite3.IntegrityError as error:
            self.connection.rollback()
            raise ValueError("Cannot delete a course referenced by students or transfer history.") from error
        except sqlite3.Error:
            self.connection.rollback()
            raise

    def add_student(self, student):
        self._require_connection("adding students")
        student.validate()
        if self.get_course_by_id(student.course_id) is None:
            raise ValueError("Invalid course ID.")

        try:
            self.connection.execute(
                """
                INSERT INTO students (student_id, name, age, course_id, marks)
                VALUES (?, ?, ?, ?, ?)
                """,
                (student.student_id, student.name, student.age, student.course_id, student.marks),
            )
            self.connection.commit()
        except sqlite3.IntegrityError as error:
            self.connection.rollback()
            if "UNIQUE constraint failed: students.student_id" in str(error):
                raise ValueError("Student ID already exists.") from error
            if "FOREIGN KEY constraint failed" in str(error):
                raise ValueError("Invalid course ID.") from error
            raise ValueError("Student data violates database constraints.") from error
        except sqlite3.Error:
            self.connection.rollback()
            raise

    def _get_students(self, query, parameters=()):
        self._require_connection("reading students")
        rows = self.connection.execute(query, parameters).fetchall()
        students = []
        for row in rows:
            student = Student(*row[:5])
            if len(row) > 5:
                student.course_name = row[5]
            students.append(student)
        return students

    def get_all_students(self):
        return self._get_students(
            """
            SELECT s.student_id, s.name, s.age, s.course_id, s.marks, c.course_name
            FROM students AS s
            INNER JOIN courses AS c ON s.course_id = c.course_id
            ORDER BY s.student_id
            """
        )

    def get_student_by_id(self, student_id):
        students = self._get_students(
            """
            SELECT s.student_id, s.name, s.age, s.course_id, s.marks, c.course_name
            FROM students AS s
            INNER JOIN courses AS c ON s.course_id = c.course_id
            WHERE s.student_id = ?
            """,
            (student_id,),
        )
        return students[0] if students else None

    def get_students_by_course(self, course):
        course = self._validate_course(course)
        return self._get_students(
            """
            SELECT s.student_id, s.name, s.age, s.course_id, s.marks, c.course_name
            FROM students AS s
            INNER JOIN courses AS c ON s.course_id = c.course_id
            WHERE c.course_name = ?
            ORDER BY s.student_id
            """,
            (course,),
        )

    def get_students_by_marks(self, min_marks):
        min_marks = self._validate_min_marks(min_marks)
        return self._get_students(
            """
            SELECT s.student_id, s.name, s.age, s.course_id, s.marks, c.course_name
            FROM students AS s
            INNER JOIN courses AS c ON s.course_id = c.course_id
            WHERE s.marks >= ?
            ORDER BY s.student_id
            """,
            (min_marks,),
        )

    def search_students_by_name(self, keyword):
        if not isinstance(keyword, str) or not keyword.strip():
            raise ValueError("Search keyword cannot be empty.")
        return self._get_students(
            """
            SELECT s.student_id, s.name, s.age, s.course_id, s.marks, c.course_name
            FROM students AS s
            INNER JOIN courses AS c ON s.course_id = c.course_id
            WHERE s.name LIKE ?
            ORDER BY s.student_id
            """,
            (f"%{keyword.strip()}%",),
        )

    def get_students_by_course_and_min_marks(self, course, min_marks):
        course = self._validate_course(course)
        min_marks = self._validate_min_marks(min_marks)
        return self._get_students(
            """
            SELECT s.student_id, s.name, s.age, s.course_id, s.marks, c.course_name
            FROM students AS s
            INNER JOIN courses AS c ON s.course_id = c.course_id
            WHERE c.course_name = ? AND s.marks >= ?
            ORDER BY s.student_id
            """,
            (course, min_marks),
        )

    def get_students_by_courses(self, first_course, second_course):
        first_course = self._validate_course(first_course)
        second_course = self._validate_course(second_course)
        return self._get_students(
            """
            SELECT s.student_id, s.name, s.age, s.course_id, s.marks, c.course_name
            FROM students AS s
            INNER JOIN courses AS c ON s.course_id = c.course_id
            WHERE c.course_name = ? OR c.course_name = ?
            ORDER BY s.student_id
            """,
            (first_course, second_course),
        )

    def get_students_sorted_by_marks(self, desc=True):
        direction = "DESC" if desc else "ASC"
        return self._get_students(
            f"""
            SELECT s.student_id, s.name, s.age, s.course_id, s.marks, c.course_name
            FROM students AS s
            INNER JOIN courses AS c ON s.course_id = c.course_id
            ORDER BY s.marks {direction}
            """
        )

    def get_top_students(self, limit):
        if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
            raise ValueError("Number of students must be greater than 0.")
        return self._get_students(
            """
            SELECT s.student_id, s.name, s.age, s.course_id, s.marks, c.course_name
            FROM students AS s
            INNER JOIN courses AS c ON s.course_id = c.course_id
            ORDER BY s.marks DESC
            LIMIT ?
            """,
            (limit,),
        )

    def get_students_with_courses(self):
        self._require_connection("reading students")
        return self.connection.execute(
            """
            SELECT s.student_id, s.name, c.course_name, s.marks
            FROM students AS s
            INNER JOIN courses AS c ON s.course_id = c.course_id
            ORDER BY s.student_id
            """
        ).fetchall()

    def get_courses_without_students(self):
        self._require_connection("reading courses")
        rows = self.connection.execute(
            """
            SELECT c.course_id, c.course_name
            FROM courses AS c
            LEFT JOIN students AS s ON c.course_id = s.course_id
            WHERE s.student_id IS NULL
            ORDER BY c.course_id
            """
        ).fetchall()
        return [Course(*row) for row in rows]

    def get_total_students(self):
        return self._get_scalar("SELECT COUNT(*) FROM students")

    def get_average_marks(self):
        return self._get_scalar("SELECT AVG(marks) FROM students")

    def get_total_marks(self):
        return self._get_scalar("SELECT SUM(marks) FROM students")

    def get_highest_marks(self):
        return self._get_scalar("SELECT MAX(marks) FROM students")

    def get_lowest_marks(self):
        return self._get_scalar("SELECT MIN(marks) FROM students")

    def _get_scalar(self, query, parameters=()):
        self._require_connection("reading analytics")
        return self.connection.execute(query, parameters).fetchone()[0]

    def get_course_statistics(self):
        self._require_connection("reading analytics")
        return self.connection.execute(
            """
            SELECT c.course_name, COUNT(s.student_id) AS total_students,
                   AVG(s.marks) AS average_marks, MAX(s.marks) AS highest_marks,
                   MIN(s.marks) AS lowest_marks
            FROM courses AS c
            LEFT JOIN students AS s ON c.course_id = s.course_id
            GROUP BY c.course_id, c.course_name
            ORDER BY c.course_id
            """
        ).fetchall()

    def get_course_average_marks(self):
        self._require_connection("reading analytics")
        return self.connection.execute(
            """
            SELECT c.course_name, AVG(s.marks)
            FROM courses AS c
            LEFT JOIN students AS s ON c.course_id = s.course_id
            GROUP BY c.course_id, c.course_name
            ORDER BY c.course_id
            """
        ).fetchall()

    def get_course_highest_marks(self):
        self._require_connection("reading analytics")
        return self.connection.execute(
            """
            SELECT c.course_name, MAX(s.marks)
            FROM courses AS c
            LEFT JOIN students AS s ON c.course_id = s.course_id
            GROUP BY c.course_id, c.course_name
            ORDER BY c.course_id
            """
        ).fetchall()

    def get_course_lowest_marks(self):
        self._require_connection("reading analytics")
        return self.connection.execute(
            """
            SELECT c.course_name, MIN(s.marks)
            FROM courses AS c
            LEFT JOIN students AS s ON c.course_id = s.course_id
            GROUP BY c.course_id, c.course_name
            ORDER BY c.course_id
            """
        ).fetchall()

    def get_course_average_marks_for_minimum_marks(self, min_marks):
        min_marks = self._validate_min_marks(min_marks)
        self._require_connection("reading analytics")
        return self.connection.execute(
            """
            SELECT c.course_name, AVG(s.marks) AS average_marks
            FROM courses AS c
            INNER JOIN students AS s ON c.course_id = s.course_id
            WHERE s.marks >= ?
            GROUP BY c.course_id, c.course_name
            ORDER BY c.course_id
            """,
            (min_marks,),
        ).fetchall()

    def get_courses_above_average(self, min_average):
        if (
            isinstance(min_average, bool)
            or not isinstance(min_average, (int, float))
            or not 0 <= min_average <= 100
        ):
            raise ValueError("Minimum average must be between 0 and 100.")
        self._require_connection("reading analytics")
        return self.connection.execute(
            """
            SELECT c.course_name, AVG(s.marks) AS average_marks
            FROM courses AS c
            INNER JOIN students AS s ON c.course_id = s.course_id
            GROUP BY c.course_id, c.course_name
            HAVING AVG(s.marks) >= ?
            ORDER BY c.course_id
            """,
            (float(min_average),),
        ).fetchall()

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
        self._require_connection("updating students")
        student.validate()
        current = self.get_student_by_id(student.student_id)
        if current is None:
            return 0
        if current.course_id != student.course_id:
            raise ValueError("Use transfer_student_course() to change a student's course.")

        try:
            cursor = self.connection.execute(
                """
                UPDATE students
                SET name = ?, age = ?, marks = ?
                WHERE student_id = ?
                """,
                (student.name, student.age, student.marks, student.student_id),
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
        self._require_connection("deleting students")
        try:
            cursor = self.connection.execute("DELETE FROM students WHERE student_id = ?", (student_id,))
            self.connection.commit()
            return cursor.rowcount
        except sqlite3.IntegrityError as error:
            self.connection.rollback()
            raise ValueError("Cannot delete a student with course transfer history.") from error
        except sqlite3.Error:
            self.connection.rollback()
            raise

    def begin_transaction(self):
        self._require_connection("starting a transaction")
        self.connection.execute("BEGIN")

    def commit(self):
        self._require_connection("committing a transaction")
        self.connection.commit()

    def rollback(self):
        self._require_connection("rolling back a transaction")
        self.connection.rollback()

    def transfer_student_course(self, student_id, new_course_id):
        self._require_connection("transferring a student")
        if isinstance(student_id, bool) or not isinstance(student_id, int):
            raise ValueError("Student ID must be an integer.")
        if isinstance(new_course_id, bool) or not isinstance(new_course_id, int):
            raise ValueError("Course ID must be an integer.")

        student = self.get_student_by_id(student_id)
        if student is None:
            raise ValueError("Student not found.")
        if self.get_course_by_id(new_course_id) is None:
            raise ValueError("Invalid course ID.")
        if student.course_id == new_course_id:
            raise ValueError("Student is already enrolled in this course.")

        self.begin_transaction()
        try:
            current = self.connection.execute(
                "SELECT course_id FROM students WHERE student_id = ?",
                (student_id,),
            ).fetchone()
            if current is None:
                raise ValueError("Student not found.")
            if self.connection.execute(
                "SELECT 1 FROM courses WHERE course_id = ?", (new_course_id,)
            ).fetchone() is None:
                raise ValueError("Invalid course ID.")

            old_course_id = current[0]
            if old_course_id == new_course_id:
                raise ValueError("Student is already enrolled in this course.")

            cursor = self.connection.execute(
                "UPDATE students SET course_id = ? WHERE student_id = ?",
                (new_course_id, student_id),
            )
            if cursor.rowcount != 1:
                raise ValueError("Student not found.")

            history_cursor = self.connection.execute(
                """
                INSERT INTO student_course_history
                    (student_id, old_course_id, new_course_id)
                VALUES (?, ?, ?)
                """,
                (student_id, old_course_id, new_course_id),
            )
            self.commit()
            return history_cursor.lastrowid
        except Exception:
            if self.connection.in_transaction:
                self.rollback()
            raise

    def _history_query(self, where_clause="", parameters=()):
        self._require_connection("reading course history")
        return self.connection.execute(
            f"""
            SELECT h.history_id, h.student_id, s.name, old_course.course_name,
                   new_course.course_name, h.changed_at
            FROM student_course_history AS h
            INNER JOIN students AS s ON h.student_id = s.student_id
            INNER JOIN courses AS old_course ON h.old_course_id = old_course.course_id
            INNER JOIN courses AS new_course ON h.new_course_id = new_course.course_id
            {where_clause}
            ORDER BY h.history_id
            """,
            parameters,
        ).fetchall()

    def get_course_history(self):
        return self._history_query()

    def get_student_course_history(self, student_id):
        if isinstance(student_id, bool) or not isinstance(student_id, int):
            raise ValueError("Student ID must be an integer.")
        return self._history_query("WHERE h.student_id = ?", (student_id,))

    @staticmethod
    def _validate_course_name(course_name):
        if not isinstance(course_name, str) or not course_name.strip():
            raise ValueError("Course name cannot be empty.")
        return course_name.strip()

    def close(self):
        if self.connection is not None:
            if self.connection.in_transaction:
                self.connection.rollback()
            self.connection.close()
            self.connection = None