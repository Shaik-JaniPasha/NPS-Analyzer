from __future__ import annotations

import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

import pandas as pd
from deep_translator import GoogleTranslator, MyMemoryTranslator

translator = GoogleTranslator(source="auto", target="en")
memory_translator = MyMemoryTranslator(source="german", target="english")

SCORE_COLUMN_CANDIDATES = ("SA Question 4", "Score", "NPS Score", "Rating")
COMMENT_COLUMN_CANDIDATES = ("SA Question 6", "Comment", "Comments", "Feedback", "NPS Comment")

NPS_BUCKETS = (
    ("Detractor", range(0, 7)),
    ("Passive", range(7, 9)),
    ("Promoter", range(9, 11)),
)

THEME_RULES = [
    {
        "theme": "Pricing and Offer Competitiveness",
        "keywords": (
            "angebot", "angebote", "angeboten", "preis", "preise", "teuer", "uberteuert",
            "ueberteuert", "gunstiger", "guenstiger", "bestandskunden", "neukunden", "rabatt",
            "abo", "monatlich", "vertrag", "verlangerung", "verlaengerung", "kosten",
            "billing", "price", "offer", "offers", "subscription", "renewal",
        ),
    },
    {
        "theme": "Cancellation and Retention Handling",
        "keywords": (
            "kundigen", "kuendigen", "kundigung", "kuendigung", "stornieren", "cancel",
            "behalten", "betteln", "respektiert", "respect", "retention",
        ),
    },
    {
        "theme": "Agent Courtesy and Empathy",
        "keywords": (
            "unfreundlich", "freundlich", "hoflich", "hoeflich", "respektlos", "frech",
            "nett", "empath", "courteous", "rude", "professional", "professionell",
        ),
    },
    {
        "theme": "Resolution Quality and Ownership",
        "keywords": (
            "anliegen", "gelost", "geloest", "losungsorientiert", "loesungsorientiert",
            "nicht eingegangen", "nicht ernst genommen", "problem", "geholfen", "hilfe",
            "support", "resolved", "solution", "standard-antworten", "standard antworten",
        ),
    },
    {
        "theme": "Agent Knowledge and Accuracy",
        "keywords": (
            "falsch", "falsche", "falschen", "genauer", "ungenau", "inkompetenz",
            "inkompetent", "nicht bereit", "nicht nennen", "wusste", "kannte", "kennen wurden",
            "know", "knowledge", "accurate", "wrong information", "different offers",
        ),
    },
    {
        "theme": "Language and Communication",
        "keywords": (
            "deutsch", "deutschsprachig", "muttersprachlich", "ubersetzungs", "uebersetzungs",
            "ubersetzungsprogramm", "uebersetzungsprogramm", "sprache", "verstehen", "language",
            "translation", "chatpartner",
        ),
    },
    {
        "theme": "Response Time and Wait Time",
        "keywords": (
            "wartezeit", "wartezeiten", "lange", "lang", "schneller", "schnell", "zeit",
            "minuten", "stunde", "beansprucht", "ticket", "slow", "wait", "waiting",
        ),
    },
    {
        "theme": "Chat and Bot Experience",
        "keywords": (
            "chat", "bot", "chatbot", "link", "geschlossen", "schliessen", "schliessen",
            "beendet", "abgelaufen", "dead link", "toten link", "chat-funktion",
        ),
    },
    {
        "theme": "Technical Product or Device Issue",
        "keywords": (
            "app", "receiver", "sony", "smart-tv", "smart tv", "gerat", "geraet", "technik",
            "technisch", "error", "bug", "problem mit", "funktioniert", "device", "website",
        ),
    },
    {
        "theme": "Contact Channel Preference",
        "keywords": (
            "telefon", "telefonisch", "anrufen", "email", "e-mail", "hotline", "kontakt",
            "call", "phone",
        ),
    },
    {
        "theme": "Process and Policy Friction",
        "keywords": (
            "adresse", "schriftliche kundigung", "schriftliche kuendigung", "pflichtverstoss",
            "prozess", "policy", "formular",
        ),
    },
]

POSITIVE_HINTS = (
    "alles bestens", "wunschlos glucklich", "wunschlos gluecklich", "sehr gut", "perfekt",
    "zufrieden", "professionell", "nichts zu verbessern", "super", "bestens", "sehr freundlich",
)

