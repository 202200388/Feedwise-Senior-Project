from preprocessing import clean_text
from sentiment import analyze_sentiment
from summarizer import summarize_text
from issue_detection import extract_top_keywords
from csv_loader import load_feedback_by_group
from pdf_reader import extract_text_from_pdf
import csv
import datetime

# ---------------------------
# CSV Saving Function
# ---------------------------
def save_results_to_csv(stats, overall_summary, strengths_summary, weaknesses_summary, keywords, course=None, faculty=None, semester=None, positive_feedback=None, negative_feedback=None):
    filename = "analysis_results.csv"
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    keyword_string = ", ".join([f"{word} ({round(score,2)})" for word, score in keywords])
    positive_str = " | ".join(positive_feedback) if positive_feedback else ""
    negative_str = " | ".join(negative_feedback) if negative_feedback else ""

    row = [
        timestamp,
        course if course else "",
        faculty if faculty else "",
        semester if semester else "",
        stats.get("POSITIVE", 0),
        stats.get("NEGATIVE", 0),
        overall_summary,
        strengths_summary,
        weaknesses_summary,
        keyword_string,
        positive_str,
        negative_str
    ]

    try:
        with open(filename, "x", newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow([
                "Timestamp",
                "Course",
                "Faculty",
                "Semester",
                "Positive %",
                "Negative %",
                "Overall Summary",
                "Strengths Summary",
                "Weaknesses Summary",
                "Top Keywords",
                "Positive Feedback",
                "Negative Feedback"
            ])
            writer.writerow(row)
    except FileExistsError:
        with open(filename, "a", newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(row)

    print(f"\n✅ Results saved for {course if course else 'Manual/PDF input'}")

# ---------------------------
# Sentiment functions
# ---------------------------
def sentiment_statistics(feedback_list):
    results = {"POSITIVE": 0, "NEGATIVE": 0}
    for text in feedback_list:
        result = analyze_sentiment(text)
        label = result['label']
        results[label] += 1
    total = len(feedback_list)
    for key in results:
        results[key] = round((results[key] / total) * 100, 2)
    return results

def split_by_sentiment(feedback_list):
    positive = []
    negative = []
    for text in feedback_list:
        result = analyze_sentiment(text)
        if result['label'] == "POSITIVE":
            positive.append(text)
        else:
            negative.append(text)
    return positive, negative

# ---------------------------
# Main analysis function
# ---------------------------
def run_analysis(feedback_text, course=None, faculty=None, semester=None):
    feedback_list = [line.strip() for line in feedback_text.split("\n") if line.strip() != ""]
    if not feedback_list:
        print("No feedback entered.")
        return

    cleaned_feedback = [clean_text(text) for text in feedback_list]

    stats = sentiment_statistics(feedback_list)
    positive, negative = split_by_sentiment(feedback_list)

    overall_summary = summarize_text(" ".join(feedback_list))
    strengths_summary = summarize_text(" ".join(positive)) if positive else ""
    weaknesses_summary = summarize_text(" ".join(negative)) if negative else ""

    keywords = extract_top_keywords(cleaned_feedback)

    # ----------- PRINT STRUCTURED REPORT -----------
    print("\n======================================")
    print(f"Course: {course if course else 'N/A'}")
    print(f"Faculty: {faculty if faculty else 'N/A'}")
    print(f"Semester: {semester if semester else 'N/A'}")
    print(f"Positive %: {stats.get('POSITIVE',0)} | Negative %: {stats.get('NEGATIVE',0)}\n")

    print("Positive Feedback:")
    if positive:
        for line in positive:
            print(f"- {line}")
    else:
        print("- None")

    print("\nNegative Feedback:")
    if negative:
        for line in negative:
            print(f"- {line}")
    else:
        print("- None")

    print("\nOverall Summary:")
    print(overall_summary)

    print("\nTop Keywords:")
    print(", ".join([f"{word} ({round(score,2)})" for word, score in keywords]))

    # ----------- SAVE TO CSV -----------
    save_results_to_csv(
        stats,
        overall_summary,
        strengths_summary,
        weaknesses_summary,
        keywords,
        course,
        faculty,
        semester,
        positive_feedback=positive,
        negative_feedback=negative
    )

# ---------------------------
# CSV Grouped Analysis
# ---------------------------
def run_csv_analysis(csv_path):
    grouped_data = load_feedback_by_group(csv_path)
    for (course, faculty, semester), feedback_list in grouped_data.items():
        print("\n======================================")
        print(f"Analyzing: {course} | {faculty} | {semester}")
        print("======================================")
        feedback_text = "\n".join(feedback_list)
        run_analysis(feedback_text, course, faculty, semester)

# ---------------------------
# PDF Grouped Analysis (CSV-style PDF lines)
# ---------------------------
def run_pdf_analysis_grouped(pdf_path):
    pdf_text = extract_text_from_pdf(pdf_path)
    if not pdf_text:
        print("No text extracted from PDF.")
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

    for (course, faculty, semester), feedback_list in grouped_data.items():
        print(f"\n--- Analyzing PDF Feedback for {course} | {faculty} | {semester} ---")
        feedback_text = "\n".join(feedback_list)
        run_analysis(feedback_text, course, faculty, semester)

# ---------------------------
# Input section
# ---------------------------
if __name__ == "__main__":
    print("Choose input method:")
    print("1 → Paste feedback manually")
    print("2 → Load from PDF file")
    print("3 → Use both")
    print("4 → Load structured CSV (course, faculty, semester)")
    choice = input("Enter option (1/2/3/4): ")

    feedback_text = ""

    if choice == "1" or choice == "3":
        print("\nPaste student feedback below. Enter one comment per line.")
        print("Press Enter twice when finished.\n")
        lines = []
        while True:
            line = input()
            if line == "":
                break
            lines.append(line)
        feedback_text += "\n".join(lines) + "\n"

    if choice == "2" or choice == "3":
        pdf_path = input("\nEnter PDF file path (example: feedback.pdf): ")
        run_pdf_analysis_grouped(pdf_path)

    if choice == "4":
        csv_path = input("Enter CSV file path (example: feedback_data.csv): ")
        run_csv_analysis(csv_path)
    else:
        if feedback_text.strip():
            run_analysis(feedback_text)