import string
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

def clean_text(text):
    """
    Cleans raw feedback text:
    - Lowercases
    - Removes punctuation
    - Removes English stopwords (full sklearn list, ~318 words)
    """
    if not text or not text.strip():
        return ""

    text = text.lower()
    text = text.translate(str.maketrans('', '', string.punctuation))

    words = text.split()
    filtered_words = [word for word in words if word not in ENGLISH_STOP_WORDS]

    return " ".join(filtered_words)