NEGATIVE_SERVICE_HINTS = (
    "unfreundlich", "nicht eingegangen", "nicht ernst genommen", "nicht bereit", "chat schliessen",
    "beendet", "betteln", "falsche", "katastrophe", "katastrophal", "inkompetenz",
    "ubersetzungsprogramm", "uebersetzungsprogramm", "lange wartezeit",
)

GERMAN_TO_ENGLISH_PHRASES = {
    "nicht ernst genommen": "not taken seriously",
    "nicht eingegangen": "not addressed",
    "nicht losungsorientiert": "not solution-oriented",
    "nicht loesungsorientiert": "not solution-oriented",
    "sehr unfreundlich": "very unfriendly",
    "lange wartezeit": "long wait time",
    "toter link": "dead link",
    "chat beendet": "chat ended",
    "chat schliessen": "close the chat",
    "deutschsprachige mitarbeiter": "German-speaking agents",
    "muttersprachliche hotline": "native-language hotline",
    "bestandskunden": "existing customers",
    "neukunden": "new customers",
    "kundigungsprozess": "cancellation process",
    "kuendigungsprozess": "cancellation process",
    "kundigen": "cancel",
    "kuendigen": "cancel",
    "kundigung": "cancellation",
    "kuendigung": "cancellation",
    "angeboten": "offers",
    "angebote": "offers",
    "angebot": "offer",
    "preise": "prices",
    "preis": "price",
    "gunstiger": "cheaper",
    "guenstiger": "cheaper",
    "uberteuert": "overpriced",
    "ueberteuert": "overpriced",
    "unfreundlich": "unfriendly",
    "freundlich": "friendly",
    "wartezeiten": "wait times",
    "wartezeit": "wait time",
    "anliegen": "request",
    "mitarbeiter": "agent",
    "vertrag": "contract",
    "telefonisch": "by phone",
    "telefon": "phone",
    "losung": "solution",
    "loesung": "solution",
    "problem": "problem",
}

