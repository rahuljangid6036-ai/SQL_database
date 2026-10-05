# University Student Management System

**Task ID:** SQL-PY-004

## Overview

A menu-driven Python and SQLite application that retains the SQL-PY-003 CRUD features and adds course/name searches, minimum-marks filtering, marks sorting, and top-N results. All user-supplied values in SQL statements are bound as parameters.

## Project files

- `main.py` provides the eleven-option menu, input validation, and CRUD flows.
- `student.py` defines student records and validates required fields and marks.
- `database.py` owns the schema, CRUD operations, and filtering/sorting queries.
- `test_student_management.py` covers CRUD, validation, filtering, sorting, top-N, AND/OR, and migration.
- `student_management.db` is created beside these files on first run.

## Database and safety

The `students` table retains its primary key, required fields, age check, and marks check. Startup migrates an unconstrained Task 1 table transactionally when necessary. Course, marks, keyword, and limit values use SQLite placeholders. The sort direction is selected from the fixed SQL keywords `ASC` or `DESC`, never from raw user input.

Key queries include:

```sql
SELECT * FROM students WHERE course = ?
SELECT * FROM students WHERE marks >= ?
SELECT * FROM students WHERE name LIKE ?
SELECT * FROM students WHERE course = ? AND marks >= ?
SELECT * FROM students WHERE course = ? OR course = ?
SELECT * FROM students ORDER BY marks DESC LIMIT ?
```

Name search binds a pattern created in Python as `f"%{keyword}%"`. Top-N binds its count using `cursor.execute(query, (limit,))`. Minimum marks must be between 0 and 100, and the top-N count must be a positive integer.

## Run and test

From this folder, run:

```powershell
python main.py
```

Run the automated tests with:

```powershell
python -m unittest -v
```

## Menu

1. Add Student
2. View All Students
3. Search Student by ID
4. Search Student by Course
5. Search Student by Name
6. Filter Students by Marks
7. Sort Students by Marks
8. Top N Students
9. Update Student
10. Delete Student
11. Exit

## Assignment questions

1. `WHERE` filters rows to those that meet a condition.
2. `AND` requires both conditions to be true; `OR` requires at least one.
3. `LIKE` compares text using a pattern and wildcard characters.
4. `%` matches any sequence of zero or more characters, allowing partial-name matches.
5. `ORDER BY` arranges the result rows using one or more columns.
6. `ASC` orders from low to high or A to Z; `DESC` orders from high to low or Z to A.
7. `LIMIT` caps the number of returned rows.
8. Use `SELECT * FROM students ORDER BY marks DESC LIMIT 5`.
9. Use `SELECT * FROM students WHERE marks > 80`.
10. Use `SELECT * FROM students WHERE name LIKE ?` and bind a pattern such as `%ri%`.
11. Without `ORDER BY`, the row order is unspecified and should not be relied upon.
12. Direct concatenation can allow SQL injection; placeholders keep data separate from SQL syntax.

## Viva questions

1. Use `SELECT * FROM students WHERE marks > ?` and bind `80`.
2. Sort by marks descending and limit the result to one row.
3. Use `LIKE` with a bound pattern such as `%name fragment%`.
4. `ASC` lists lower marks first; `DESC` lists higher marks first.
5. `LIMIT 5` returns at most five rows.
6. Yes. For example, `SELECT * FROM students WHERE course = ? ORDER BY marks DESC` filters first, then orders the matches.