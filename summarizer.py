from transformers import BartForConditionalGeneration, BartTokenizer

MODEL_NAME = "facebook/bart-large-cnn"
tokenizer = BartTokenizer.from_pretrained(MODEL_NAME)
model = BartForConditionalGeneration.from_pretrained(MODEL_NAME)

def summarize_text(text, max_length=100, min_length=30):
    if not text or len(text.split()) < 15:
        return text.strip() if text else "No feedback provided."

    try:
        inputs = tokenizer(text, return_tensors="pt", max_length=1024, truncation=True)
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
        return f"Summary error: {str(e)}"