GERMAN_TO_ENGLISH_WORDS = {
    "aber": "but",
    "absolut": "absolutely",
    "agent": "agent",
    "alle": "all",
    "alles": "everything",
    "als": "than",
    "am": "at the",
    "an": "to",
    "angebot": "offer",
    "angebote": "offers",
    "angeboten": "offers",
    "anfrage": "request",
    "anliegen": "request",
    "ansprechpartnerin": "advisor",
    "app": "app",
    "arbeiten": "work",
    "auch": "also",
    "auf": "on",
    "aufhoren": "stop",
    "atzend": "awful",
    "aus": "out",
    "beendet": "ended",
    "bei": "during",
    "bekam": "received",
    "bessere": "better",
    "besser": "better",
    "bestandskunden": "existing customers",
    "bestellung": "order",
    "betteln": "begging",
    "bevor": "before",
    "bitte": "please",
    "bot": "bot",
    "chat": "chat",
    "chatfunktion": "chat function",
    "chatpartner": "chat agent",
    "dann": "then",
    "das": "that",
    "dass": "that",
    "da": "there",
    "dauerte": "took",
    "dazu": "for that",
    "deutsch": "german",
    "deutschsprachige": "german-speaking",
    "die": "the",
    "diesem": "this",
    "direkt": "directly",
    "doch": "after all",
    "ein": "a",
    "eine": "a",
    "einem": "a",
    "einen": "a",
    "einfach": "simply",
    "einfacher": "simpler",
    "er": "he",
    "erhalten": "receive",
    "erst": "first",
    "es": "it",
    "euer": "your",
    "far": "far",
    "fall": "case",
    "freundlich": "friendly",
    "fur": "for",
    "funktion": "function",
    "funktioniert": "works",
    "ganz": "very",
    "gemacht": "made",
    "genauer": "more accurate",
    "geandert": "changed",
    "gewohnungsbedurftig": "hard to get used to",
    "geschickt": "sent",
    "geschlossen": "closed",
    "gibt": "there is",
    "gute": "good",
    "gunstige": "cheap",
    "gunstiger": "cheaper",
    "hat": "has",
    "hatte": "had",
    "helfen": "help",
    "hilfe": "help",
    "hotline": "hotline",
    "ich": "I",
    "ihrem": "their",
    "im": "in the",
    "ki": "AI",
    "immer": "always",
    "in": "in",
    "individueller": "more tailored",
    "ist": "is",
    "ja": "indeed",
    "jetzt": "now",
    "kann": "can",
    "katastrophe": "disaster",
    "katastrophal": "catastrophic",
    "keine": "no",
    "kein": "no",
    "kennen": "know",
    "klaren": "clarify",
    "konnte": "could",
    "konnen": "can",
    "kontakt": "contact",
    "kosten": "costs",
    "kunde": "customer",
    "kunden": "customers",
    "kundigen": "cancel",
    "kundigung": "cancellation",
    "langjahrigen": "long-term",
    "lange": "long",
    "laut": "according to",
    "leistungsverhaltnis": "value for money",
    "link": "link",
    "losungsorientiert": "solution-oriented",
    "macht": "makes",
    "machen": "make",
    "mal": "once",
    "mehr": "more",
    "mein": "my",
    "meine": "my",
    "mit": "with",
    "mitarbeiter": "agent",
    "monatlich": "monthly",
    "muttersprachliche": "native-language",
    "muss": "must",
    "nach": "after",
    "neue": "new",
    "neues": "anything new",
    "neukunden": "new customers",
    "nicht": "not",
    "nochmal": "again",
    "nur": "only",
    "ob": "whether",
    "oder": "or",
    "ohne": "without",
    "personliche": "personal",
    "phone": "phone",
    "preis": "price",
    "preise": "prices",
    "problem": "problem",
    "respektiert": "respected",
    "sagt": "says",
    "schliessen": "close",
    "schrieb": "wrote",
    "sehr": "very",
    "schneller": "faster",
    "sowie": "as well as",
    "sollte": "should",
    "sony": "sony",
    "so": "so",
    "stehen": "show",
    "toten": "dead",
    "ueberprufung": "review",
    "uberteuert": "overpriced",
    "unterschiedliche": "different",
    "unterschiedlichen": "different",
    "unterschiedlicher": "different",
    "unfreundlich": "unfriendly",
    "unsere": "our",
    "versteht": "understands",
    "vertrag": "contract",
    "verlangerung": "renewal",
    "verbessert": "improved",
    "verbessern": "improve",
    "versprochen": "promised",
    "vielleicht": "maybe",
    "viel": "much",
    "voll": "completely",
    "vor": "before",
    "war": "was",
    "waren": "were",
    "warte": "wait",
    "wartezeit": "wait time",
    "wartezeiten": "wait times",
    "weil": "because",
    "wenn": "when",
    "werden": "be",
    "wie": "as",
    "will": "wants",
    "wir": "we",
    "wirklich": "really",
    "wird": "will be",
    "wollen": "want",
    "zu": "too",
    "zufrieden": "satisfied",
}

