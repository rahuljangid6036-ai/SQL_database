# University Student Management System

**Task ID:** SQL-PY-002

## Overview

A menu-driven student management application using Python and SQLite. Student data is validated in Python and protected by database constraints so invalid records are rejected even if they bypass the application.

## Project files

- `main.py` runs the application menu.
- `student.py` defines `Student` and validates input.
- `database.py` manages SQLite, schema creation, migration, inserts, and queries.
- `test_student_management.py` covers validation, constraints, duplicate IDs, search, and migration.
- `student_management.db` is created beside these files on first run.

## Database design

The `students` table uses this schema:

```sql
CREATE TABLE students (
    student_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    age INTEGER NOT NULL CHECK (age > 0),
    course TEXT NOT NULL,
    marks REAL NOT NULL CHECK (marks >= 0 AND marks <= 100)
);
```

The primary key prevents duplicate student IDs. `NOT NULL` protects required fields, and `CHECK` enforces valid age and marks ranges. The optional `status` default and course-list constraint are not included.

If the database contains the Task 1 table without constraints, startup migrates it in a transaction and preserves existing records. If existing data violates the new rules, the migration rolls back rather than discarding records.

## Run

From this folder, run:

```powershell
python main.py
```

Use the menu to add a student, view all students, search by ID, or exit. The database file persists records between runs.

Run tests with:

```powershell
python -m unittest -v
```

## Validation and database operations

The `Student` class rejects non-integer IDs, empty names or courses, ages less than or equal to zero, and marks outside 0-100. `Database.add_student()` uses a parameterized `INSERT`, commits successful writes, rolls back failed writes, and translates duplicate IDs to `Student ID already exists.` Other invalid database writes receive a clear constraint message.

`get_all_students()` retrieves the student records with `SELECT`. `get_student_by_id()` uses `SELECT ... WHERE student_id = ?`; a missing record is reported as `Student not found.` by the application. Python validation gives the user immediate feedback, while SQL constraints protect the stored data from every writer.

## SQL-PY-002 viva questions

1. A primary key uniquely identifies each row and cannot be duplicated or NULL.
2. `student_id` identifies one student, so a primary key prevents ambiguous duplicates.
3. No. The database rejects a duplicate primary key.
4. `NOT NULL` requires a value; an empty string is still a value and differs from NULL.
5. `CHECK` accepts only rows whose values satisfy its expression.
6. Database constraints also protect records written by other programs or direct SQL.
7. SQLite raises an integrity error, which the application reports as `Student ID already exists.`
8. NULL means no value is present; an empty string is text with zero characters.
9. `DEFAULT` supplies a value when an insert omits that column.
10. Both: Python gives user-friendly feedback, and the database enforces integrity for every writer.
