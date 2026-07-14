import os

from flask import Flask

from auth.routes import auth_bp
from database.mongo import init_db
from main.routes import main_bp


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "mozhi-mate-dev-secret")
    app.config["MONGO_URI"] = os.getenv("MONGO_URI", "mongodb://localhost:27017/mozhi_mate")
    app.config["UPLOAD_FOLDER"] = os.path.join(app.root_path, "uploads")
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    init_db(app)
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
