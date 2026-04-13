import PyPDF2

def extract_text_from_pdf(pdf_path):
    """
    Extracts all text from a PDF file, page by page.
    Returns a single cleaned string of all extracted text.
    """
    text = ""

    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)

            if len(reader.pages) == 0:
                print("⚠️ PDF has no pages.")
                return ""

            for i, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
                else:
                    print(f"⚠️ Page {i + 1} has no extractable text (may be scanned).")

    except FileNotFoundError:
        print(f"❌ File not found: {pdf_path}")
    except Exception as e:
        print(f"❌ Error reading PDF: {e}")

    return text.strip()
