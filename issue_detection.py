from sklearn.feature_extraction.text import TfidfVectorizer

def extract_top_keywords(text_list, top_n=10):
    vectorizer = TfidfVectorizer(
        stop_words='english',
        ngram_range=(1,1),
        token_pattern=r'\b[a-zA-Z]{3,}\b'
    )
    X = vectorizer.fit_transform(text_list)
    feature_names = vectorizer.get_feature_names_out()
    scores = X.sum(axis=0).tolist()[0]

    keyword_scores = list(zip(feature_names, scores))
    sorted_keywords = sorted(keyword_scores, key=lambda x: x[1], reverse=True)

    return sorted_keywords[:top_n]