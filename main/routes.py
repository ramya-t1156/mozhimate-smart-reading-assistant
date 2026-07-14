import os

from flask import Blueprint, current_app, flash, g, jsonify, redirect, render_template, request, session, url_for
from werkzeug.utils import secure_filename

from auth.routes import hash_password, login_required, verify_password
from cv.service import extract_text_from_image, extract_text_from_pdf
from database.repositories import (
    delete_word,
    get_analytics_summary,
    get_recent_words,
    get_streak,
    update_quiz_result,
    update_user_password,
    upsert_word,
)
from dl_model.service import score_word_difficulty
from nlp.service import extract_candidate_words, get_bulk_word_details, get_word_details, process_speech_text
from revision.service import build_revision_quiz
from speech.service import synthesize_pronunciation

try:
    from bson import ObjectId
except Exception:  # pragma: no cover
    ObjectId = lambda value: value

main_bp = Blueprint("main", __name__)


def _get_revision_state(reset: bool = False):
    state = session.get("revision_quiz_state")
    if reset or not isinstance(state, dict):
        state = {"answered": 0, "correct": 0}
    return state


@main_bp.route("/")
def index():
    if session.get("user_id"):
        return redirect(url_for("main.dashboard"))
    return redirect(url_for("auth.login"))


@main_bp.route("/dashboard")
@login_required
def dashboard():
    analytics = get_analytics_summary(g.db, g.user["_id"])
    streak = get_streak(g.db, g.user["_id"])
    return render_template("dashboard.html", analytics=analytics, streak=streak)


@main_bp.route("/start-reading")
@login_required
def start_reading():
    return render_template("start_reading.html")


@main_bp.route("/start-reading/text")
@login_required
def text_mode_page():
    return render_template("mode_text.html")


@main_bp.route("/start-reading/speech")
@login_required
def speech_mode_page():
    return render_template("mode_speech.html")


@main_bp.route("/start-reading/image")
@login_required
def image_mode_page():
    return render_template("mode_image.html")


@main_bp.route("/start-reading/pdf")
@login_required
def pdf_mode_page():
    return render_template("mode_pdf.html")


@main_bp.route("/revision")
@login_required
def revision():
    reset_quiz = request.args.get("reset_quiz") == "1"
    active_view = request.args.get("view", "words")
    if active_view not in {"words", "quiz"}:
        active_view = "words"

    if reset_quiz:
        session["revision_quiz_state"] = {"answered": 0, "correct": 0}
        session.pop("revision_quiz_feedback", None)

    words = get_recent_words(g.db, g.user["_id"])
    quiz = build_revision_quiz(words)
    state = _get_revision_state(reset=reset_quiz)
    session["revision_quiz_state"] = state
    feedback = session.pop("revision_quiz_feedback", None)

    return render_template(
        "revision.html",
        words=words,
        quiz=quiz,
        active_view=active_view,
        quiz_feedback=feedback,
        quiz_state=state,
        total_quiz=len(quiz),
    )


@main_bp.route("/revision/delete", methods=["POST"])
@login_required
def revision_delete_word():
    word_id = request.form.get("word_id", "")
    active_view = request.form.get("active_view", "words")
    if not word_id:
        flash("Word could not be deleted.", "error")
        return redirect(url_for("main.revision", view=active_view))

    deleted = delete_word(g.db, g.user["_id"], word_id)
    flash("Word removed from revision list." if deleted else "Word could not be deleted.", "success" if deleted else "error")
    return redirect(url_for("main.revision", view=active_view))


@main_bp.route("/revision/quiz", methods=["POST"])
@login_required
def revision_quiz():
    word_id = request.form.get("word_id")
    submitted = request.form.get("selected_meaning", "")
    expected = request.form.get("expected_meaning", "")
    word_text = request.form.get("word", "Word")
    is_correct = submitted == expected
    updated = update_quiz_result(g.db, word_id, is_correct)
    if updated:
        scored = score_word_difficulty(updated)
        g.db.words.update_one(
            {"_id": ObjectId(word_id)},
            {
                "$set": {
                    "difficulty_level": scored["difficulty_level"],
                    "forgetting_probability": scored["forgetting_probability"],
                }
            },
        )

    state = _get_revision_state()
    state["answered"] = state.get("answered", 0) + 1
    if is_correct:
        state["correct"] = state.get("correct", 0) + 1
    session["revision_quiz_state"] = state
    session["revision_quiz_feedback"] = {
        "is_correct": is_correct,
        "word": word_text,
        "selected": submitted,
        "expected": expected,
        "answered": state["answered"],
        "correct": state["correct"],
    }

    flash("Correct answer!" if is_correct else "Answer recorded. Review the correct meaning below.", "success" if is_correct else "error")
    return redirect(url_for("main.revision", view="quiz"))


