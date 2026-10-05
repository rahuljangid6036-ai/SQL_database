import sqlite3

from database import Database
from student import Student


def _read_integer(prompt):
    try:
        return int(input(prompt).strip())
    except ValueError as error:
        raise ValueError("Please enter a valid integer.") from error


def _read_marks(prompt):
    try:
        return float(input(prompt).strip())
    except ValueError as error:
        raise ValueError("Please enter a valid number for marks.") from error


def add_student(database):
    student_id = _read_integer("Student ID: ")
    name = input("Name: ")
    age = _read_integer("Age: ")
    course = input("Course: ")
    marks = _read_marks("Marks (0-100): ")

    student = Student(student_id, name, age, course, marks)
    database.add_student(student)
    print("Student added successfully.")


def show_all_students(database):
    students = database.get_all_students()
    if not students:
        print("No students found.")
        return

    for student in students:
        print(student)


def search_student(database):
    student_id = _read_integer("Student ID to search: ")
    student = database.get_student_by_id(student_id)
    if student is None:
        print("Student not found.")
    else:
        print(student)


def update_student(database):
    student_id = _read_integer("Student ID to update: ")
    current = database.get_student_by_id(student_id)
    if current is None:
        print("Student not found.")
        return

    print(f"Current record: {current}")
    print("Press Enter to keep the current value.")
    name = input(f"Name [{current.name}]: ").strip() or current.name
    age_text = input(f"Age [{current.age}]: ").strip()
    course = input(f"Course [{current.course}]: ").strip() or current.course
    marks_text = input(f"Marks [{current.marks:g}]: ").strip()

    age = int(age_text) if age_text else current.age
    marks = float(marks_text) if marks_text else current.marks
    updated = Student(current.student_id, name, age, course, marks)
    if database.update_student(updated):
        print("Student updated successfully.")
    else:
        print("Student not found.")


def delete_student(database):
    student_id = _read_integer("Student ID to delete: ")
    student = database.get_student_by_id(student_id)
    if student is None:
        print("Student not found.")
        return

    print(f"Student to delete: {student}")
    confirmation = input("Delete this student? (y/n): ").strip().casefold()
    if confirmation not in ("y", "yes"):
        print("Deletion cancelled.")
        return

    if database.delete_student(student_id):
        print("Student deleted successfully.")
    else:
        print("Student not found.")


def run_application(database):
    while True:
        print("\nUniversity Student Management System")
        print("1. Add Student")
        print("2. View All Students")
        print("3. Search Student")
        print("4. Update Student")
        print("5. Delete Student")
        print("6. Exit")
        choice = input("Choose an option: ").strip()

        actions = {
            "1": add_student,
            "2": show_all_students,
            "3": search_student,
            "4": update_student,
            "5": delete_student,
        }
        if choice == "6":
            print("Goodbye.")
            return
        action = actions.get(choice)
        if action is None:
            print("Invalid option. Choose 1, 2, 3, 4, 5, or 6.")
            continue

        try:
            action(database)
        except ValueError as error:
            print(error)


def main():
    database = Database()
    try:
        database.connect()
        database.create_table()
        run_application(database)
    except sqlite3.Error as error:
        print(f"Database error: {error}")
    finally:
        database.close()


if __name__ == "__main__":
    main()
