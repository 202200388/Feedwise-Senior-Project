import csv
from collections import defaultdict

def load_feedback_by_group(csv_file):
    grouped_data = defaultdict(list)

    with open(csv_file, newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            course = row["course"]
            faculty = row["faculty"]
            semester = row["semester"]
            feedback = row["feedback"]
            key = (course, faculty, semester)
            grouped_data[key].append(feedback)

    return grouped_data