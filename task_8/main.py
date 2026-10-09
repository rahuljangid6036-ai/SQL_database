from config import ConfigurationError
from course import Course
from database import Database, DatabaseConnectionError, DatabaseDependencyError
from student import Student


def _is_postgres_error(error):
    return type(error).__module__.startswith("psycopg")


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


def _show_students(students):
    if not students:
        print("No students found.")
        return
    for student in students:
        print(student)


def add_course(database):
    name = input("Course name: ").strip()
    course_id = input("Course ID (Enter to assign automatically): ").strip()
    course = Course(int(course_id) if course_id else None, name)
    created_id = database.add_course(course)
    print(f"Course added successfully. Course ID: {created_id}")


def show_courses(database):
    courses = database.get_all_courses()
    if not courses:
        print("No courses found.")
        return
    print(f"{'Course ID':<12}Course Name")
    for course in courses:
        print(f"{course.course_id:<12}{course.course_name}")


def add_student(database):
    student_id = _read_integer("Student ID: ")
    name = input("Name: ")
    age = _read_integer("Age: ")
    course_id = _read_integer("Course ID: ")
    marks = _read_marks("Marks (0-100): ")
    database.add_student(Student(student_id, name, age, course_id, marks))
    print("Student added successfully.")


def show_all_students(database):
    rows = database.get_students_with_courses()
    if not rows:
        print("No students found.")
        return
    print(f"{'ID':<8}{'Name':<24}{'Course':<16}Marks")
    for student_id, name, course_name, marks in rows:
        print(f"{student_id:<8}{name:<24}{course_name:<16}{marks:g}")


def search_student(database):
    student_id = _read_integer("Student ID to search: ")
    student = database.get_student_by_id(student_id)
    print(student if student is not None else "Student not found.")


def search_students_by_course(database):
    _show_students(database.get_students_by_course(input("Course name: ").strip()))


def search_students_by_marks(database):
    marks = _read_marks("Minimum marks (0-100): ")
    if not 0 <= marks <= 100:
        raise ValueError("Marks must be between 0 and 100.")
    _show_students(database.get_students_by_marks(marks))


def sort_students(database):
    print("1. Highest marks first")
    print("2. Lowest marks first")
    choice = input("Choose sort order: ").strip()
    if choice not in ("1", "2"):
        raise ValueError("Invalid sort order. Choose 1 or 2.")
    _show_students(database.get_students_sorted_by_marks(desc=choice == "1"))


def show_top_students(database):
    _show_students(database.get_top_students(_read_integer("Number of top students: ")))


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
    try:
        age = int(age_text) if age_text else current.age
        course_id = int(course_text) if course_text else current.course_id
        marks = float(marks_text) if marks_text else current.marks
    except ValueError as error:
        raise ValueError("Please enter valid numbers for age, course ID, and marks.") from error
    student = Student(current.student_id, name, age, course_id, marks)
    if database.update_student(student):
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
    if input("Delete this student? (y/n): ").strip().casefold() not in ("y", "yes"):
        print("Deletion cancelled.")
        return
    if database.delete_student(student_id):
        print("Student deleted successfully.")
    else:
        print("Student not found.")


def show_student_statistics(database):
    total = database.get_total_students()
    total_marks = database.get_total_marks()
    average = database.get_average_marks()
    highest = database.get_highest_marks()
    lowest = database.get_lowest_marks()
    print(f"Total Students      : {total}")
    print(f"Total Marks         : {total_marks if total_marks is not None else 0}")
    print(f"Average Marks       : {average:.2f}" if average is not None else "Average Marks       : N/A")
    print(f"Highest Marks       : {highest}" if highest is not None else "Highest Marks       : N/A")
    print(f"Lowest Marks        : {lowest}" if lowest is not None else "Lowest Marks        : N/A")


def show_course_statistics(database):
    rows = database.get_course_statistics()
    if not rows:
        print("No course statistics found.")
        return
    print(f"{'Course':<16}{'Students':>10}{'Average':>12}{'Highest':>12}{'Lowest':>10}")
    for name, total, average, highest, lowest in rows:
        fields = (
            f"{average:.2f}" if average is not None else "N/A",
            str(highest) if highest is not None else "N/A",
            str(lowest) if lowest is not None else "N/A",
        )
        print(f"{name:<16}{total:>10}{fields[0]:>12}{fields[1]:>12}{fields[2]:>10}")


def show_courses_without_students(database):
    courses = database.get_courses_without_students()
    if not courses:
        print("Every course has at least one student.")
        return
    for course_id, course_name in courses:
        print(f"{course_id}: {course_name}")


def transfer_student_course(database):
    student_id = _read_integer("Student ID to transfer: ")
    new_course_id = _read_integer("New course ID: ")
    database.transfer_student_course(student_id, new_course_id)
    print("Student course transferred successfully.")


def show_course_history(database):
    student_id_text = input("Student ID (Enter for all history): ").strip()
    if student_id_text:
        try:
            history = database.get_student_course_history(int(student_id_text))
        except ValueError as error:
            raise ValueError("Please enter a valid integer.") from error
    else:
        history = database.get_course_history()
    if not history:
        print("No course transfer history found.")
        return
    print(f"{'History':<9}{'Student':<8}{'Name':<20}{'Old course':<16}{'New course':<16}Changed at")
    for history_id, student_id, name, old_course, new_course, changed_at in history:
        print(
            f"{history_id:<9}{student_id:<8}{name:<20}{old_course:<16}"
            f"{new_course:<16}{changed_at}"
        )


def run_application(database):
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
        "15": transfer_student_course,
        "16": show_course_history,
    }
    while True:
        print("\nStudent Management System — PostgreSQL")
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
        print("15. Transfer Student Course")
        print("16. View Course Transfer History")
        print("17. Exit")
        choice = input("Choose an option: ").strip()
        if choice == "17":
            print("Goodbye.")
            return
        action = actions.get(choice)
        if action is None:
            print("Invalid option. Choose a number from 1 to 17.")
            continue
        try:
            action(database)
        except ValueError as error:
            print(error)
        except Exception as error:
            if not _is_postgres_error(error):
                raise
            if choice == "15":
                print("Transaction failed. Rolling back changes.")
            else:
                print("Database operation failed.")


def main():
    database = Database()
    try:
        database.connect()
        database.create_tables()
        print("Connected to PostgreSQL database successfully.")
        run_application(database)
    except ConfigurationError as error:
        print(f"Database configuration error: {error}")
    except DatabaseConnectionError as error:
        print(error)
    except DatabaseDependencyError as error:
        print(error)
    except Exception as error:
        if not _is_postgres_error(error):
            raise
        print("Database setup failed.")
    finally:
        database.close()


if __name__ == "__main__":
    main()
