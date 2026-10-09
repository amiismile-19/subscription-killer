from flask import Flask, jsonify
from flask_cors import CORS
from config import Config
from database import init_db, close_db
from routes.subscriptions import bp as subscriptions_bp
from routes.cancellations import bp as cancellations_bp
from routes.notifications import bp as notifications_bp
from routes.scores import bp as scores_bp
from routes.voice import bp as voice_bp
from services.scheduler import start_scheduler

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    CORS(app, resources={r"/*": {"origins": "*"}})

    init_db(app.config["DATABASE_PATH"])
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
            "version": "2.0.0",
            "mode": app.config.get("APP_MODE", "demo"),
            "features": [
                "Transaction-ID-based tracking (No bank details required)",
                "Direct Cancellation with instant receipt",
                "Custom user-input notifications",
                "Cancellation deadline calculations & urgency",
                "Credit scores allotted on cancellation and upgrade",
                "Multi-language Voice ASR & TTS (EN, HI, MR, TA, TE, BN, GU) via Bhashini & Whisper"
            ]
        })

    @app.get("/health")
    @app.get("/api/health")
    def health():
        return jsonify({"ok": True, "status": "healthy"})


    if app.config.get("ENABLE_SCHEDULER"):
        start_scheduler(app)

    return app

app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=app.config.get("DEBUG", False))
