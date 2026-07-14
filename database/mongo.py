from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

from flask import current_app, g

try:
    from pymongo import MongoClient
except Exception:  # pragma: no cover
    MongoClient = None


def init_db(app):
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    @app.before_request
    def attach_db():
        g.db = get_db()


def get_db():
    if "db" in g and g.db is not None:
        return g.db

    mongo_uri = current_app.config["MONGO_URI"]
    if MongoClient is None:
        raise RuntimeError("PyMongo is not installed. Please install pymongo to use MongoDB.")

    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=2500)
    db_name = mongo_uri.rsplit("/", 1)[-1].split("?")[0] or "mozhi_mate"
    g.mongo_client = client
    g.db = client[db_name]
    ensure_indexes(g.db)
    return g.db


def ensure_indexes(db):
    db.users.create_index("email", unique=True)
    db.words.create_index([("user_id", 1), ("word", 1)])
    db.words.create_index([("user_id", 1), ("timestamp", -1)])
    db.streak.create_index("user_id", unique=True)
    db.sessions.create_index("created_at", expireAfterSeconds=int(timedelta(days=7).total_seconds()))


def utc_now():
    return datetime.now(timezone.utc)
