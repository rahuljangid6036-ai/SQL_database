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


def _read_minimum_marks(prompt):
    marks = _read_marks(prompt)
    if not 0 <= marks <= 100:
        raise ValueError("Invalid marks.")
    return marks


def _read_top_count(prompt):
    limit = _read_integer(prompt)
    if limit <= 0:
        raise ValueError("Number of students must be greater than 0.")
    return limit


def _show_students(students):
    if not students:
        print("No students found.")
        return

    for student in students:
        print(student)


def add_student(database):
    student_id = _read_integer("Student ID: ")
    name = input("Name: ")
    age = _read_integer("Age: ")
    course = input("Course: ")
    marks = _read_marks("Marks (0-100): ")

    database.add_student(Student(student_id, name, age, course, marks))
    print("Student added successfully.")


def show_all_students(database):
    _show_students(database.get_all_students())


def search_student(database):
    student_id = _read_integer("Student ID to search: ")
    student = database.get_student_by_id(student_id)
    if student is None:
        print("Student not found.")
    else:
        print(student)


def search_students_by_course(database):
    course = input("Course to search: ").strip()
    _show_students(database.get_students_by_course(course))


def search_students_by_name(database):
    keyword = input("Name keyword to search: ").strip()
    _show_students(database.search_students_by_name(keyword))


def filter_students_by_marks(database):
    min_marks = _read_minimum_marks("Minimum marks (0-100): ")
    _show_students(database.get_students_by_marks(min_marks))


def sort_students_by_marks(database):
    print("1. Highest marks first")
    print("2. Lowest marks first")
    choice = input("Choose sort order: ").strip()
    if choice not in ("1", "2"):
        raise ValueError("Invalid sort order. Choose 1 or 2.")

    _show_students(database.get_students_sorted_by_marks(desc=choice == "1"))


def show_top_students(database):
    limit = _read_top_count("Number of top students: ")
    _show_students(database.get_top_students(limit))


def show_student_statistics(database):
    total_students = database.get_total_students()
    total_marks = database.get_total_marks()
    average_marks = database.get_average_marks()
    highest_marks = database.get_highest_marks()
    lowest_marks = database.get_lowest_marks()

    print(f"Total Students      : {total_students}")
    print(f"Total Marks         : {total_marks if total_marks is not None else 0:g}")
    average_display = f"{average_marks:.2f}" if average_marks is not None else "N/A"
    highest_display = f"{highest_marks:g}" if highest_marks is not None else "N/A"
    lowest_display = f"{lowest_marks:g}" if lowest_marks is not None else "N/A"
    print(f"Average Marks       : {average_display}")
    print(f"Highest Marks       : {highest_display}")
    print(f"Lowest Marks        : {lowest_display}")


def _read_minimum_average(prompt):
    value = input(prompt).strip()
    if not value:
        return 80.0

    try:
        minimum_average = float(value)
    except ValueError as error:
        raise ValueError("Please enter a valid number for the minimum average.") from error
    if not 0 <= minimum_average <= 100:
        raise ValueError("Minimum average must be between 0 and 100.")
    return minimum_average


def show_course_statistics(database):
    statistics = database.get_course_statistics()
    if not statistics:
        print("No course statistics found.")
    else:
        print(f"{'Course':<12}{'Students':>10}{'Average':>12}{'Highest':>12}{'Lowest':>10}")
        print("--------------------------------------------------------------")
        for course, total_students, average, highest, lowest in statistics:
            print(f"{course:<12}{total_students:>10}{average:>12.2f}{highest:>12g}{lowest:>10g}")

    minimum_average = _read_minimum_average(
        "Minimum course average for HAVING (0-100, Enter for 80): "
    )
    qualifying_courses = database.get_courses_above_average(minimum_average)
    print(f"Courses with average marks >= {minimum_average:g}:")
    if not qualifying_courses:
        print("No courses meet this average.")
        return

    for course, average in qualifying_courses:
        print(f"{course}: {average:.2f}")


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
        print("3. Search Student by ID")
        print("4. Search Student by Course")
        print("5. Search Student by Name")
        print("6. Filter Students by Marks")
        print("7. Sort Students by Marks")
        print("8. Top N Students")
        print("9. Update Student")
        print("10. Delete Student")
        print("11. Student Statistics")
        print("12. Course-wise Statistics")
        print("13. Exit")
        choice = input("Choose an option: ").strip()

        actions = {
            "1": add_student,
            "2": show_all_students,
            "3": search_student,
            "4": search_students_by_course,
            "5": search_students_by_name,
            "6": filter_students_by_marks,
            "7": sort_students_by_marks,
            "8": show_top_students,
            "9": update_student,
            "10": delete_student,
            "11": show_student_statistics,
            "12": show_course_statistics,
        }
        if choice == "13":
            print("Goodbye.")
            return
        action = actions.get(choice)
        if action is None:
            print("Invalid option. Choose a number from 1 to 13.")
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