PATTERN_TRANSLATIONS = [
    (
        re.compile(r"wenn ein kunde sagt, dass er (.+?) will, dann sollte das respektiert werden", re.IGNORECASE),
        lambda match: f"When a customer says they want to {match.group(1)}, that should be respected.",
    ),
    (
        re.compile(r"bestandskunden neue gute angebote machen sowie vertrag nicht dauert verteuern ohne neues dazu zu nehmen", re.IGNORECASE),
        lambda match: "Existing customers should receive good new offers, and contracts should not keep getting more expensive without adding anything new.",
    ),
    (
        re.compile(r"laut bestellung waren (.+?) monatlich angegeben.*?aber (.+?) euro.*?uberprufung geandert wird", re.IGNORECASE),
        lambda match: f"According to the order, the price was listed as {match.group(1)} per month, but the subscription shows {match.group(2)} euros and the AI said it would be corrected during review.",
    ),
    (
        re.compile(r"aufhoren zu betteln, nicht einfach den chat schliessen, nur weil ein kunde (.+?) mochte", re.IGNORECASE),
        lambda match: f"Stop begging and do not simply close the chat just because a customer wants to {match.group(1)}.",
    ),
    (
        re.compile(r"vielleicht sollten die unterschiedlichen mitarbeiter mal klaren.*?unterschiedliche angebote.*?telefon nochmal andere.*?katastrophe", re.IGNORECASE),
        lambda match: "Agents should align on what prices and offers can actually be given. Getting different offers in chat and again on the phone is a disaster.",
    ),
    (
        re.compile(r"sehr unfreundlich und nicht losungsorientiert\.?", re.IGNORECASE),
        lambda match: "Very unfriendly and not solution-oriented.",
    ),
    (
        re.compile(r"preis[- ]+.*leistungsver.*muss dri?ngend verbessert werden", re.IGNORECASE),
        lambda match: "The value for money must be improved urgently.",
    ),
    (
        re.compile(r"einfacher kundigungsprozess", re.IGNORECASE),
        lambda match: "The cancellation process should be simpler.",
    ),
    (
        re.compile(r"gunstigere angebote,? viel zu uberteuert", re.IGNORECASE),
        lambda match: "Cheaper offers are needed; the current pricing is far too expensive.",
    ),
    (
        re.compile(r"sky-app fur (.+)", re.IGNORECASE),
        lambda match: f"Sky app for {match.group(1)}.",
    ),
    (
        re.compile(r"in meinem fall gibt es nichts zu verbessern\.?", re.IGNORECASE),
        lambda match: "There is nothing to improve in my case.",
    ),
    (
        re.compile(r"wunschlos glucklich", re.IGNORECASE),
        lambda match: "Completely satisfied.",
    ),
    (
        re.compile(r"alles bestens", re.IGNORECASE),
        lambda match: "Everything was excellent.",
    ),
    (
        re.compile(r"personliche muttersprachliche hotline ziehe ich einem chat vor.*?bot.*?toten link", re.IGNORECASE),
        lambda match: "I prefer a personal native-language hotline over chat. Before I even reached an agent, the bot sent me to a dead link three times.",
    ),
    (
        re.compile(r"die chat-funktion ist erst einmal sehr gewohnungsbedurftig.*?ansprechpartnerin war sehr freundlich.*?funktioniert, wie versprochen", re.IGNORECASE),
        lambda match: "The chat function takes some getting used to. Our advisor was very friendly, but I still need to see whether everything works as promised.",
    ),
    (
        re.compile(r"preis.*leistungsver.*verbessert werden", re.IGNORECASE),
        lambda match: "The value for money must be improved urgently.",
    ),
]


def normalize_text(text: str) -> str:
    value = str(text or "").strip().lower()
    value = (
        value.replace("ä", "a")
        .replace("ö", "o")
        .replace("ü", "u")
        .replace("ß", "ss")
    )
    value = value.replace("\n", " ")
    value = re.sub(r"\s+", " ", value)
    return value


def detect_columns(df: pd.DataFrame) -> tuple[str, str]:
    score_column = next(
        (column for column in df.columns if any(candidate.lower() in str(column).lower() for candidate in SCORE_COLUMN_CANDIDATES)),
        None,
    )
    comment_column = next(
        (column for column in df.columns if any(candidate.lower() in str(column).lower() for candidate in COMMENT_COLUMN_CANDIDATES)),
        None,
    )

    if score_column is None:
        raise ValueError("Could not find the NPS score column in the uploaded workbook.")
    if comment_column is None:
        raise ValueError("Could not find the SA Question 6 comment column in the uploaded workbook.")

    return str(score_column), str(comment_column)


def parse_score(raw_value) -> int | None:
    if pd.isna(raw_value):
        return None

    match = re.search(r"\d+", str(raw_value))
    if not match:
        return None

    score = int(match.group())
    return score if 0 <= score <= 10 else None


def nps_category(score: int | None) -> str:
    if score is None:
        return "Unknown"

    for label, valid_range in NPS_BUCKETS:
        if score in valid_range:
            return label
    return "Unknown"


def sentiment_from_score(score: int | None) -> str:
    category = nps_category(score)
    if category == "Promoter":
        return "Positive"
    if category == "Passive":
        return "Neutral"
    if category == "Detractor":
        return "Negative"
    return "Neutral"


