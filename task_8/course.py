class Course:
    def __init__(self, course_id, course_name):
        self.course_id = course_id
        self.course_name = course_name
        self.validate()

    def validate(self):
        if self.course_id is not None and (
            isinstance(self.course_id, bool) or not isinstance(self.course_id, int)
        ):
            raise ValueError("Course ID must be an integer.")
        if not isinstance(self.course_name, str) or not self.course_name.strip():
            raise ValueError("Course name cannot be empty.")
        if len(self.course_name.strip()) > 100:
            raise ValueError("Course name cannot exceed 100 characters.")
        self.course_name = self.course_name.strip()
        return True

    def __str__(self):
        return f"ID: {self.course_id} | Course: {self.course_name}"
