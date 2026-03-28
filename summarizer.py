from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np

def summarize_text(text, num_sentences=2):
    sentences = text.split(". ")

    if len(sentences) <= num_sentences:
        return text

    vectorizer = TfidfVectorizer(stop_words='english')
    X = vectorizer.fit_transform(sentences)

    scores = np.array(X.sum(axis=1)).flatten()

    ranked_sentences = [sentences[i] for i in scores.argsort()[::-1]]

    summary = ". ".join(ranked_sentences[:num_sentences])

    return summary