def glossary_translate(text: str) -> str:
    translated = f" {str(text or '').strip()} "
    for german_phrase, english_phrase in sorted(GERMAN_TO_ENGLISH_PHRASES.items(), key=lambda item: len(item[0]), reverse=True):
        pattern = r"(?<!\w)" + re.escape(german_phrase) + r"(?!\w)"
        translated = re.sub(pattern, english_phrase, translated, flags=re.IGNORECASE)
    transliterated = normalize_text(translated)
    tokens = re.findall(r"[a-zA-Z0-9-]+|[^\w\s]", transliterated)
    translated_tokens = [GERMAN_TO_ENGLISH_WORDS.get(token, token) for token in tokens]
    output = []
    for token in translated_tokens:
        if token in {".", ",", "!", "?", ";", ":"}:
            if output:
                output[-1] = f"{output[-1]}{token}"
            else:
                output.append(token)
        else:
            output.append(token)
    translated = " ".join(output).strip()
    translated = re.sub(r"\s+", " ", translated).strip()
    return translated if translated else str(text or "").strip()


def split_translation_chunks(text: str) -> list[str]:
    chunks = [chunk.strip(" ,;") for chunk in re.split(r"(?<=[.!?])\s+|[;\n]+", str(text or "").strip())]
    return [chunk for chunk in chunks if chunk]


def apply_pattern_translation(text: str) -> str | None:
    normalized = normalize_text(text)
    for pattern, formatter in PATTERN_TRANSLATIONS:
        match = pattern.search(normalized)
        if match:
            return glossary_translate(formatter(match))
    return None


def looks_like_untranslated(source: str, translated: str) -> bool:
    source_norm = normalize_text(source)
    translated_norm = normalize_text(translated)
    if not translated_norm:
        return True
    if source_norm == translated_norm:
        return True
    german_markers = (
        " nicht ", " und ", " oder ", " aber ", " kunde ", " kunden ", " mitarbeiter ",
        " angebot", " angebote", " preis", " wartezeit", " kuendig", " chat ", " bitte ",
    )
    return any(marker in f" {translated_norm} " for marker in german_markers)


def translate_chunk(chunk: str) -> str:
    pattern_translation = apply_pattern_translation(chunk)
    if pattern_translation:
        return pattern_translation

    for translate_fn in (translator.translate, memory_translator.translate):
        try:
            translated = translate_fn(chunk)
            if translated and not looks_like_untranslated(chunk, translated):
                return translated.strip()
        except Exception:
            continue
    return glossary_translate(chunk)


def translate_text(text: str) -> str:
    cleaned = str(text or "").strip()
    if not cleaned:
        return ""

    pattern_translation = apply_pattern_translation(cleaned)
    if pattern_translation:
        return pattern_translation

    translated = translate_chunk(cleaned)
    if not looks_like_untranslated(cleaned, translated):
        return translated

    chunks = split_translation_chunks(cleaned)
    if len(chunks) > 1:
      joined = " ".join(translate_chunk(chunk) for chunk in chunks).strip()
      if joined and not looks_like_untranslated(cleaned, joined):
          return joined

    return glossary_translate(cleaned)


def translate_unique_comments(comments: pd.Series, progress_callback: Callable[[int, int], None] | None = None) -> dict[str, str]:
    unique_comments = [comment for comment in pd.unique(comments) if str(comment).strip()]
    total = max(len(unique_comments), 1)
    lookup = {"": ""}

    def worker(item: tuple[int, str]):
        index, comment = item
        translated = translate_text(comment)
        if progress_callback:
            progress_callback(index + 1, total)
        return comment, translated

    if unique_comments:
        with ThreadPoolExecutor(max_workers=min(8, len(unique_comments))) as executor:
            for source, translated in executor.map(worker, enumerate(unique_comments)):
                lookup[source] = translated
    elif progress_callback:
        progress_callback(1, 1)

    return lookup


