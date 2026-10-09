# Student Management System: PostgreSQL Integration

**Task ID:** SQL-PY-008

This continues SQL-PY-007, replacing SQLite with PostgreSQL while preserving
course relationships, JOINs, CRUD, grouped statistics, and atomic course
transfers with history.

## Project files

- `main.py` contains the console application and CRUD/transfer menu.
- `database.py` owns the psycopg connection, parameterized SQL, CRUD, joins,
  transaction boundaries, and course history.
- `config.py` loads credentials from process environment variables and the
  local `.env` file.
- `student.py` and `course.py` validate application records.
- `requirements.txt` declares psycopg 3 with its binary package.
- `.env.example` shows configuration keys. Copy it to `.env` and enter your
  local password; `.env` is ignored by Git.
- `test_student_management.py` tests query construction, configuration, and
  transfer commit/rollback using an in-memory fake connection. The README also
  documents the live PostgreSQL acceptance checks.

## PostgreSQL setup

Install PostgreSQL and create the database using `createdb student_management`
or from `psql`:

```sql
CREATE DATABASE student_management;
```

In PowerShell, from this directory:

```powershell
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` with the connection values for your local PostgreSQL installation:

```dotenv
DB_HOST=localhost
DB_PORT=5432
DB_NAME=student_management
DB_USER=postgres
DB_PASSWORD=your_local_password
```

Never commit `.env` or place a real password in Python source. Process
environment variables take precedence over values in `.env`. `main.py`
creates the three required tables and reports a concise message when the server
is unavailable or authentication fails.

Run:

```powershell
python main.py
python -m unittest -v
```

PostgreSQL course IDs are generated with `SERIAL` when the course ID prompt is
left empty; an explicit ID may also be entered for the earlier project data.
Add courses before adding students. To demonstrate a transfer, create BCA and
MCA, add a student to BCA, then choose **15. Transfer Student Course**. Option
16 displays all transfer history or history for a selected student.

## Connection and query behavior

The `Database` object owns one psycopg connection. Connection settings are
passed to `psycopg.connect`; SQL values use psycopg `%s` placeholders and are
always supplied separately. Search patterns use PostgreSQL `ILIKE`. The
student-course history query joins the student and both course records.

Transfers run `BEGIN`, lock the student row with `FOR UPDATE`, update the
course, insert history, then `COMMIT`. Errors roll back both writes and are
re-raised to the application layer. The general student update uses the same
atomic history behavior if the course changes. PostgreSQL `NUMERIC(5,2)`
results are converted to normal application `float` values by the `Student`
model for display.

## Live PostgreSQL acceptance checks

After setting up PostgreSQL and `.env`, verify the application startup message,
then add four courses and five students using the menu. Test viewing joined
students, searching, updating, and deleting a disposable student. Transfer
Rahul from BCA to MCA, then inspect option 16 for the old/new course and date.
For a live rollback check, create a temporary PostgreSQL trigger that raises
an exception before history insertion, attempt a transfer, and verify the
student still has the original course with no new history row. Remove the
trigger afterward. Restart the application and confirm committed records remain.

The automated tests run without a PostgreSQL server. They verify generated
PostgreSQL DDL, parameter binding, environment configuration, successful
transfer, invalid transfer handling, and rollback after a simulated history
insert failure. Live connection and durability checks require a running server.

## Assignment questions

1. PostgreSQL is an open-source object-relational database management system.
2. SQLite is an embedded database stored in a local file; PostgreSQL is a
   separate server process supporting concurrent network clients.
3. A database server accepts client connections and executes database work.
4. A database client is an application or tool that connects to the server.
5. A PostgreSQL connection is a session between a client and the server,
   identified by host, port, database, and credentials.
6. A cursor executes SQL and retrieves query results.
7. Hard-coded credentials can be exposed in source control, logs, or shared
   code; environment configuration keeps secrets out of source.
8. An environment variable is a named value supplied to a process by its
   operating environment.
9. Parameterized queries send values separately from SQL syntax, avoiding
   injection and handling values safely.
10. SQL injection is an attack in which untrusted input changes the meaning of
    a SQL statement.
11. `VARCHAR(n)` stores text up to a specified length; `NUMERIC(p,s)` stores
    exact decimal values with precision `p` and scale `s`.
12. A foreign key references another table's key and enforces valid
    relationships between rows.
13. `SERIAL` supplies an integer value from a sequence when a row is inserted.
14. Connection handling reports unavailable-server and authentication failures
    clearly, without printing credentials or an uncontrolled traceback.
15. `CREATE TABLE courses (course_id SERIAL PRIMARY KEY, course_name
    VARCHAR(100) NOT NULL UNIQUE);`
16. `INSERT INTO students (student_id, name, age, course_id, marks) VALUES
    (%s, %s, %s, %s, %s);`
17. `UPDATE students SET marks = %s WHERE student_id = %s;`
18. `DELETE FROM students WHERE student_id = %s;`
19. `SELECT s.student_id, s.name, c.course_name, s.marks FROM students AS s
    INNER JOIN courses AS c ON s.course_id = c.course_id;`
20. `SELECT student_id, name, marks FROM students ORDER BY marks DESC LIMIT 3;`

## Viva questions

- **Why move from SQLite to PostgreSQL?** PostgreSQL is a production-grade
  client-server database built for concurrent and networked applications.
- **Does PostgreSQL replace Python?** No. Python is the application layer;
  PostgreSQL stores and manages relational data.
- **What connects Python to PostgreSQL?** A driver such as psycopg.
- **Why not put the password in `database.py`?** Source code may be shared or
  committed, exposing the secret.
- **What is SQL injection?** Malicious input altering the intended SQL.
- **What does a foreign key do?** It maintains valid references between tables.
- **What happens when PostgreSQL is stopped?** New connections fail until the
  server becomes available again.
