class Student:
    def __init__(self, student_id, name, age, course, marks):
        if isinstance(student_id, bool) or not isinstance(student_id, int):
            raise ValueError("Student ID must be an integer.")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Student name cannot be empty.")
        if isinstance(age, bool) or not isinstance(age, int) or age <= 0:
            raise ValueError("Age must be an integer greater than 0.")
        if not isinstance(course, str) or not course.strip():
            raise ValueError("Course cannot be empty.")
        if isinstance(marks, bool) or not isinstance(marks, (int, float)) or not 0 <= marks <= 100:
            raise ValueError("Marks must be between 0 and 100.")

        self.student_id = student_id
        self.name = name.strip()
        self.age = age
        self.course = course.strip()
        self.marks = float(marks)

    def __str__(self):
        return (
            f"ID: {self.student_id} | Name: {self.name} | Age: {self.age} | "
            f"Course: {self.course} | Marks: {self.marks:g}"
        )
