from transformers import BartForConditionalGeneration, BartTokenizer

# Load BART model and tokenizer directly (works with all transformers versions)
MODEL_NAME = "facebook/bart-large-cnn"

print("⏳ Loading summarization model...")
tokenizer = BartTokenizer.from_pretrained(MODEL_NAME)
model = BartForConditionalGeneration.from_pretrained(MODEL_NAME)
print("✅ Summarization model loaded.")


def summarize_text(text, max_length=80, min_length=20):
    """
    Summarizes the given text using Facebook's BART model.
    Falls back gracefully if text is too short to summarize.
    """
    if not text or not text.strip():
        return "No feedback available."

    word_count = len(text.split())
    if word_count < 15:
        return text.strip()

    # Truncate input to 900 words safely
    truncated = " ".join(text.split()[:900])

    try:
        inputs = tokenizer(
            truncated,
            return_tensors="pt",
            max_length=1024,
            truncation=True
        )

        summary_ids = model.generate(
            inputs["input_ids"],
            max_length=max_length,
            min_length=min_length,
            length_penalty=2.0,
            num_beams=4,
            early_stopping=True
        )

        return tokenizer.decode(summary_ids[0], skip_special_tokens=True)

    except Exception as e:
        print(f"⚠️ Summarizer error: {e}")
        return text.strip()