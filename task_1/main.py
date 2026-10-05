import sqlite3

from database import Database
from student import Student


def add_student(database):
    student_id = int(input("Student ID: ").strip())
    name = input("Name: ")
    age = int(input("Age: ").strip())
    course = input("Course: ")
    marks = float(input("Marks (0-100): ").strip())

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
    student_id = int(input("Student ID to search: ").strip())
    student = database.get_student_by_id(student_id)
    if student is None:
        print("Student not found.")
    else:
        print(student)


def run_application(database):
    while True:
        print("\nUniversity Student Management System")
        print("1. Add student")
        print("2. View all students")
        print("3. Search by student ID")
        print("4. Exit")
        choice = input("Choose an option: ").strip()

        if choice == "1":
            try:
                add_student(database)
            except ValueError as error:
                print(error)
        elif choice == "2":
            show_all_students(database)
        elif choice == "3":
            try:
                search_student(database)
            except ValueError:
                print("Validation error: Student ID must be an integer.")
        elif choice == "4":
            print("Goodbye.")
            return
        else:
            print("Invalid option. Choose 1, 2, 3, or 4.")


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