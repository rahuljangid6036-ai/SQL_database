# University Student Management System

**Task ID:** SQL-PY-002

## Problem statement

Store student records persistently in SQLite and protect their integrity at both the Python and database levels. The application can add students, list saved students, and search by student ID.

## Technologies

- Python 3
- SQLite through Python's built-in `sqlite3` module
- SQL (`CREATE TABLE`, `INSERT`, and `SELECT ... WHERE`)

## Project files

- `main.py` runs the menu-driven application.
- `student.py` defines the `Student` class and validates student data.
- `database.py` manages the SQLite connection and student queries.
- `test_student_management.py` contains automated tests.
- `student_management.db` is created beside the Python files on first run.

## Database table

The `students` table has five columns: `student_id INTEGER PRIMARY KEY`, `name TEXT NOT NULL`, `age INTEGER NOT NULL CHECK (age > 0)`, `course TEXT NOT NULL`, and `marks REAL NOT NULL CHECK (marks >= 0 AND marks <= 100)`. The database rejects duplicate IDs, missing required values, invalid ages, and marks outside 0-100, even when writes bypass Python validation.

On startup, the application upgrades a Task 1 table inside a transaction and preserves its records. If an old record violates the new constraints, the migration rolls back rather than discarding data.

## Run the application

Open a terminal in this folder and run:

```powershell
python main.py
```

Choose an option to add a student, view all students, search by ID, or exit. Records remain in `student_management.db` after the program closes.

Run the automated tests with:

```powershell
python -m unittest -v
```

## INSERT and SELECT

`Database.add_student()` runs a parameterized `INSERT INTO students ... VALUES (?, ?, ?, ?, ?)` statement and calls `commit()` so the new record is saved. A duplicate primary key is translated to `Student ID already exists.` and failed writes are rolled back. `get_all_students()` uses `SELECT` to retrieve every record. `get_student_by_id()` uses `SELECT ... WHERE student_id = ?` to retrieve one matching record. Parameters are passed separately from SQL so user input is treated as data.

## Validation rules

- Student ID must be an integer.
- Name and course must contain non-whitespace text.
- Age must be an integer greater than zero.
- Marks must be a number from 0 through 100.
- Student IDs already in the table cannot be added again.

Invalid input is rejected before the insert. The application also handles database errors and reports a missing search result as `Student not found.`

## Test results

The test suite checks the required valid student (ID 6, Karan), search and missing-record behavior, duplicate ID messaging and rollback, Python validation, direct database constraint enforcement, and migration of a Task 1 database. Run the command above to see the results in your environment.

## How Python communicates with SQL

Python's `sqlite3.connect()` opens the database and returns a connection. The connection executes SQL statements, with query results returned as rows. Python turns those rows back into `Student` objects, while `commit()` persists changes and `close()` releases the connection.

## Assignment questions

1. A Python object is an in-memory instance with attributes and methods. A database record is a row stored persistently in a table.
2. A list exists only while the program is running and is inconvenient to share or search as data grows. A database persists data and supports structured queries.
3. SQL is the language used to define, retrieve, and change data in relational databases.
4. `sqlite3.connect()` opens or creates a SQLite database and provides a connection for executing SQL.
5. `cursor.execute()` sends a SQL statement and its parameters to the database. In this project, the connection's `execute()` convenience method is used.
6. `commit()` completes the transaction and makes successful changes persistent.
7. A Python class defines the behavior and attributes of application objects. An SQL table defines the columns and stores rows of data.
8. Validation rejects incorrect values before they can become stored records, keeping the data consistent.

## SQL-PY-002 viva questions

1. A primary key uniquely identifies each row and cannot be duplicated or NULL.
2. `student_id` identifies one student, so a primary key prevents ambiguous duplicates.
3. No. The database rejects a duplicate primary key.
4. `NOT NULL` requires a value for a column; an empty string is still a value and is different from NULL.
5. `CHECK` accepts only rows whose values satisfy its expression.
6. Database constraints also protect records written by other programs or direct SQL, beyond this application's validation.
7. SQLite raises an integrity error, which the application reports as `Student ID already exists.`
8. NULL means no value is present; an empty string is a text value with zero characters.
9. `DEFAULT` supplies a value when an insert omits that column. It is an optional extension and is not included in this task's required schema.
10. Both: Python provides useful feedback, while database constraints enforce integrity for every writer.