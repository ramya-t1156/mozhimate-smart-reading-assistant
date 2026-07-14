from __future__ import annotations

from datetime import timedelta

try:
    from bson import ObjectId
except Exception:  # pragma: no cover
    ObjectId = lambda value: value

try:
    from pymongo import DESCENDING
except Exception:  # pragma: no cover
    DESCENDING = -1

from database.mongo import utc_now


def create_user(db, name: str, email: str, password_hash: str):
    payload = {
        "name": name,
        "email": email.lower().strip(),
        "password": password_hash,
        "created_at": utc_now(),
    }
    result = db.users.insert_one(payload)
    db.streak.insert_one(
        {
            "user_id": result.inserted_id,
            "current_streak": 1,
            "last_active_date": utc_now().date().isoformat(),
        }
    )
    return db.users.find_one({"_id": result.inserted_id})


def find_user_by_email(db, email: str):
    return db.users.find_one({"email": email.lower().strip()})


def find_user_by_id(db, user_id: str):
    return db.users.find_one({"_id": ObjectId(user_id)})


def update_user_password(db, user_id: str, password_hash: str):
    db.users.update_one({"_id": ObjectId(user_id)}, {"$set": {"password": password_hash}})
    return db.users.find_one({"_id": ObjectId(user_id)})


def update_streak(db, user_id):
    streak = db.streak.find_one({"user_id": user_id})
    today = utc_now().date()
    yesterday = today - timedelta(days=1)
    if not streak:
        db.streak.insert_one(
            {
                "user_id": user_id,
                "current_streak": 1,
                "last_active_date": today.isoformat(),
            }
        )
        return 1

    last_active = streak.get("last_active_date")
    if last_active == today.isoformat():
        return streak.get("current_streak", 0)

    if last_active == yesterday.isoformat():
        current_streak = streak.get("current_streak", 0) + 1
    else:
        current_streak = 1

    db.streak.update_one(
        {"user_id": user_id},
        {"$set": {"current_streak": current_streak, "last_active_date": today.isoformat()}},
    )
    return current_streak


def get_streak(db, user_id):
    streak = db.streak.find_one({"user_id": user_id}) or {}
    return streak.get("current_streak", 0)


def upsert_word(db, user_id, word_data: dict):
    word = word_data["word"]
    existing = db.words.find_one({"user_id": user_id, "word": word})
    now = utc_now()
    if existing:
        db.words.update_one(
            {"_id": existing["_id"]},
            {
                "$set": {
                    "meaning": word_data.get("meaning", existing.get("meaning")),
                    "example": word_data.get("example", existing.get("example")),
                    "synonyms": word_data.get("synonyms", existing.get("synonyms", [])),
                    "antonyms": word_data.get("antonyms", existing.get("antonyms", [])),
                    "last_seen": now,
                },
                "$inc": {"frequency": 1},
            },
        )
        return db.words.find_one({"_id": existing["_id"]})

    payload = {
        "user_id": user_id,
        "word": word,
        "meaning": word_data.get("meaning", "Meaning unavailable"),
        "example": word_data.get("example", ""),
        "synonyms": word_data.get("synonyms", []),
        "antonyms": word_data.get("antonyms", []),
        "timestamp": now,
        "last_seen": now,
        "frequency": 1,
        "correct_count": 0,
        "incorrect_count": 0,
        "consecutive_correct_days": 0,
        "mastered": False,
        "difficulty_level": "Medium",
        "forgetting_probability": 0.5,
    }
    result = db.words.insert_one(payload)
    return db.words.find_one({"_id": result.inserted_id})


def delete_word(db, user_id, word_id: str):
    result = db.words.delete_one({"_id": ObjectId(word_id), "user_id": user_id})
    return result.deleted_count > 0


def get_recent_words(db, user_id, days=3):
    cutoff = utc_now() - timedelta(days=days)
    return list(
        db.words.find({"user_id": user_id, "last_seen": {"$gte": cutoff}}).sort("last_seen", DESCENDING)
    )


def update_quiz_result(db, word_id: str, is_correct: bool):
    word = db.words.find_one({"_id": ObjectId(word_id)})
    if not word:
        return None

    update = {
        "$inc": {"correct_count": 1 if is_correct else 0, "incorrect_count": 0 if is_correct else 1},
        "$set": {"last_seen": utc_now()},
    }

    consecutive_days = word.get("consecutive_correct_days", 0)
    if is_correct:
        consecutive_days += 1
    else:
        consecutive_days = 0

    update["$set"]["consecutive_correct_days"] = consecutive_days
    update["$set"]["mastered"] = consecutive_days >= 3
    db.words.update_one({"_id": word["_id"]}, update)
    return db.words.find_one({"_id": word["_id"]})


def get_analytics_summary(db, user_id):
    words = list(db.words.find({"user_id": user_id}))
    total_words = len(words)
    total_correct = sum(word.get("correct_count", 0) for word in words)
    total_incorrect = sum(word.get("incorrect_count", 0) for word in words)
    total_attempts = total_correct + total_incorrect
    accuracy = round((total_correct / max(total_attempts, 1)) * 100, 2)
    difficulty_distribution = {"Easy": 0, "Medium": 0, "Hard": 0}
    for word in words:
        difficulty_distribution[word.get("difficulty_level", "Medium")] += 1

    return {
        "total_words": total_words,
        "quiz_accuracy": accuracy,
        "quiz_correct": total_correct,
        "quiz_incorrect": total_incorrect,
        "quiz_attempts": total_attempts,
        "mastered_words": sum(1 for word in words if word.get("mastered")),
        "time_spent_minutes": total_words * 2,
        "difficulty_distribution": difficulty_distribution,
        "recent_words": words[-7:],
    }
