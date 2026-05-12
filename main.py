from preprocessing import clean_text
from sentiment import analyze_sentiment
from summarizer import summarize_text
from issue_detection import extract_top_keywords
from csv_loader import load_feedback_by_group
from excel_reader import load_feedback_from_excel
from pdf_reader import extract_text_from_pdf
import csv
import datetime
from flask import Flask

app = Flask(__name__)
if __name__ == "_main_":
    app.run(host="0.0.0.0", port=8080)
# ---------------------------
# CSV Saving Function
# ---------------------------
def save_results_to_csv(stats, overall_summary, strengths_summary, weaknesses_summary,
                        keywords, course="", faculty="", semester=""):
    filename = "analysis_results.csv"
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    keyword_string = ", ".join([f"{word} ({round(score, 2)})" for word, score in keywords])

    row = [
        timestamp,
        course,
        faculty,
        semester,
        stats.get("POSITIVE", 0),
        stats.get("NEGATIVE", 0),
        overall_summary,
        strengths_summary,
        weaknesses_summary,
        keyword_string
    ]

    headers = [
        "Timestamp", "Course", "Faculty", "Semester",
        "Positive %", "Negative %",
        "Overall Summary", "Strengths Summary", "Weaknesses Summary",
        "Top Keywords"
    ]

    try:
        with open(filename, "x", newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(headers)
            writer.writerow(row)
    except FileExistsError:
        with open(filename, "a", newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(row)

    print(f"✅ Results saved for: {course if course else 'Manual/PDF input'}")

# ---------------------------
# Sentiment Helpers
# ---------------------------
def sentiment_statistics(feedback_list):
    results = {"POSITIVE": 0, "NEGATIVE": 0}
    for text in feedback_list:
        label = analyze_sentiment(text)['label']
        results[label] += 1
    total = len(feedback_list)
    return {k: round((v / total) * 100, 2) for k, v in results.items()}

def split_by_sentiment(feedback_list):
    positive, negative = [], []
    for text in feedback_list:
        if analyze_sentiment(text)['label'] == "POSITIVE":
            positive.append(text)
        else:
            negative.append(text)
    return positive, negative

# ---------------------------
# Core Analysis Function
# ---------------------------
def run_analysis(feedback_text, course="", faculty="", semester=""):
    feedback_list = [line.strip() for line in feedback_text.split("\n") if line.strip()]

    if not feedback_list:
        print("⚠️ No feedback to analyze.")
        return

    cleaned_feedback = [clean_text(text) for text in feedback_list]

    stats = sentiment_statistics(feedback_list)
    positive, negative = split_by_sentiment(feedback_list)

    overall_summary   = summarize_text(" ".join(feedback_list))
    strengths_summary = summarize_text(" ".join(positive)) if positive else "No positive feedback."
    weaknesses_summary = summarize_text(" ".join(negative)) if negative else "No negative feedback."

    keywords = extract_top_keywords(cleaned_feedback)

    # Print report
    print("\n" + "=" * 50)
    print(f"  Course  : {course   or 'N/A'}")
    print(f"  Faculty : {faculty  or 'N/A'}")
    print(f"  Semester: {semester or 'N/A'}")
    print("=" * 50)
    print(f"  Positive: {stats.get('POSITIVE', 0)}%  |  Negative: {stats.get('NEGATIVE', 0)}%")
    print(f"\n  Overall Summary:\n  {overall_summary}")
    print(f"\n  Strengths:\n  {strengths_summary}")
    print(f"\n  Weaknesses:\n  {weaknesses_summary}")
    print(f"\n  Top Keywords:")
    print("  " + ", ".join([f"{w} ({round(s, 2)})" for w, s in keywords]))
    print("=" * 50)

    save_results_to_csv(stats, overall_summary, strengths_summary,
                        weaknesses_summary, keywords, course, faculty, semester)

# ---------------------------
# Grouped Analysis (shared)
# ---------------------------
def run_grouped_analysis(grouped_data, source_label=""):
    if not grouped_data:
        print(f"⚠️ No data loaded from {source_label}.")
        return

    for (course, faculty, semester), feedback_list in grouped_data.items():
        print(f"\n{'=' * 50}")
        print(f"  Analyzing: {course} | {faculty} | {semester}")
        run_analysis("\n".join(feedback_list), course, faculty, semester)

# ---------------------------
# Input Handlers
# ---------------------------
def handle_manual():
    print("\nPaste feedback below — one comment per line.")
    print("Press Enter on an empty line when done.\n")
    lines = []
    while True:
        line = input()
        if line == "":
            break
        lines.append(line)
    return "\n".join(lines)

def handle_csv():
    path = input("Enter CSV file path (e.g. feedback_data.csv): ").strip()
    grouped = load_feedback_by_group(path)
    run_grouped_analysis(grouped, source_label=path)

def handle_excel():
    path = input("Enter Excel file path (e.g. feedback_data.xlsx): ").strip()
    grouped = load_feedback_from_excel(path)
    run_grouped_analysis(grouped, source_label=path)

def handle_pdf():
    path = input("Enter PDF file path (e.g. feedback.pdf): ").strip()
    pdf_text = extract_text_from_pdf(path)
    if not pdf_text:
        return

    lines = [line.strip() for line in pdf_text.splitlines() if line.strip()]
    grouped_data = {}
    for line in lines:
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 4:
            continue
        course, faculty, semester = parts[:3]
        feedback = ", ".join(parts[3:])
        key = (course, faculty, semester)
        if key not in grouped_data:
            grouped_data[key] = []
        grouped_data[key].append(feedback)

    run_grouped_analysis(grouped_data, source_label=path)

# ---------------------------
# Entry Point
# ---------------------------
if __name__ == "__main__":
    print("\n========================================")
    print("   Academic Feedback Summarizer")
    print("========================================")
    print("Choose input method:")
    print("  1 → Paste feedback manually")
    print("  2 → Load from PDF file")
    print("  3 → Load from CSV file")
    print("  4 → Load from Excel file (.xlsx)")
    print("  5 → Manual + PDF combined")

    choice = input("\nEnter option (1–5): ").strip()

    if choice == "1":
        text = handle_manual()
        if text.strip():
            run_analysis(text)

    elif choice == "2":
        handle_pdf()

    elif choice == "3":
        handle_csv()

    elif choice == "4":
        handle_excel()

    elif choice == "5":
        text = handle_manual()
        handle_pdf()
        if text.strip():
            run_analysis(text)

    else:
        print("❌ Invalid option. Please run again and choose 1–5.")
