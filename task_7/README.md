# University Student Management System

**Task ID:** SQL-PY-007

## Overview

This task extends SQL-PY-006 with an auditable course-transfer transaction. A transfer updates `students.course_id` and inserts a `student_course_history` row as one unit: both changes commit together or both roll back.

## Project files

- `main.py` preserves the course/student and analytics menu and adds transfer/history options.
- `database.py` manages prior queries and the transaction boundary for course transfers.
- `student.py` and `course.py` retain the SQL-PY-006 data models.
- `test_student_management.py` covers successful commits, validation, explicit rollback, and forced failure atomicity.
- `student_management.db` is created beside these files on first run.

## Run and test

From this folder:

```powershell
python main.py
python -m unittest -v
```

Add courses and students first, then choose **15. Transfer Student Course**. A valid transfer records its previous course, new course, and timestamp. Option 16 displays the complete transfer history. Ordinary student updates do not change the course; course changes must use the transfer operation so they cannot bypass the audit history.

## Transaction behavior

`transfer_student_course()` validates the student and destination course before opening a transaction. It then rechecks them, executes the student UPDATE and history INSERT, and commits. Any exception during those writes causes a rollback and is re-raised to the menu for reporting. The history table has foreign keys to the student and both courses, and referenced students/courses cannot be deleted while history rows refer to them.

```sql
BEGIN;
UPDATE students SET course_id = ? WHERE student_id = ?;
INSERT INTO student_course_history
    (student_id, old_course_id, new_course_id)
VALUES (?, ?, ?);
COMMIT;
```

On failure, `ROLLBACK` restores the original student course and removes the uncommitted history row. The test suite uses a SQLite trigger to deliberately fail the history INSERT after the UPDATE and checks that neither change persists.

## ACID properties

- **Atomicity:** all transfer writes commit together, or none do.
- **Consistency:** primary keys, checks, and foreign keys keep every committed state valid.
- **Isolation:** SQLite transactions keep uncommitted changes from being treated as committed data by other connections.
- **Durability:** after COMMIT completes, the database retains the changes.

## Assignment questions

1. A transaction groups related database operations into a single unit of work.
2. `COMMIT` permanently saves the current transaction's changes.
3. `ROLLBACK` cancels uncommitted changes in the current transaction.
4. Transactions prevent partial writes when several operations must succeed together.
5. For a course transfer, the student's new course and the history row must both be written, or neither should be.
6. Atomicity is all-or-nothing; consistency preserves constraints; isolation separates concurrent transactions; durability preserves committed changes.
7. If an exception occurs before commit, code should roll back the transaction so its partial changes are discarded.
8. A partial update occurs when only some operations in a logically single action persist.
9. Validating first rejects bad input before taking locks or making writes; values are rechecked inside the transaction to guard against changes between validation and execution.
10. `commit()` saves the transaction; `rollback()` undoes its uncommitted writes.
11. `UPDATE students SET course_id = ? WHERE student_id = ?;`
12. `INSERT INTO student_course_history (student_id, old_course_id, new_course_id) VALUES (?, ?, ?);`
13. `SELECT * FROM student_course_history ORDER BY history_id;`
14. Join history to students, old courses, and new courses, selecting student name, both course names, and `changed_at`.

## Viva questions

- A transaction prevents partial results when multiple related operations must succeed together.
- `COMMIT` makes the current transaction permanent; `ROLLBACK` cancels its uncommitted work.
- A bank transfer is a common example: debit and credit must both occur.
- ACID means Atomicity, Consistency, Isolation, and Durability. “All or nothing” describes Atomicity.