@main_bp.route("/analytics")
@login_required
def analytics():
    analytics_data = get_analytics_summary(g.db, g.user["_id"])
    return render_template("analytics.html", analytics=analytics_data)


@main_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not all([current_password, new_password, confirm_password]):
            flash("Fill in all password fields.", "error")
        elif not verify_password(current_password, g.user["password"]):
            flash("Current password is incorrect.", "error")
        elif len(new_password) < 6:
            flash("New password must be at least 6 characters.", "error")
        elif new_password != confirm_password:
            flash("New password and confirm password do not match.", "error")
        else:
            update_user_password(g.db, str(g.user["_id"]), hash_password(new_password))
            flash("Password updated successfully.", "success")
            return redirect(url_for("main.profile"))

    streak = get_streak(g.db, g.user["_id"])
    return render_template("profile.html", streak=streak)


@main_bp.route("/api/text-meaning", methods=["POST"])
@login_required
def text_meaning():
    word = request.json.get("word", "")
    details = get_word_details(word)
    if details.get("word"):
        stored = upsert_word(g.db, g.user["_id"], details)
        scored = score_word_difficulty(stored)
        g.db.words.update_one(
            {"_id": stored["_id"]},
            {"$set": {"difficulty_level": scored["difficulty_level"], "forgetting_probability": scored["forgetting_probability"]}},
        )
        details.update(scored)
    return jsonify(details)


@main_bp.route("/get_meaning")
@login_required
def get_meaning():
    word = request.args.get("word", "")
    details = get_word_details(word)
    if details.get("error"):
        return jsonify(details), 400

    if details.get("word"):
        stored = upsert_word(g.db, g.user["_id"], details)
        scored = score_word_difficulty(stored)
        g.db.words.update_one(
            {"_id": stored["_id"]},
            {
                "$set": {
                    "difficulty_level": scored["difficulty_level"],
                    "forgetting_probability": scored["forgetting_probability"],
                }
            },
        )
        details.update(scored)

    return jsonify(details)


@main_bp.route("/api/pronounce", methods=["POST"])
@login_required
def pronounce_word():
    word = request.json.get("word", "")
    return jsonify({"audio_status": synthesize_pronunciation(word)})


@main_bp.route("/api/speech-meaning", methods=["POST"])
@login_required
def speech_meaning():
    transcript = request.json.get("transcript", "")
    candidates = process_speech_text(transcript)
    results = []
    for details in get_bulk_word_details(candidates, limit=8):
        stored = upsert_word(g.db, g.user["_id"], details)
        scored = score_word_difficulty(stored)
        g.db.words.update_one(
            {"_id": stored["_id"]},
            {"$set": {"difficulty_level": scored["difficulty_level"], "forgetting_probability": scored["forgetting_probability"]}},
        )
        details.update(scored)
        results.append(details)
    return jsonify({"words": results, "live_words": candidates[:12]})


@main_bp.route("/api/image-ocr", methods=["POST"])
@login_required
def image_ocr():
    image = request.files.get("image")
    if not image:
        return jsonify({"error": "No image uploaded."}), 400

    filename = secure_filename(image.filename)
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
    image.save(path)
    result = extract_text_from_image(path)
    return jsonify(result)


@main_bp.route("/api/pdf-ocr", methods=["POST"])
@login_required
def pdf_ocr():
    pdf = request.files.get("pdf")
    if not pdf:
        return jsonify({"error": "No PDF uploaded."}), 400

    filename = secure_filename(pdf.filename)
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
    pdf.save(path)
    result = extract_text_from_pdf(path)
    difficult_words = extract_candidate_words(result.get("text", ""))
    return jsonify({"text": result.get("text", ""), "words": difficult_words[:30], "warning": result.get("warning")})


@main_bp.route("/api/store-word", methods=["POST"])
@login_required
def store_word():
    word = request.json.get("word", "")
    details = get_word_details(word)
    if details.get("word"):
        stored = upsert_word(g.db, g.user["_id"], details)
        return jsonify({"stored": bool(stored), "word": details})
    return jsonify({"stored": False, "word": details}), 400