def classify_theme(comment: str, translated_comment: str, score: int | None) -> str:
    normalized_source = normalize_text(comment)
    normalized_translated = normalize_text(translated_comment)
    normalized = f"{normalized_source} | {normalized_translated}"

    if not normalized_source or normalized_source == normalize_text("No Feedback written by customer"):
        return "Survey without comment"

    has_positive_hint = any(hint in normalized_source for hint in POSITIVE_HINTS)
    has_negative_service_hint = any(hint in normalized_source for hint in NEGATIVE_SERVICE_HINTS)

    if score is not None and score >= 9 and has_positive_hint and not has_negative_service_hint:
        return "Positive Service Experience"

    theme_scores: dict[str, int] = {}
    for rule in THEME_RULES:
        match_score = sum(1 for keyword in rule["keywords"] if keyword in normalized)
        if match_score:
            theme_scores[rule["theme"]] = match_score

    if theme_scores:
        if score is not None and score <= 8:
            service_priority = (
                "Cancellation and Retention Handling",
                "Agent Courtesy and Empathy",
                "Resolution Quality and Ownership",
                "Agent Knowledge and Accuracy",
                "Language and Communication",
                "Response Time and Wait Time",
                "Chat and Bot Experience",
                "Process and Policy Friction",
            )
            for priority_theme in service_priority:
                if theme_scores.get(priority_theme, 0) >= 2:
                    return priority_theme
                if has_negative_service_hint and theme_scores.get(priority_theme, 0) >= 1:
                    return priority_theme

        return max(theme_scores.items(), key=lambda item: (item[1], -len(item[0])))[0]

    if has_positive_hint:
        return "Positive Service Experience"
    if score is not None and score <= 8:
        return "General Service Dissatisfaction"
    if score is not None and score >= 9:
        return "Positive Service Experience"
    return "Unspecified Feedback"


def classify_avoidable(theme: str, comment: str, translated_comment: str, score: int | None) -> str:
    category = nps_category(score)
    if category == "Promoter":
        return "Not Applicable"

    if theme == "Survey without comment":
        return "Non-Avoidable"

    normalized = f"{normalize_text(comment)} | {normalize_text(translated_comment)}"
    normalized_source = normalize_text(comment)
    has_positive_hint = any(hint in normalized_source for hint in POSITIVE_HINTS)

    avoidable_themes = {
        "Cancellation and Retention Handling",
        "Agent Courtesy and Empathy",
        "Resolution Quality and Ownership",
        "Agent Knowledge and Accuracy",
        "Language and Communication",
        "Response Time and Wait Time",
        "Chat and Bot Experience",
        "Process and Policy Friction",
        "General Service Dissatisfaction",
    }
    non_avoidable_themes = {
        "Pricing and Offer Competitiveness",
        "Technical Product or Device Issue",
        "Contact Channel Preference",
    }

    if theme == "Positive Service Experience" and has_positive_hint:
        return "Not Applicable"
    if theme in avoidable_themes:
        return "Avoidable"
    if theme in non_avoidable_themes:
        if any(hint in normalized for hint in NEGATIVE_SERVICE_HINTS):
            return "Avoidable"
        return "Non-Avoidable"
    if any(hint in normalized for hint in NEGATIVE_SERVICE_HINTS):
        return "Avoidable"
    return "Non-Avoidable"


def build_kpi(df: pd.DataFrame) -> pd.DataFrame:
    total = len(df)
    detractors = int((df["NPS Category"] == "Detractor").sum())
    passives = int((df["NPS Category"] == "Passive").sum())
    promoters = int((df["NPS Category"] == "Promoter").sum())
    actionable = df[df["NPS Category"].isin(["Detractor", "Passive"])]
    avoidable = int((actionable["Avoidable Impact"] == "Avoidable").sum())

    return pd.DataFrame(
        {
            "Metric": [
                "Total Responses",
                "Promoter %",
                "Passive %",
                "Detractor %",
                "Avoidable % (Passives + Detractors)",
                "NPS Score",
            ],
            "Value": [
                total,
                round((promoters / total) * 100, 2) if total else 0,
                round((passives / total) * 100, 2) if total else 0,
                round((detractors / total) * 100, 2) if total else 0,
                round((avoidable / len(actionable)) * 100, 2) if len(actionable) else 0,
                round(((promoters - detractors) / total) * 100, 2) if total else 0,
            ],
        }
    )


