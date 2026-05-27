from flask import Flask
from flask_cors import CORS

from routes.analyze_routes import analyze_bp
from routes.compare_routes import compare_bp
from routes.download_routes import download_bp
from routes.auth_routes import auth_bp

app = Flask(__name__)
CORS(app)

# Register Blueprints
app.register_blueprint(analyze_bp)
app.register_blueprint(compare_bp)
app.register_blueprint(download_bp)
app.register_blueprint(auth_bp)

if __name__ == "__main__":
    app.run(debug=True)