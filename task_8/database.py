import importlib
from decimal import Decimal

from config import get_database_config
from course import Course
from student import Student


class DatabaseConnectionError(RuntimeError):
    pass


class DatabaseDependencyError(RuntimeError):
    pass


class Database:
    def __init__(self, connection_config=None):
        self.connection_config = connection_config
        self.connection = None
        self._transaction_active = False

    def connect(self):
        if self.connection is not None:
            return self.connection

        try:
            psycopg = importlib.import_module("psycopg")
        except ImportError as error:
            raise DatabaseDependencyError(
                "PostgreSQL driver is missing. Install project dependencies with "
                "'python -m pip install -r requirements.txt'."
            ) from error

        config = self.connection_config or get_database_config()
        try:
            self.connection = psycopg.connect(**config, autocommit=True)
            return self.connection
        except psycopg.OperationalError as error:
            sqlstate = getattr(error, "sqlstate", None) or ""
            if sqlstate.startswith("28"):
                raise DatabaseConnectionError("Database authentication failed.") from error
            raise DatabaseConnectionError("Unable to connect to database.") from error

    def close(self):
        if self.connection is not None:
            self.connection.close()
            self.connection = None
            self._transaction_active = False

    def _require_connection(self):
        if self.connection is None:
            raise RuntimeError("Connect to the PostgreSQL database first.")

    def execute_query(self, query, parameters=()):
        self._require_connection()
        return self.connection.execute(query, parameters)

    def fetch_one(self, query, parameters=()):
        cursor = self.execute_query(query, parameters)
        try:
            return cursor.fetchone()
        finally:
            cursor.close()

    def fetch_all(self, query, parameters=()):
        cursor = self.execute_query(query, parameters)
        try:
            return cursor.fetchall()
        finally:
            cursor.close()

    def commit(self):
        self._require_connection()
        if self._transaction_active:
            self.execute_query("COMMIT").close()
            self._transaction_active = False
        else:
            self.connection.commit()

    def rollback(self):
        self._require_connection()
        if self._transaction_active:
            self.execute_query("ROLLBACK").close()
            self._transaction_active = False
        else:
            self.connection.rollback()

    def begin_transaction(self):
        self._require_connection()
        if self._transaction_active:
            raise RuntimeError("A transaction is already active.")
        self.execute_query("BEGIN").close()
        self._transaction_active = True

    def create_tables(self):
        self._require_connection()
        statements = (
            """
            CREATE TABLE IF NOT EXISTS courses (
                course_id SERIAL PRIMARY KEY,
                course_name VARCHAR(100) NOT NULL UNIQUE
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS students (
                student_id INTEGER PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                age INTEGER NOT NULL CHECK (age > 0),
                course_id INTEGER NOT NULL REFERENCES courses(course_id),
                marks NUMERIC(5, 2) NOT NULL CHECK (marks >= 0 AND marks <= 100)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS student_course_history (
                history_id SERIAL PRIMARY KEY,
                student_id INTEGER NOT NULL REFERENCES students(student_id),
                old_course_id INTEGER NOT NULL REFERENCES courses(course_id),
                new_course_id INTEGER NOT NULL REFERENCES courses(course_id),
                changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
        )
        self.begin_transaction()
        try:
            for statement in statements:
                self.execute_query(statement).close()
            self.commit()
        except Exception:
            if self._transaction_active:
                self.rollback()
            raise

    @staticmethod
    def _is_integrity_error(error):
        return getattr(error, "sqlstate", None) is not None and str(
            error.sqlstate
        ).startswith("23")

    def add_course(self, course):
        course.validate()
        try:
            if course.course_id is None:
                row = self.fetch_one(
                    """
                    INSERT INTO courses (course_name)
                    VALUES (%s)
                    RETURNING course_id
                    """,
                    (course.course_name,),
                )
            else:
                row = self.fetch_one(
                    """
                    INSERT INTO courses (course_id, course_name)
                    VALUES (%s, %s)
                    RETURNING course_id
                    """,
                    (course.course_id, course.course_name),
                )
                self.fetch_one(
                    """
                    SELECT setval(
                        pg_get_serial_sequence('courses', 'course_id'),
                        GREATEST((SELECT COALESCE(MAX(course_id), 1) FROM courses), 1),
                        true
                    )
                    """
                )
            return row[0]
        except Exception as error:
            if self._is_integrity_error(error):
                constraint = getattr(error, "diag", None)
                constraint_name = getattr(constraint, "constraint_name", "")
                if constraint_name == "courses_course_name_key":
                    raise ValueError("Course name already exists.") from error
                if constraint_name == "courses_pkey":
                    raise ValueError("Course ID already exists.") from error
                raise ValueError("Course data violates database constraints.") from error
            raise

    def get_all_courses(self):
        rows = self.fetch_all(
            "SELECT course_id, course_name FROM courses ORDER BY course_id"
        )
        return [Course(*row) for row in rows]

    def get_course_by_id(self, course_id):
        row = self.fetch_one(
            "SELECT course_id, course_name FROM courses WHERE course_id = %s",
            (course_id,),
        )
        return Course(*row) if row else None

    def delete_course(self, course_id):
        try:
            cursor = self.execute_query(
                "DELETE FROM courses WHERE course_id = %s",
                (course_id,),
            )
            deleted = cursor.rowcount
            cursor.close()
            return deleted
        except Exception as error:
            if self._is_integrity_error(error):
                raise ValueError(
                    "Cannot delete a course referenced by students or transfer history."
                ) from error
            raise

    def add_student(self, student):
        student.validate()
        if self.get_course_by_id(student.course_id) is None:
            raise ValueError("Invalid course ID.")
        try:
            cursor = self.execute_query(
                """
                INSERT INTO students (student_id, name, age, course_id, marks)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (student.student_id, student.name, student.age, student.course_id, student.marks),
            )
            cursor.close()
        except Exception as error:
            if self._is_integrity_error(error):
                constraint = getattr(error, "diag", None)
                constraint_name = getattr(constraint, "constraint_name", "")
                if constraint_name == "students_pkey":
                    raise ValueError("Student ID already exists.") from error
                if constraint_name == "students_course_id_fkey":
                    raise ValueError("Invalid course ID.") from error
                raise ValueError("Student data violates database constraints.") from error
            raise

    def _get_students(self, query, parameters=()):
        return [Student(*row) for row in self.fetch_all(query, parameters)]

    def get_all_students(self):
        return self._get_students(
            """
            SELECT student_id, name, age, course_id, marks
            FROM students
            ORDER BY student_id
            """
        )

    def get_student_by_id(self, student_id):
        row = self.fetch_one(
            """
            SELECT student_id, name, age, course_id, marks
            FROM students
            WHERE student_id = %s
            """,
            (student_id,),
        )
        return Student(*row) if row else None

    def get_students_by_course(self, course_name):
        self._validate_course_name(course_name)
        return self._get_students(
            """
            SELECT s.student_id, s.name, s.age, s.course_id, s.marks
            FROM students AS s
            INNER JOIN courses AS c ON s.course_id = c.course_id
            WHERE c.course_name = %s
            ORDER BY s.student_id
            """,
            (course_name.strip(),),
        )

    def get_students_by_marks(self, min_marks):
        min_marks = self._validate_marks(min_marks)
        return self._get_students(
            """
            SELECT student_id, name, age, course_id, marks
            FROM students
            WHERE marks >= %s
            ORDER BY student_id
            """,
            (min_marks,),
        )

    def search_students_by_name(self, keyword):
        if not isinstance(keyword, str) or not keyword.strip():
            raise ValueError("Search keyword cannot be empty.")
        return self._get_students(
            """
            SELECT student_id, name, age, course_id, marks
            FROM students
            WHERE name ILIKE %s
            ORDER BY student_id
            """,
            (f"%{keyword.strip()}%",),
        )

    def get_students_by_course_and_min_marks(self, course_name, min_marks):
        self._validate_course_name(course_name)
        min_marks = self._validate_marks(min_marks)
        return self._get_students(
            """
            SELECT s.student_id, s.name, s.age, s.course_id, s.marks
            FROM students AS s
            INNER JOIN courses AS c ON s.course_id = c.course_id
            WHERE c.course_name = %s AND s.marks >= %s
            ORDER BY s.student_id
            """,
            (course_name.strip(), min_marks),
        )

    def get_students_by_courses(self, first_course, second_course):
        self._validate_course_name(first_course)
        self._validate_course_name(second_course)
        return self._get_students(
            """
            SELECT s.student_id, s.name, s.age, s.course_id, s.marks
            FROM students AS s
            INNER JOIN courses AS c ON s.course_id = c.course_id
            WHERE c.course_name = %s OR c.course_name = %s
            ORDER BY s.student_id
            """,
            (first_course.strip(), second_course.strip()),
        )

    def get_students_sorted_by_marks(self, desc=True):
        direction = "DESC" if desc else "ASC"
        return self._get_students(
            f"""
            SELECT student_id, name, age, course_id, marks
            FROM students
            ORDER BY marks {direction}, student_id
            """
        )

    def get_top_students(self, limit):
        if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
            raise ValueError("Number of students must be greater than 0.")
        return self._get_students(
            """
            SELECT student_id, name, age, course_id, marks
            FROM students
            ORDER BY marks DESC, student_id
            LIMIT %s
            """,
            (limit,),
        )

    def get_students_with_courses(self):
        return self.fetch_all(
            """
            SELECT s.student_id, s.name, c.course_name, s.marks
            FROM students AS s
            INNER JOIN courses AS c ON s.course_id = c.course_id
            ORDER BY s.student_id
            """
        )

    def get_course_statistics(self):
        return self.fetch_all(
            """
            SELECT c.course_name,
                   COUNT(s.student_id) AS total_students,
                   AVG(s.marks) AS average_marks,
                   MAX(s.marks) AS highest_marks,
                   MIN(s.marks) AS lowest_marks
            FROM courses AS c
            LEFT JOIN students AS s ON c.course_id = s.course_id
            GROUP BY c.course_id, c.course_name
            ORDER BY c.course_id
            """
        )

    def get_courses_without_students(self):
        return self.fetch_all(
            """
            SELECT c.course_id, c.course_name
            FROM courses AS c
            LEFT JOIN students AS s ON c.course_id = s.course_id
            WHERE s.student_id IS NULL
            ORDER BY c.course_id
            """
        )

    def get_total_students(self):
        return self.fetch_one("SELECT COUNT(*) FROM students")[0]

    def get_total_marks(self):
        return self.fetch_one("SELECT SUM(marks) FROM students")[0]

    def get_average_marks(self):
        return self.fetch_one("SELECT AVG(marks) FROM students")[0]

    def get_highest_marks(self):
        return self.fetch_one("SELECT MAX(marks) FROM students")[0]

    def get_lowest_marks(self):
        return self.fetch_one("SELECT MIN(marks) FROM students")[0]

    def get_course_statistics_by_aggregate(self, aggregate):
        aggregates = {"AVG": "AVG", "MAX": "MAX", "MIN": "MIN"}
        function = aggregates.get(aggregate)
        if function is None:
            raise ValueError("Unsupported aggregate.")
        return self.fetch_all(
            f"""
            SELECT c.course_name, {function}(s.marks)
            FROM courses AS c
            INNER JOIN students AS s ON c.course_id = s.course_id
            GROUP BY c.course_id, c.course_name
            ORDER BY c.course_name
            """
        )

    def get_course_average_marks(self):
        return self.get_course_statistics_by_aggregate("AVG")

    def get_course_highest_marks(self):
        return self.get_course_statistics_by_aggregate("MAX")

    def get_course_lowest_marks(self):
        return self.get_course_statistics_by_aggregate("MIN")

    def get_course_average_marks_for_minimum_marks(self, min_marks):
        min_marks = self._validate_marks(min_marks)
        return self.fetch_all(
            """
            SELECT c.course_name, AVG(s.marks) AS average_marks
            FROM courses AS c
            INNER JOIN students AS s ON c.course_id = s.course_id
            WHERE s.marks >= %s
            GROUP BY c.course_id, c.course_name
            ORDER BY c.course_name
            """,
            (min_marks,),
        )

    def get_courses_above_average(self, min_average):
        min_average = self._validate_marks(min_average)
        return self.fetch_all(
            """
            SELECT c.course_name, AVG(s.marks) AS average_marks
            FROM courses AS c
            INNER JOIN students AS s ON c.course_id = s.course_id
            GROUP BY c.course_id, c.course_name
            HAVING AVG(s.marks) >= %s
            ORDER BY c.course_name
            """,
            (min_average,),
        )

    def get_course_history(self):
        return self._query_course_history()

    def get_student_course_history(self, student_id):
        self._validate_student_id(student_id)
        return self._query_course_history(student_id)

    def _query_course_history(self, student_id=None):
        query = """
            SELECT h.history_id, h.student_id, s.name,
                   old_course.course_name, new_course.course_name, h.changed_at
            FROM student_course_history AS h
            INNER JOIN students AS s ON s.student_id = h.student_id
            INNER JOIN courses AS old_course ON old_course.course_id = h.old_course_id
            INNER JOIN courses AS new_course ON new_course.course_id = h.new_course_id
        """
        if student_id is not None:
            query += " WHERE h.student_id = %s"
            parameters = (student_id,)
        else:
            parameters = ()
        query += " ORDER BY h.history_id"
        return self.fetch_all(query, parameters)

    def transfer_student_course(self, student_id, new_course_id):
        self._validate_student_id(student_id)
        self._validate_course_id(new_course_id)
        self.begin_transaction()
        try:
            row = self.fetch_one(
                "SELECT course_id FROM students WHERE student_id = %s FOR UPDATE",
                (student_id,),
            )
            if row is None:
                raise ValueError("Student not found.")
            old_course_id = row[0]
            if old_course_id == new_course_id:
                raise ValueError("Student is already enrolled in this course.")
            if self.fetch_one(
                "SELECT 1 FROM courses WHERE course_id = %s",
                (new_course_id,),
            ) is None:
                raise ValueError("Invalid course ID.")

            cursor = self.execute_query(
                "UPDATE students SET course_id = %s WHERE student_id = %s",
                (new_course_id, student_id),
            )
            if cursor.rowcount != 1:
                cursor.close()
                raise ValueError("Student not found.")
            cursor.close()
            cursor = self.execute_query(
                """
                INSERT INTO student_course_history
                    (student_id, old_course_id, new_course_id)
                VALUES (%s, %s, %s)
                """,
                (student_id, old_course_id, new_course_id),
            )
            cursor.close()
            self.commit()
        except Exception:
            if self._transaction_active:
                self.rollback()
            raise

    def update_student(self, student):
        student.validate()
        self._validate_course_id(student.course_id)
        self.begin_transaction()
        try:
            row = self.fetch_one(
                "SELECT course_id FROM students WHERE student_id = %s FOR UPDATE",
                (student.student_id,),
            )
            if row is None:
                self.rollback()
                return 0
            if self.fetch_one(
                "SELECT 1 FROM courses WHERE course_id = %s",
                (student.course_id,),
            ) is None:
                raise ValueError("Invalid course ID.")

            old_course_id = row[0]
            cursor = self.execute_query(
                """
                UPDATE students
                SET name = %s, age = %s, course_id = %s, marks = %s
                WHERE student_id = %s
                """,
                (student.name, student.age, student.course_id, student.marks, student.student_id),
            )
            updated = cursor.rowcount
            cursor.close()
            if old_course_id != student.course_id:
                cursor = self.execute_query(
                    """
                    INSERT INTO student_course_history
                        (student_id, old_course_id, new_course_id)
                    VALUES (%s, %s, %s)
                    """,
                    (student.student_id, old_course_id, student.course_id),
                )
                cursor.close()
            self.commit()
            return updated
        except Exception:
            if self._transaction_active:
                self.rollback()
            raise

    def delete_student(self, student_id):
        try:
            cursor = self.execute_query(
                "DELETE FROM students WHERE student_id = %s",
                (student_id,),
            )
            deleted = cursor.rowcount
            cursor.close()
            return deleted
        except Exception as error:
            if self._is_integrity_error(error):
                raise ValueError(
                    "Cannot delete a student referenced by transfer history."
                ) from error
            raise

    @staticmethod
    def _validate_course_name(course_name):
        if not isinstance(course_name, str) or not course_name.strip():
            raise ValueError("Course name cannot be empty.")
        if len(course_name.strip()) > 100:
            raise ValueError("Course name cannot exceed 100 characters.")

    @staticmethod
    def _validate_marks(marks):
        if (
            isinstance(marks, bool)
            or not isinstance(marks, (int, float, Decimal))
            or not 0 <= marks <= 100
        ):
            raise ValueError("Marks must be between 0 and 100.")
        return float(marks)

    @staticmethod
    def _validate_student_id(student_id):
        if isinstance(student_id, bool) or not isinstance(student_id, int):
            raise ValueError("Student ID must be an integer.")

    @staticmethod
    def _validate_course_id(course_id):
        if isinstance(course_id, bool) or not isinstance(course_id, int):
            raise ValueError("Course ID must be an integer.")