def build_insights(df: pd.DataFrame) -> list[dict[str, str]]:
    total = len(df)
    actionable = df[df["NPS Category"].isin(["Detractor", "Passive"])]
    detractors = df[df["NPS Category"] == "Detractor"]
    passives = df[df["NPS Category"] == "Passive"]

    if total == 0:
        return [{"Insights": "No responses were available in the uploaded workbook."}]

    top_detractor_theme = detractors["Theme"].value_counts().index[0] if not detractors.empty else "None"
    top_passive_theme = passives["Theme"].value_counts().index[0] if not passives.empty else "None"
    avoidable_actionable = int((actionable["Avoidable Impact"] == "Avoidable").sum())

    return [
        {"Insights": f"Analyzed {total} response(s) using Detractor 0-6, Passive 7-8, and Promoter 9-10 score bands."},
        {"Insights": f"Promoters are excluded from avoidable-impact scoring and treated as service-quality positive responses."},
        {"Insights": f"The top detractor theme is {top_detractor_theme}." if top_detractor_theme != "None" else "No detractor theme was detected."},
        {"Insights": f"The top passive theme is {top_passive_theme}." if top_passive_theme != "None" else "No passive theme was detected."},
        {"Insights": f"{avoidable_actionable} passive or detractor survey(s) were flagged as avoidable."},
    ]


def process_nps(input_file: str, progress_callback: Callable[[int, int], None] | None = None):
    file_name = os.path.basename(input_file)
    output_file = os.path.join("output_files", f"Output_{int(time.time())}_{file_name}")

    df = pd.read_excel(input_file)
    if df.empty:
        raise ValueError("The uploaded Excel file is empty.")

    score_column, comment_column = detect_columns(df)

    df["NPS Score"] = df[score_column].map(parse_score)
    df["NPS Category"] = df["NPS Score"].map(nps_category)
    df["Comment Text"] = df[comment_column].fillna("").astype(str).str.strip()
    df["Comment Text"] = df["Comment Text"].mask(df["Comment Text"] == "", "No Feedback written by customer")

    # Translation is intentionally restricted to the SA Question 6 comment column only.
    comments_for_translation = df["Comment Text"].replace("No Feedback written by customer", "")
    translation_lookup = translate_unique_comments(comments_for_translation, progress_callback=progress_callback)
    df["Translated_Text"] = comments_for_translation.map(lambda value: translation_lookup.get(value, str(value)))
    df["Translated_Text"] = df["Translated_Text"].mask(df["Comment Text"] == "No Feedback written by customer", "No Feedback written by customer")

    df["Sentiment"] = df["NPS Score"].map(sentiment_from_score)
    df["Theme"] = df.apply(
        lambda row: classify_theme(row["Comment Text"], row["Translated_Text"], row["NPS Score"]),
        axis=1,
    )
    df["Avoidable Impact"] = df.apply(
        lambda row: classify_avoidable(row["Theme"], row["Comment Text"], row["Translated_Text"], row["NPS Score"]),
        axis=1,
    )

    summary = (
        df.groupby(["NPS Category", "Theme", "Avoidable Impact"])
        .size()
        .reset_index(name="Count")
        .sort_values(["NPS Category", "Count"], ascending=[True, False])
    )

    focus_areas = (
        df[df["NPS Category"].isin(["Detractor", "Passive"])]
        .groupby(["NPS Category", "Theme"])
        .size()
        .reset_index(name="Count")
        .sort_values(["NPS Category", "Count"], ascending=[True, False])
    )

    avoidable_summary = (
        df[df["NPS Category"].isin(["Detractor", "Passive"])]
        .groupby(["NPS Category", "Avoidable Impact"])
        .size()
        .reset_index(name="Count")
        .rename(columns={"NPS Category": "Survey Type", "Avoidable Impact": "Impact Classification"})
        .sort_values(["Survey Type", "Impact Classification"])
    )

    kpi = build_kpi(df)
    insights = build_insights(df)
    synopsis = pd.DataFrame(insights)

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with pd.ExcelWriter(output_file) as writer:
        df.to_excel(writer, sheet_name="Detailed Data", index=False)
        summary.to_excel(writer, sheet_name="Summary", index=False)
        focus_areas.to_excel(writer, sheet_name="Focus Areas", index=False)
        avoidable_summary.to_excel(writer, sheet_name="Avoidable Impact", index=False)
        kpi.to_excel(writer, sheet_name="KPIs", index=False)
        synopsis.to_excel(writer, sheet_name="Synopsis", index=False)

    return {
        "output_file": output_file,
        "kpi": kpi.to_dict(orient="records"),
        "summary": summary.to_dict(orient="records"),
        "focus_areas": focus_areas.to_dict(orient="records"),
        "avoidable_summary": avoidable_summary.to_dict(orient="records"),
        "insights": insights,
    }
