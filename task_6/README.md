# University Student Management System

**Task ID:** SQL-PY-007

## Overview

This Python and SQLite application extends SQL-PY-006 with atomic course transfers. Each student stores a `course_id` foreign key, and every successful transfer updates the student and adds a history row in the same transaction.

## Project files

- `main.py` provides the 17-option course, student, transaction, filtering, sorting, and analytics menu.
- `database.py` manages courses, students, transfer history, transaction boundaries, course CRUD, and JOIN queries.
- `student.py` validates students using `course_id` instead of a repeated course name.
- `course.py` defines and validates course records.
- `test_student_management.py` covers foreign keys, CRUD, joins, analytics, schema migration, successful transfers, validation, and rollback after a simulated failure.
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

## Transactions and ACID

`student_course_history` records the student, old course, new course, and transfer timestamp. `transfer_student_course()` validates the IDs and same-course case before opening a transaction. It then updates the student and inserts history; either both commit, or an exception rolls back both operations. The history foreign keys keep student and course references valid.

The database API also exposes `begin_transaction()`, `commit()`, and `rollback()` for learning and controlled multi-statement work. The menu's transfer option uses the atomic operation; the history option displays all transfers or filters by student ID.

- **Atomicity:** the student update and history insert succeed or are both undone.
- **Consistency:** foreign keys and table constraints maintain valid student/course references.
- **Isolation:** SQLite transactions prevent another connection from observing a partially completed transfer.
- **Durability:** a committed transfer and its history remain stored after the connection closes.

Test the rollback path with:

```powershell
python -m unittest -v
```

The test suite installs a temporary SQLite trigger that deliberately rejects a history insert after the student update. It verifies that Rahul remains in BCA and no history row is created.

```sql
UPDATE students SET course_id = ? WHERE student_id = ?;

INSERT INTO student_course_history
    (student_id, old_course_id, new_course_id)
VALUES (?, ?, ?);

SELECT s.name, old_course.course_name AS old_course,
       new_course.course_name AS new_course, h.changed_at
FROM student_course_history AS h
JOIN students AS s ON s.student_id = h.student_id
JOIN courses AS old_course ON old_course.course_id = h.old_course_id
JOIN courses AS new_course ON new_course.course_id = h.new_course_id
ORDER BY h.history_id;
```

## Assignment questions

1. A transaction groups one or more database statements into a unit of work.
2. `COMMIT` permanently saves the transaction's changes.
3. `ROLLBACK` cancels uncommitted changes.
4. Transactions prevent partial updates when related operations must succeed together.
5. In a course transfer, the student update and history insert must both happen or neither should.
6. ACID means Atomicity, Consistency, Isolation, and Durability.
7. An exception before commit causes `transfer_student_course()` to roll back before re-raising the error.
8. A partial update is when only some operations in a logically related group take effect.
9. Validation before the transaction avoids opening a transaction for invalid input and reduces unnecessary locking.
10. `commit()` saves changes; `rollback()` undoes uncommitted changes.
11. `UPDATE students SET course_id = ? WHERE student_id = ?;`
12. `INSERT INTO student_course_history (student_id, old_course_id, new_course_id) VALUES (?, ?, ?);`
13. Join `student_course_history` to students and both course aliases; see the query above.
14. The query above returns the student name, old course, new course, and transfer timestamp.

## Viva questions

1. Transactions prevent partial updates by treating related SQL statements as one unit.
2. `COMMIT` makes the transaction's changes permanent.
3. `ROLLBACK` cancels changes that have not been committed.
4. A bank transfer is a real-world example; a student course transfer is this project's example.
5. ACID stands for Atomicity, Consistency, Isolation, Durability.
6. Atomicity means all operations succeed or none do.