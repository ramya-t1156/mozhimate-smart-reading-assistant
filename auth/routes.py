from functools import wraps

from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from database.repositories import create_user, find_user_by_email, find_user_by_id, update_streak

try:
    import bcrypt
except Exception:  # pragma: no cover
    bcrypt = None

try:
    from pymongo.errors import DuplicateKeyError
except Exception:  # pragma: no cover
    class DuplicateKeyError(Exception):
        pass


auth_bp = Blueprint("auth", __name__)


def hash_password(password: str) -> str:
    if bcrypt is not None:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    return generate_password_hash(password)


def verify_password(password: str, stored_hash: str) -> bool:
    if bcrypt is not None and not stored_hash.startswith("scrypt:") and not stored_hash.startswith("pbkdf2:"):
        return bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8"))
    return check_password_hash(stored_hash, password)


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)

    return wrapped_view


@auth_bp.before_app_request
def load_logged_in_user():
    user_id = session.get("user_id")
    g.user = find_user_by_id(g.db, user_id) if user_id else None


@auth_bp.route("/auth-success")
def auth_success():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))
    action = request.args.get("action", "login")
    action_label = "Account Ready" if action == "signup" else "Signed In"
    return render_template("auth_success.html", action_label=action_label)


@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not all([name, email, password]):
            flash("Please fill in all fields.", "error")
            return render_template("signup.html")

        password_hash = hash_password(password)
        try:
            user = create_user(g.db, name, email, password_hash)
        except DuplicateKeyError:
            flash("An account with that email already exists.", "error")
            return render_template("signup.html")

        session["user_id"] = str(user["_id"])
        update_streak(g.db, user["_id"])
        return redirect(url_for("auth.auth_success", action="signup"))

    return render_template("signup.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        user = find_user_by_email(g.db, email)
        if not user or not verify_password(password, user["password"]):
            flash("Invalid email or password.", "error")
            return render_template("login.html")

        session["user_id"] = str(user["_id"])
        update_streak(g.db, user["_id"])
        return redirect(url_for("auth.auth_success", action="login"))

    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
