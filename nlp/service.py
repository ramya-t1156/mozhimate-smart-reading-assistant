from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

import requests

try:
    import nltk
    from nltk.corpus import stopwords, wordnet as wn
    from nltk.stem import WordNetLemmatizer
except Exception:  # pragma: no cover
    nltk = None
    stopwords = None
    wn = None
    WordNetLemmatizer = None


WIKI_SUMMARY_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/{}"
WORD_CACHE: dict[str, dict] = {}
CACHE_LOCK = Lock()
EXECUTOR = ThreadPoolExecutor(max_workers=8)
MIN_WORD_LENGTH = 3
NLTK_READY = False
DEFAULT_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "but", "by", "for", "from", "had", "has", "have",
    "he", "her", "hers", "him", "his", "i", "if", "in", "into", "is", "it", "its", "me", "my", "of", "on",
    "or", "our", "ours", "she", "so", "that", "the", "their", "them", "there", "they", "this", "to", "too",
    "us", "was", "we", "were", "what", "when", "where", "which", "who", "will", "with", "you", "your",
}
STOPWORD_SET: set[str] = set(DEFAULT_STOPWORDS)
HTTP = requests.Session()
HTTP.headers.update({"User-Agent": "MozhiMate/1.0"})
LEMMATIZER = WordNetLemmatizer() if WordNetLemmatizer is not None else None


def _safe_download_nltk():
    global NLTK_READY, STOPWORD_SET
    if nltk is None or NLTK_READY:
        return
    try:
        nltk.data.find("corpora/wordnet")
    except LookupError:
        nltk.download("wordnet", quiet=True)
    try:
        nltk.data.find("corpora/omw-1.4")
    except LookupError:
        nltk.download("omw-1.4", quiet=True)
    try:
        nltk.data.find("corpora/stopwords")
    except LookupError:
        nltk.download("stopwords", quiet=True)

    if stopwords is not None:
        STOPWORD_SET = set(stopwords.words("english"))
    NLTK_READY = True


def clean_word(word: str) -> str:
    return re.sub(r"[^A-Za-z-]", "", word or "").lower().strip()


def is_ignored_word(word: str) -> bool:
    cleaned = clean_word(word)
    if len(cleaned) < MIN_WORD_LENGTH:
        return True
    _safe_download_nltk()
    return cleaned in STOPWORD_SET


def normalize_word(word: str) -> str:
    cleaned = clean_word(word)
    if len(cleaned) < MIN_WORD_LENGTH:
        return ""
    _safe_download_nltk()
    if cleaned in STOPWORD_SET:
        return ""
    if LEMMATIZER is None:
        return cleaned
    return LEMMATIZER.lemmatize(cleaned)


def _wordnet_details(normalized: str) -> dict | None:
    if wn is None:
        return None

    _safe_download_nltk()
    candidate_forms = [normalized]
    for pos in [wn.NOUN, wn.VERB, wn.ADJ, wn.ADV]:
        lemma = wn.morphy(normalized, pos)
        if lemma and lemma not in candidate_forms:
            candidate_forms.append(lemma)

    synsets = []
    resolved = normalized
    for form in candidate_forms:
        synsets = wn.synsets(form)
        if synsets:
            resolved = form
            break

    if not synsets:
        return None

    primary = synsets[0]
    examples = primary.examples()
    synonyms = set()
    antonyms = set()
    for lemma in primary.lemmas():
        synonyms.add(lemma.name().replace("_", " "))
        for antonym in lemma.antonyms():
            antonyms.add(antonym.name().replace("_", " "))

    return {
        "word": normalized,
        "meaning": primary.definition(),
        "example": examples[0] if examples else f"The word '{resolved}' appeared in your reading session.",
        "synonyms": sorted(synonyms)[:6],
        "antonyms": sorted(antonyms)[:6],
        "source": "wordnet",
    }


def _wikipedia_details(normalized: str) -> dict:
    details = {
        "word": normalized,
        "meaning": "Meaning unavailable for this word right now.",
        "example": "Try another form of the word or use it inside a sentence.",
        "synonyms": [],
        "antonyms": [],
        "source": "fallback",
    }
    try:
        response = HTTP.get(WIKI_SUMMARY_URL.format(normalized), timeout=0.9)
        if response.ok:
            data = response.json()
            extract = data.get("extract", "")
            if extract:
                details["meaning"] = extract
                details["example"] = f"{normalized.capitalize()} is commonly used in reading and conversation."
                details["source"] = "wikipedia"
    except Exception:
        pass
    return details


def get_word_details(word: str) -> dict:
    cleaned = clean_word(word)
    if len(cleaned) < MIN_WORD_LENGTH:
        return {"error": "Please enter a valid word with at least 3 letters."}
    if is_ignored_word(cleaned):
        return {"error": "This word is too common to analyze usefully in Speech Mode."}

    normalized = normalize_word(cleaned)
    if not normalized:
        return {"error": "Please enter a more specific word."}

    with CACHE_LOCK:
        cached = WORD_CACHE.get(normalized)
    if cached:
        return dict(cached)

    details = _wordnet_details(normalized)
    if details is None:
        details = _wikipedia_details(normalized)

    with CACHE_LOCK:
        WORD_CACHE[normalized] = dict(details)
    return details


def get_bulk_word_details(words: list[str], limit: int = 8):
    candidates = []
    seen = set()
    for word in words:
        normalized = normalize_word(word)
        if normalized and normalized not in seen:
            seen.add(normalized)
            candidates.append(normalized)
        if len(candidates) >= limit:
            break

    futures = [EXECUTOR.submit(get_word_details, word) for word in candidates]
    results = []
    for future in as_completed(futures):
        data = future.result()
        if not data.get("error"):
            results.append(data)
    results.sort(key=lambda item: candidates.index(item["word"]))
    return results


def process_speech_text(transcript: str):
    tokens = re.findall(r"[A-Za-z]+", (transcript or "").lower())
    cleaned = []
    for token in tokens:
        normalized = normalize_word(token)
        if normalized:
            cleaned.append(normalized)
    return cleaned


def extract_candidate_words(text: str):
    words = process_speech_text(text)
    unique = []
    seen = set()
    for word in words:
        if word not in seen:
            seen.add(word)
            unique.append(word)
    return unique
