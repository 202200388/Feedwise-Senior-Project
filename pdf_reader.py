import PyPDF2

def extract_text_from_pdf(pdf_path):
    text = ""

    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)

            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"

    except Exception as e:
        print("Error reading PDF:", e)

    return text.strip()