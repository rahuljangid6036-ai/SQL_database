# University Student Management System

**Task ID:** SQL-PY-005

## Overview

This Python and SQLite application extends SQL-PY-004 with student-wide and course-wise performance analytics. SQL performs all COUNT, SUM, AVG, MIN, MAX, GROUP BY, and HAVING calculations; Python formats the returned aggregate rows for display.

## Project files

- `main.py` provides the 13-option CRUD, filtering, and analytics menu.
- `student.py` defines student records and their validation rules.
- `database.py` contains the schema, prior CRUD/filtering methods, and analytics queries.
- `test_student_management.py` covers CRUD preservation, analytics, HAVING, empty databases, and migration.
- `student_management.db` is created beside these files on first run.

## Run and test

From this folder:

```powershell
python main.py
python -m unittest -v
```

## Analytics queries

Student-level methods each use a SQL aggregate, for example:

```sql
SELECT COUNT(*) FROM students;
SELECT SUM(marks) FROM students;
SELECT AVG(marks) FROM students;
SELECT MAX(marks) FROM students;
SELECT MIN(marks) FROM students;
```

Course statistics use one grouped query:

```sql
SELECT course, COUNT(*) AS total_students, AVG(marks) AS average_marks,
       MAX(marks) AS highest_marks, MIN(marks) AS lowest_marks
FROM students
GROUP BY course;
```

`get_course_average_marks_for_minimum_marks()` demonstrates `WHERE` filtering rows before grouping. `get_courses_above_average(min_average)` binds the threshold and uses `HAVING AVG(marks) >= ?` to filter groups. The application defaults the HAVING screen to 80 when its prompt is left blank.

For an empty table, `COUNT(*)` returns 0. SQLite returns `NULL` for `SUM`, `AVG`, `MIN`, and `MAX`; the database methods preserve that result, while the menu displays zero for the total and `N/A` for undefined statistics.

## Assignment questions

1. An aggregate function calculates one result from multiple rows.
2. `COUNT()` counts rows or non-NULL values, depending on its argument; `COUNT(*)` counts rows.
3. `SUM()` adds the values in a column.
4. `AVG()` calculates the arithmetic mean of non-NULL values.
5. `MIN()` returns the smallest value.
6. `MAX()` returns the largest value.
7. `GROUP BY` partitions matching rows into groups that share column values.
8. We use it to calculate aggregates separately for each group, such as each course.
9. `WHERE` filters rows before aggregation; `HAVING` filters groups after aggregation.
10. Yes. `WHERE` selects rows, then `GROUP BY` aggregates the remaining rows.
11. Yes, for an aggregate query without groups, `HAVING` can filter the single aggregate result; `WHERE` is usually used for row filtering.
12. Database aggregation avoids transferring every record and is more efficient for large datasets.
13. `AVG()` returns `NULL` when there are no non-NULL marks; on an empty table this is displayed as `N/A`.
14. An alias gives an expression a readable result-column name, such as `average_marks`.
15. One combined query scans/groups the data once and returns count, average, highest, and lowest values together.

## Viva questions

1. `SELECT COUNT(*) FROM students;`
2. `SELECT AVG(marks) FROM students;`
3. `SELECT MAX(marks) FROM students;`
4. `SELECT course, COUNT(*) FROM students GROUP BY course;`
5. `WHERE` filters individual rows; `HAVING` filters grouped aggregate results.
6. `GROUP BY` forms the groups for per-course aggregate calculations.
7. `SELECT course, AVG(marks) FROM students GROUP BY course HAVING AVG(marks) > 80;`