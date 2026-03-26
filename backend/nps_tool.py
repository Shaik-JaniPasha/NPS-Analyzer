print("🚀 NPS TOOL LOADED")

import pandas as pd
from textblob import TextBlob
from deep_translator import GoogleTranslator
import os
import time

# ---------------- MAIN FUNCTION ----------------
def process_nps(input_file):

    file_name = os.path.basename(input_file)
    timestamp = int(time.time())
    output_file = f"output_files/Output_{timestamp}_{file_name}"

    print(f"📂 File loaded: {file_name}")

    # ---------------- LOAD DATA ----------------
    df = pd.read_excel(input_file)
    print(f"📊 Total rows: {len(df)}")

    # ---------------- TRANSLATOR ----------------
    translator = GoogleTranslator(source='auto', target='en')

    def translate_text(text):
        try:
            return translator.translate(str(text))
        except:
            return str(text)

    # ---------------- IDENTIFY TEXT COLUMNS ----------------
    text_columns = df.select_dtypes(include=['object']).columns
    print(f"📝 Text columns detected: {list(text_columns)}")

    # Combine all text columns into one
    df["Combined_Text"] = df[text_columns].astype(str).agg(" ".join, axis=1)

    # ---------------- SENTIMENT ----------------
    def get_sentiment(text):
        polarity = TextBlob(str(text)).sentiment.polarity
        if polarity > 0:
            return "Positive"
        elif polarity < 0:
            return "Negative"
        else:
            return "Neutral"

    # ---------------- THEME ----------------
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

    # ---------------- AVOIDABLE ----------------
    def avoidable_flag(text):
        text = str(text).lower()
        keywords = ["delay", "bad", "poor", "issue", "error", "late"]
        return "Avoidable" if any(k in text for k in keywords) else "Non-Avoidable"

    # ---------------- PROCESS ----------------
    translated = []
    sentiments = []
    themes = []
    avoidable = []

    total = len(df)

    for i, text in enumerate(df["Combined_Text"]):
        eng = translate_text(text)
        translated.append(eng)

        sentiments.append(get_sentiment(eng))
        themes.append(detect_theme(eng))
        avoidable.append(avoidable_flag(eng))

        if i % 50 == 0:
            print(f"Processing {i+1}/{total}")

    # Add columns
    df["Translated_Text"] = translated
    df["Sentiment"] = sentiments
    df["Theme"] = themes
    df["Avoidable Impact"] = avoidable

    print("✅ Processing complete")

    # ---------------- SUMMARY ----------------
    summary = df.groupby(["Sentiment", "Theme"]).size().reset_index(name="Count")

    # Top 3 focus areas
    focus_areas = (
        df[df["Sentiment"] == "Negative"]["Theme"]
        .value_counts()
        .head(3)
        .reset_index()
    )
    focus_areas.columns = ["Theme", "Count"]

    # Avoidable split
    avoidable_summary = df["Avoidable Impact"].value_counts().reset_index()
    avoidable_summary.columns = ["Type", "Count"]

    # ---------------- KPI ----------------
    positive = len(df[df["Sentiment"] == "Positive"])
    negative = len(df[df["Sentiment"] == "Negative"])
    neutral = len(df[df["Sentiment"] == "Neutral"])

    avoidable_pct = round((len(df[df["Avoidable Impact"] == "Avoidable"]) / total) * 100, 2)

    kpi = pd.DataFrame({
        "Metric": [
            "Total Responses",
            "Positive %",
            "Negative %",
            "Neutral %",
            "Avoidable Issues %"
        ],
        "Value": [
            total,
            round(positive/total*100,2),
            round(negative/total*100,2),
            round(neutral/total*100,2),
            avoidable_pct
        ]
    })

    # ---------------- INSIGHTS ----------------
    top_issue = focus_areas.iloc[0]["Theme"] if not focus_areas.empty else "None"

    insights_list = [
        f"{round(negative/total*100,2)}% feedback is negative",
        f"Top issue: {top_issue}",
        f"{avoidable_pct}% issues are avoidable"
    ]

    if positive > negative:
        insights_list.append("Overall sentiment is positive")
    else:
        insights_list.append("Immediate improvement needed")

    insights = pd.DataFrame({"Insights": insights_list})

    # ---------------- SAVE ----------------
    os.makedirs("output_files", exist_ok=True)

    # Prevent permission error (overwrite safely)
    if os.path.exists(output_file):
        os.remove(output_file)

    with pd.ExcelWriter(output_file) as writer:
        df.to_excel(writer, sheet_name="Detailed Data", index=False)
        summary.to_excel(writer, sheet_name="Summary", index=False)
        focus_areas.to_excel(writer, sheet_name="Focus Areas", index=False)
        avoidable_summary.to_excel(writer, sheet_name="Avoidable Impact", index=False)
        kpi.to_excel(writer, sheet_name="KPIs", index=False)
        insights.to_excel(writer, sheet_name="Key Insights", index=False)

    print("🎉 Output saved at:", output_file)

    # ✅ FINAL RETURN (THIS FIXES YOUR API)
    return (
        output_file,
        kpi.to_dict(orient="records"),
        focus_areas.to_dict(orient="records"),
        insights.to_dict(orient="records")
    )