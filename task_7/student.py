class Student:
    def __init__(self, student_id, name, age, course_id, marks):
        self.student_id = student_id
        self.name = name
        self.age = age
        self.course_id = course_id
        self.marks = marks
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
        if (
            isinstance(self.marks, bool)
            or not isinstance(self.marks, (int, float))
            or not 0 <= self.marks <= 100
        ):
            raise ValueError("Marks must be between 0 and 100.")

        self.name = self.name.strip()
        self.marks = float(self.marks)
        return True

    def __str__(self):
        return (
            f"ID: {self.student_id} | Name: {self.name} | Age: {self.age} | "
            f"Course ID: {self.course_id} | Marks: {self.marks:g}"
        )
