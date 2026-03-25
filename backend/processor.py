import os
import pandas as pd
from textblob import TextBlob
from deep_translator import GoogleTranslator

translator = GoogleTranslator(source='auto', target='en')


def translate_text(text):
    try:
        return translator.translate(str(text))
    except Exception:
        return str(text)


def get_sentiment(text):
    polarity = TextBlob(str(text)).sentiment.polarity
    if polarity > 0:
        return "Positive"
    elif polarity < 0:
        return "Negative"
    else:
        return "Neutral"


def detect_theme(text):
    text = str(text).lower()
    if any(word in text for word in ["delay", "late", "delivery"]):
        return "Delivery Issue"
    elif any(word in text for word in ["support", "service", "help"]):
        return "Customer Service"
    elif any(word in text for word in ["price", "cost", "expensive"]):
        return "Pricing"
    elif any(word in text for word in ["quality", "defect", "broken"]):
        return "Product Quality"
    elif any(word in text for word in ["app", "website", "error", "bug"]):
        return "Technical Issue"
    else:
        return "Other"


def avoidable_flag(text):
    text = str(text).lower()
    keywords = ["delay", "bad", "poor", "issue", "error", "late"]
    return "Avoidable" if any(k in text for k in keywords) else "Non-Avoidable"


def process_file(input_path, output_dir):
    df = pd.read_excel(input_path)
    # defensive: pick 5th column if exists else the last column
    try:
        column_name = df.columns[4]
    except Exception:
        column_name = df.columns[-1]

    translated = []
    sentiments = []
    themes = []
    avoidable = []

    for text in df[column_name]:
        eng = translate_text(text)
        translated.append(eng)
        sentiments.append(get_sentiment(eng))
        themes.append(detect_theme(eng))
        avoidable.append(avoidable_flag(eng))

    df["Translated_Text"] = translated
    df["Sentiment"] = sentiments
    df["Theme"] = themes
    df["Avoidable Impact"] = avoidable

    summary = df.groupby(["Sentiment", "Theme"]).size().reset_index(name="Count")

    focus_areas = (
        df[df["Sentiment"] == "Negative"]
        .groupby("Theme")
        .size()
        .sort_values(ascending=False)
        .reset_index(name="Count")
    )

    avoidable_summary = df["Avoidable Impact"].value_counts().reset_index()
    avoidable_summary.columns = ["Type", "Count"]

    total = len(df)
    positive = len(df[df["Sentiment"] == "Positive"])
    negative = len(df[df["Sentiment"] == "Negative"])

    kpi = pd.DataFrame({
        "Metric": ["Total Responses", "Positive %", "Negative %"],
        "Value": [total, round(positive / total * 100, 2) if total else 0, round(negative / total * 100, 2) if total else 0],
    })

    top_issue = focus_areas.iloc[0]["Theme"] if not focus_areas.empty else "None"

    synopsis = pd.DataFrame({
        "Insight": [
            f"Total responses analyzed: {total}",
            f"Positive feedback: {round(positive / total * 100, 2) if total else 0}%",
            f"Negative feedback: {round(negative / total * 100, 2) if total else 0}%",
            f"Top issue area: {top_issue}",
            "Focus on reducing avoidable issues to improve NPS",
        ]
    })

    os.makedirs(output_dir, exist_ok=True)
    base = os.path.basename(input_path)
    out_name = f"Output_{base}"
    output_path = os.path.join(output_dir, out_name)

    with pd.ExcelWriter(output_path) as writer:
        df.to_excel(writer, sheet_name="Detailed Data", index=False)
        summary.to_excel(writer, sheet_name="Summary", index=False)
        focus_areas.to_excel(writer, sheet_name="Focus Areas", index=False)
        avoidable_summary.to_excel(writer, sheet_name="Avoidable Impact", index=False)
        kpi.to_excel(writer, sheet_name="KPIs", index=False)
        synopsis.to_excel(writer, sheet_name="Synopsis", index=False)

    # return small JSON-friendly summaries
    return {
        "kpi": kpi.to_dict(orient="records"),
        "summary": summary.to_dict(orient="records"),
        "focus_areas": focus_areas.to_dict(orient="records"),
        "avoidable_summary": avoidable_summary.to_dict(orient="records"),
        "output_path": output_path,
    }
