import sqlite3

from course import Course
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


def add_course(database):
    course_id = _read_integer("Course ID: ")
    course_name = input("Course name: ")
    database.add_course(Course(course_id, course_name))
    print("Course added successfully.")


def show_courses(database):
    courses = database.get_all_courses()
    if not courses:
        print("No courses found.")
        return

    for course in courses:
        print(course)


def add_student(database):
    student_id = _read_integer("Student ID: ")
    name = input("Name: ")
    age = _read_integer("Age: ")
    course_id = _read_integer("Course ID: ")
    if database.get_course_by_id(course_id) is None:
        print("Invalid course ID.")
        return

    marks = _read_marks("Marks (0-100): ")
    database.add_student(Student(student_id, name, age, course_id, marks))
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
    course_name = input("Course name to search: ").strip()
    _show_students(database.get_students_by_course(course_name))


def search_students_by_marks(database):
    min_marks = _read_minimum_marks("Minimum marks (0-100): ")
    _show_students(database.get_students_by_marks(min_marks))


def sort_students(database):
    print("1. Highest marks first")
    print("2. Lowest marks first")
    choice = input("Choose sort order: ").strip()
    if choice not in ("1", "2"):
        raise ValueError("Invalid sort order. Choose 1 or 2.")

    _show_students(database.get_students_sorted_by_marks(desc=choice == "1"))


def show_top_students(database):
    limit = _read_top_count("Number of top students: ")
    _show_students(database.get_top_students(limit))


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
    course_text = input(f"Course ID [{current.course_id}]: ").strip()
    marks_text = input(f"Marks [{current.marks:g}]: ").strip()

    age = int(age_text) if age_text else current.age
    course_id = int(course_text) if course_text else current.course_id
    marks = float(marks_text) if marks_text else current.marks
    updated = Student(current.student_id, name, age, course_id, marks)
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


def show_course_statistics(database):
    statistics = database.get_course_statistics()
    if not statistics:
        print("No course statistics found.")
        return

    print(f"{'Course':<12}{'Students':>10}{'Average':>12}{'Highest':>12}{'Lowest':>10}")
    print("--------------------------------------------------------------")
    for course_name, total_students, average, highest, lowest in statistics:
        average_display = f"{average:.2f}" if average is not None else "N/A"
        highest_display = f"{highest:g}" if highest is not None else "N/A"
        lowest_display = f"{lowest:g}" if lowest is not None else "N/A"
        print(
            f"{course_name:<12}{total_students:>10}{average_display:>12}"
            f"{highest_display:>12}{lowest_display:>10}"
        )


def show_courses_without_students(database):
    courses = database.get_courses_without_students()
    if not courses:
        print("Every course has at least one student.")
        return

    print("Courses without students:")
    for course in courses:
        print(course.course_name)


def run_application(database):
    while True:
        print("\nUniversity Student Management System")
        print("1. Add Course")
        print("2. View Courses")
        print("3. Add Student")
        print("4. View All Students")
        print("5. Search Student")
        print("6. Search Students by Course")
        print("7. Search Students by Marks")
        print("8. Sort Students")
        print("9. Top N Students")
        print("10. Update Student")
        print("11. Delete Student")
        print("12. Student Statistics")
        print("13. Course-wise Statistics")
        print("14. Courses Without Students")
        print("15. Exit")
        choice = input("Choose an option: ").strip()

        actions = {
            "1": add_course,
            "2": show_courses,
            "3": add_student,
            "4": show_all_students,
            "5": search_student,
            "6": search_students_by_course,
            "7": search_students_by_marks,
            "8": sort_students,
            "9": show_top_students,
            "10": update_student,
            "11": delete_student,
            "12": show_student_statistics,
            "13": show_course_statistics,
            "14": show_courses_without_students,
        }
        if choice == "15":
            print("Goodbye.")
            return
        action = actions.get(choice)
        if action is None:
            print("Invalid option. Choose a number from 1 to 15.")
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