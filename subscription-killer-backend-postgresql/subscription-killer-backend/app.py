from flask import Flask, jsonify
from datetime import date, datetime, time
from decimal import Decimal
from config import Config
from database import init_db, close_db
from routes.subscriptions import bp as subscriptions_bp
from routes.cancellations import bp as cancellations_bp
from routes.notifications import bp as notifications_bp
from routes.scores import bp as scores_bp
from routes.voice import bp as voice_bp
from services.scheduler import start_scheduler

class AppJSONProvider(__import__("flask").json.provider.DefaultJSONProvider):
    @staticmethod
    def default(value):
        if isinstance(value, (date, datetime, time)):
            return value.isoformat()
        if isinstance(value, Decimal):
            return float(value)
        return __import__("flask").json.provider.DefaultJSONProvider.default(value)

def create_app():
    app = Flask(__name__)
    app.json = AppJSONProvider(app)
    app.config.from_object(Config)
    init_db(app.config["DATABASE_URL"])
    app.teardown_appcontext(close_db)

    app.register_blueprint(subscriptions_bp, url_prefix="/api/subscriptions")
    app.register_blueprint(cancellations_bp, url_prefix="/api")
    app.register_blueprint(notifications_bp, url_prefix="/api")
    app.register_blueprint(scores_bp, url_prefix="/api")
    app.register_blueprint(voice_bp, url_prefix="/api/voice")

    @app.get("/")
    def index():
        return jsonify({
            "name": "Subscription Killer API",
            "status": "running",
            "mode": app.config["APP_MODE"],
            "docs": "See README.md for endpoint examples"
        })

    @app.get("/health")
    def health():
        return jsonify({"ok": True})

    if app.config["ENABLE_SCHEDULER"]:
        start_scheduler(app)

    return app

app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=app.config["DEBUG"])
