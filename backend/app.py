import os
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["HF_HUB_DISABLE_SYMLINKS"] = "1"

from flask import Flask
from flask_cors import CORS

from routes.analyze_routes import analyze_bp
from routes.compare_routes import compare_bp
from routes.download_routes import download_bp
from routes.auth_routes import auth_bp
from routes.fake_detection_routes import fake_bp
from routes.bullet_rewrite import rewrite_bullets

app = Flask(__name__)
CORS(app)

# Register Blueprints
app.register_blueprint(analyze_bp)
app.register_blueprint(compare_bp)
app.register_blueprint(download_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(fake_bp)

try:

    app.register_blueprint(rewrite_bullets)
except Exception as exc:
    print(f"[startup] Bullet rewriting unavailable: {exc}")

if __name__ == "__main__":

    app.run(debug=True, use_reloader=False)
    