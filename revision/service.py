from __future__ import annotations

import random


def build_revision_quiz(words: list[dict]):
    quiz_items = []
    meanings = [word.get("meaning", "") for word in words if word.get("meaning")]
    for word in words[:10]:
        distractors = [meaning for meaning in meanings if meaning != word.get("meaning")]
        random.shuffle(distractors)
        options = [word.get("meaning", "Meaning unavailable"), *distractors[:3]]
        random.shuffle(options)
        quiz_items.append({"word": word, "options": options})
    return quiz_items
