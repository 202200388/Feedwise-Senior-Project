import string

# Simple stopwords list (no nltk needed)
stop_words = {
    "the", "and", "is", "in", "it", "of", "to", "a",
    "was", "were", "for", "on", "with", "as", "that",
    "this", "but", "very", "too", "not"
}

def clean_text(text):
    text = text.lower()
    text = text.translate(str.maketrans('', '', string.punctuation))

    words = text.split()
    filtered_words = [word for word in words if word not in stop_words]

    return " ".join(filtered_words)