# University Student Management System

**Task ID:** SQL-PY-006

## Overview

This Python and SQLite application extends SQL-PY-005 with normalized `courses` and `students` tables. Each student stores a `course_id` foreign key, so one course can be related to many students while course names remain in one place.

## Project files

- `main.py` provides the 15-option course, student, filtering, sorting, and analytics menu.
- `database.py` manages both tables, prior student functionality, course CRUD, and JOIN queries.
- `student.py` validates students using `course_id` instead of a repeated course name.
- `course.py` defines and validates course records.
- `test_student_management.py` covers foreign keys, CRUD, joins, analytics, and schema migration.
- `student_management.db` is created beside these files on first run.

## Run and test

From this folder:

```powershell
python main.py
python -m unittest -v
```

Create courses from the menu before adding students. The sample IDs are BCA=1, BBA=2, MCA=3, and MBA=4. SQL-PY-005 databases with course names in `students.course` are migrated at startup; course rows are created from the existing names and student records are preserved.

## Relationship and integrity

`courses.course_id` is the primary key. `students.course_id` is a foreign key referencing it. The connection enables SQLite foreign-key enforcement, and the application also checks a selected course before inserting a student. Courses with students cannot be deleted; the database rejects that deletion to preserve referential integrity.

The relationship is one-to-many: one course can be related to multiple students. `get_students_with_courses()` uses an INNER JOIN. Course statistics and courses without students use LEFT JOIN so courses with no matching student are retained.

```sql
SELECT s.student_id, s.name, c.course_name, s.marks
FROM students AS s
INNER JOIN courses AS c ON s.course_id = c.course_id;

SELECT c.course_name, COUNT(s.student_id) AS total_students,
       AVG(s.marks) AS average_marks, MAX(s.marks) AS highest_marks,
       MIN(s.marks) AS lowest_marks
FROM courses AS c
LEFT JOIN students AS s ON c.course_id = s.course_id
GROUP BY c.course_id, c.course_name;

SELECT c.course_name
FROM courses AS c
LEFT JOIN students AS s ON c.course_id = s.course_id
WHERE s.student_id IS NULL;
```

## Assignment questions

1. A foreign key references a key in another table and enforces a valid relationship.
2. A primary key uniquely identifies each row in its table.
3. A relationship connects rows in different tables using related key values.
4. One course can be referenced by many student rows; each student references one course.
5. A separate courses table avoids repeating course data and keeps names consistent.
6. Normalization organizes data into related tables to reduce duplication and update anomalies.
7. `INNER JOIN` returns rows with a match in both tables.
8. `LEFT JOIN` returns all left-table rows and matching right-table rows, using NULL where there is no match.
9. `INNER JOIN` drops unmatched rows; `LEFT JOIN` preserves every row from the left table.
10. `ON` specifies how the rows in the two tables are related.
11. Aliases shorten table references and make multi-table queries easier to read.
12. The foreign key rejects the student insert; the application reports `Invalid course ID.`
13. A LEFT JOIN produces NULL columns for a left-side row without a matching right-side row.
14. LEFT JOIN courses to students and filter with `WHERE s.student_id IS NULL`.
15. Yes. JOIN combines related rows, then GROUP BY forms groups for aggregate calculations.

## Viva questions

1. A foreign key points to a key in another table and prevents invalid references.
2. An INNER JOIN returns only rows with matching keys in both tables.
3. A LEFT JOIN keeps all rows from its left table, including unmatched rows.
4. LEFT JOIN students and filter on `s.student_id IS NULL`.
5. A separate courses table reduces repeated data and helps maintain consistent course names.
6. It is a one-to-many relationship: one course can have multiple students.

```sql
SELECT c.course_name
FROM courses AS c
LEFT JOIN students AS s ON c.course_id = s.course_id
WHERE s.student_id IS NULL;
```