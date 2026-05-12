import csv
from collections import defaultdict

REQUIRED_COLUMNS = {"course", "faculty", "semester", "feedback"}

def load_feedback_by_group(csv_file):
    """
    Loads feedback from a CSV file and groups it by (course, faculty, semester).
    Validates required columns before processing.
    Returns a dict: {(course, faculty, semester): [feedback, ...]}
    """
    grouped_data = defaultdict(list)

    try:
        with open(csv_file, newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)

            # Validate columns
            if not reader.fieldnames:
                print("❌ CSV file is empty or has no headers.")
                return grouped_data

            missing = REQUIRED_COLUMNS - {col.strip().lower() for col in reader.fieldnames}
            if missing:
                print(f"❌ CSV is missing required columns: {missing}")
                return grouped_data

            for i, row in enumerate(reader, start=2):  # start=2 because row 1 is header
                course   = row.get("course", "").strip()
                faculty  = row.get("faculty", "").strip()
                semester = row.get("semester", "").strip()
                feedback = row.get("feedback", "").strip()

                if not all([course, faculty, semester, feedback]):
                    print(f"⚠️ Skipping incomplete row {i}: {dict(row)}")
                    continue

                grouped_data[(course, faculty, semester)].append(feedback)

    except FileNotFoundError:
        print(f"❌ File not found: {csv_file}")
    except Exception as e:
        print(f"❌ Error reading CSV: {e}")

    return grouped_data
