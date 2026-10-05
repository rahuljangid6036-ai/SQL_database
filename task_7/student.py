class Student:
    def __init__(self, student_id, name, age, course_id, marks):
        self.student_id = student_id
        self.name = name
        self.age = age
        self.course_id = course_id
        self.marks = marks
        self.course_name = None
        self.validate()

    def validate(self):
        if isinstance(self.student_id, bool) or not isinstance(self.student_id, int):
            raise ValueError("Student ID must be an integer.")
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("Student name cannot be empty.")
        if isinstance(self.age, bool) or not isinstance(self.age, int) or self.age <= 0:
            raise ValueError("Age must be an integer greater than 0.")
        if isinstance(self.course_id, bool) or not isinstance(self.course_id, int):
            raise ValueError("Course ID must be an integer.")
        if isinstance(self.marks, bool) or not isinstance(self.marks, (int, float)) or not 0 <= self.marks <= 100:
            raise ValueError("Marks must be between 0 and 100.")

        self.name = self.name.strip()
        self.marks = float(self.marks)

    def __str__(self):
        course = self.course_name if self.course_name is not None else self.course_id
        return (
            f"ID: {self.student_id} | Name: {self.name} | Age: {self.age} | "
            f"Course: {course} | Marks: {self.marks:g}"
        )