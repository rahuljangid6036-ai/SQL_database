# Student Management System: Transactions and ACID

**Task ID:** SQL-PY-007

## Overview

This project continues the relational student database from SQL-PY-006. Student
course transfers update the student's course and write a transfer-history row
as one transaction. If either database operation fails, SQLite rolls both back.

## Files

- `main.py` provides the 17-option menu.
- `database.py` creates the course, student, and course-history tables and
  implements the relational queries and transaction methods.
- `student.py` and `course.py` define validated records.
- `test_student_management.py` checks successful transfers, invalid input,
  transaction controls, and a simulated history-insert failure.
- `student_management.db` is created alongside the source files when run.

## Run and test

From this directory:

```powershell
python main.py
python -m unittest -v
```

Add courses before students. For the transfer example, create BCA with course
ID `1` and MCA with course ID `3`, then add Rahul with student ID `5` to BCA.
Choose **15. Transfer Student Course** and enter `5` and `3`.

## Transaction boundary

The transfer checks identifier types before starting, then obtains a write
transaction and checks the student and destination course before making any
change. Both SQL statements must finish before commit:

```sql
UPDATE students
SET course_id = ?
WHERE student_id = ?;

INSERT INTO student_course_history
    (student_id, old_course_id, new_course_id)
VALUES (?, ?, ?);
```

`transfer_student_course()` commits only after both statements succeed. Any
exception triggers rollback and is re-raised for the menu or caller to report.
Its checks inside the transaction also prevent the current course from
changing between validation and update. The public `begin_transaction()`,
`commit()`, and `rollback()` methods are available for other grouped operations.

The history view joins students and both course records, showing the student's
name, old and new course names, and timestamp. Course and student records
referenced by transfer history cannot be deleted, preserving the audit trail.
The general student update method also records course changes in the same
transaction as the other edited fields.

## ACID

- **Atomicity:** A transfer and its history insert both persist, or neither
  does. The rollback test forces the history insert to fail after the student
  update and verifies that Rahul remains in BCA.
- **Consistency:** Foreign keys and `CHECK` constraints protect valid student,
  course, and marks data before and after each transaction.
- **Isolation:** SQLite serializes writers; `BEGIN IMMEDIATE` reserves the write
  transaction while the transfer's validation and writes are performed.
- **Durability:** After `COMMIT` returns successfully, SQLite saves the
  transaction. The committed transfer can be read back from the database.

## Assignment questions

1. A database transaction is a group of database operations treated as one
   unit of work.
2. `COMMIT` saves the current transaction's changes.
3. `ROLLBACK` discards changes made in the uncommitted transaction.
4. Transactions protect related operations from leaving partially updated data.
5. During a course transfer, the student's course and the history entry must
   both change, or neither should change.
6. Atomicity is all-or-nothing behavior; consistency preserves database rules;
   isolation prevents conflicting transactions from seeing partial work; and
   durability means committed changes persist.
7. If an exception occurs before commit, the application should roll back the
   transaction; the transfer method does so and then re-raises the exception.
8. A partial update occurs when only some operations in a related set are saved.
9. Validate input before the transaction to avoid opening a write transaction
   for malformed values. Existence and current-state checks belong inside the
   transaction when they must remain true through the update.
10. `COMMIT` saves uncommitted changes; `ROLLBACK` discards them.
11. `UPDATE students SET course_id = ? WHERE student_id = ?;`
12. `INSERT INTO student_course_history (student_id, old_course_id,
    new_course_id) VALUES (?, ?, ?);`
13. `SELECT * FROM student_course_history ORDER BY history_id;`
14. Join history to students and join courses twice, once for each course ID:

```sql
SELECT s.name, old_course.course_name AS old_course,
       new_course.course_name AS new_course, h.changed_at
FROM student_course_history AS h
JOIN students AS s ON s.student_id = h.student_id
JOIN courses AS old_course ON old_course.course_id = h.old_course_id
JOIN courses AS new_course ON new_course.course_id = h.new_course_id
ORDER BY h.history_id;
```

## Viva questions

- **What problem does a transaction solve?** It treats related database
  operations as one unit and prevents partial updates.
- **What happens when COMMIT executes?** The transaction's changes are saved.
- **What does ROLLBACK do?** It cancels uncommitted transaction changes.
- **Give a real-world example.** A bank transfer that debits one account and
  credits another as a single unit.
- **What does ACID stand for?** Atomicity, Consistency, Isolation, Durability.
- **Which property means “all or nothing”?** Atomicity.
