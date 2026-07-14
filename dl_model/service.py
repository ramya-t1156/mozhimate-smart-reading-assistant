from __future__ import annotations

from datetime import datetime, timezone

try:
    import numpy as np
except Exception:  # pragma: no cover
    np = None

try:
    from tensorflow.keras import Sequential
    from tensorflow.keras.layers import Dense, Input
except Exception:  # pragma: no cover
    Sequential = None
    Dense = None
    Input = None


def _build_demo_model():
    if Sequential is None or Dense is None or Input is None:
        return None
    model = Sequential(
        [
            Input(shape=(4,)),
            Dense(8, activation="relu"),
            Dense(6, activation="relu"),
            Dense(2, activation="sigmoid"),
        ]
    )
    model.compile(optimizer="adam", loss="mse")
    return model


MODEL = _build_demo_model()


def _hours_since_seen(last_seen):
    if not isinstance(last_seen, datetime):
        return 24.0

    if last_seen.tzinfo is None:
        last_seen = last_seen.replace(tzinfo=timezone.utc)

    return max((datetime.now(timezone.utc) - last_seen).total_seconds() / 3600, 0.0)


def score_word_difficulty(word_doc: dict):
    correct = float(word_doc.get("correct_count", 0))
    incorrect = float(word_doc.get("incorrect_count", 0))
    frequency = float(word_doc.get("frequency", 1))
    time_since_seen = _hours_since_seen(word_doc.get("last_seen"))

    heuristic_score = incorrect * 0.35 + time_since_seen * 0.02 - correct * 0.15 + max(0, 3 - frequency) * 0.2
    forgetting_probability = round(min(max(0.15 + heuristic_score, 0.05), 0.99), 2)

    if MODEL is not None and np is not None:
        features = np.array([[correct, incorrect, frequency, time_since_seen]], dtype=float)
        prediction = MODEL.predict(features, verbose=0)[0]
        forgetting_probability = round(float(prediction[1]), 2)

    if forgetting_probability < 0.35:
        difficulty = "Easy"
    elif forgetting_probability < 0.65:
        difficulty = "Medium"
    else:
        difficulty = "Hard"

    return {"difficulty_level": difficulty, "forgetting_probability": forgetting_probability}
