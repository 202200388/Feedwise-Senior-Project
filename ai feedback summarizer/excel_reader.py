import openpyxl
from collections import defaultdict

REQUIRED_COLUMNS = {"course", "faculty", "semester", "feedback"}

def load_feedback_from_excel(excel_path):
    """
    Loads feedback from an Excel (.xlsx) file and groups it by (course, faculty, semester).

    Expected columns (case-insensitive):
        course | faculty | semester | feedback

    Returns a dict: {(course, faculty, semester): [feedback, ...]}
    """
    grouped_data = defaultdict(list)

    try:
        workbook = openpyxl.load_workbook(excel_path, read_only=True, data_only=True)
        sheet = workbook.active

        rows = list(sheet.iter_rows(values_only=True))

        if not rows:
            print("❌ Excel file is empty.")
            return grouped_data

        # Read and normalize headers from first row
        headers = [str(cell).strip().lower() if cell else "" for cell in rows[0]]

        # Validate required columns
        missing = REQUIRED_COLUMNS - set(headers)
        if missing:
            print(f"❌ Excel file is missing required columns: {missing}")
            print(f"   Found columns: {headers}")
            return grouped_data

        # Map column names to indices
        col = {name: headers.index(name) for name in REQUIRED_COLUMNS}

        skipped = 0
        for i, row in enumerate(rows[1:], start=2):  # start=2 because row 1 is header
            try:
                course   = str(row[col["course"]]).strip()   if row[col["course"]]   else ""
                faculty  = str(row[col["faculty"]]).strip()  if row[col["faculty"]]  else ""
                semester = str(row[col["semester"]]).strip() if row[col["semester"]] else ""
                feedback = str(row[col["feedback"]]).strip() if row[col["feedback"]] else ""

                if not all([course, faculty, semester, feedback]):
                    print(f"⚠️ Skipping incomplete row {i}")
                    skipped += 1
                    continue

                grouped_data[(course, faculty, semester)].append(feedback)

            except Exception as e:
                print(f"⚠️ Error reading row {i}: {e}")
                skipped += 1
                continue

        workbook.close()

        total = sum(len(v) for v in grouped_data.values())
        print(f"✅ Loaded {total} feedback entries from Excel ({skipped} rows skipped).")

    except FileNotFoundError:
        print(f"❌ File not found: {excel_path}")
    except Exception as e:
        print(f"❌ Error reading Excel file: {e}")

    return grouped_data
