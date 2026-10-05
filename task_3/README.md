# University Student Management System

**Task ID:** SQL-PY-003

## Overview

A menu-driven Python and SQLite application for creating, reading, searching, updating, and deleting student records. The database retains the Task 2 integrity constraints, while `Student.validate()` applies application-level validation to inserts and updates.

## Project files

- `main.py` provides the six-option CRUD menu and confirmation flow for deletion.
- `student.py` defines the student record and its validation rules.
- `database.py` manages the constrained SQLite table and CRUD queries.
- `test_student_management.py` covers validation, CRUD, `rowcount`, deletion confirmation, and migration.
- `student_management.db` is created beside these files on first run.

## Database and safety

The `students` table has `student_id INTEGER PRIMARY KEY`, required `name`, `age`, `course`, and `marks` fields, plus checks for `age > 0` and marks from 0 through 100. Startup migrates the unconstrained Task 1 table transactionally when needed and preserves valid records.

Updates use `UPDATE students SET name = ?, age = ?, course = ?, marks = ? WHERE student_id = ?`; the primary key is never changed. Deletion uses `DELETE FROM students WHERE student_id = ?`. Both methods return SQLite's `cursor.rowcount`, allowing the application to report success or `Student not found.` The application displays the selected record and asks for confirmation before deletion; any response other than `y` or `yes` cancels it.

## Run

From this folder, run:

```powershell
python main.py
```

Run automated tests with:

```powershell
python -m unittest -v
```

## CRUD mapping

- Create: `INSERT` through `Database.add_student()`.
- Read: `SELECT` through `get_all_students()` and `get_student_by_id()`.
- Update: validated student data through `UPDATE ... WHERE`.
- Delete: confirmed ID through `DELETE ... WHERE`.

## Assignment questions

1. CRUD stands for Create, Read, Update, and Delete.
2. `UPDATE` modifies existing records.
3. `DELETE` removes records.
4. `WHERE` restricts an update to the intended record.
5. `WHERE` restricts a deletion to the intended record.
6. An `UPDATE` without `WHERE` can change every row in the table.
7. A `DELETE` without `WHERE` can remove every row in the table.
8. `student_id` is the primary key used to identify a record, so it should remain stable.
9. `cursor.rowcount` reports how many rows were affected by a statement.
10. Validation prevents invalid data from reaching the update query and preserves database integrity.
11. Confirmation helps prevent accidental record loss.
12. `SELECT` reads and returns records; `DELETE` removes matching records.
