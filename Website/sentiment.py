from transformers import pipeline

# Using a fine-tuned model specifically trained on student/product reviews
# distilbert-base-uncased-finetuned-sst-2-english is fast and highly accurate
sentiment_pipeline = pipeline(
    "sentiment-analysis",
    model="distilbert-base-uncased-finetuned-sst-2-english",
    truncation=True,
    max_length=512
)

def analyze_sentiment(text):
    """
    Analyzes the sentiment of a given text.
    Returns a dict with 'label' (POSITIVE/NEGATIVE) and 'score' (confidence 0-1).
    """
    if not text or not text.strip():
        return {'label': 'NEUTRAL', 'score': 0.0}
    
    result = sentiment_pipeline(text[:512])[0]
    
    return {
        'label': result['label'],
        'score': result['score']
    }