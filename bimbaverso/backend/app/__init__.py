from flask import Flask
from flask_cors import CORS

def create_app():
    app = Flask(__name__)
    CORS(app)

    from app.routes.chat import chat_bp
    from app.routes.programacion import programacion_bp

    app.register_blueprint(chat_bp)
    app.register_blueprint(programacion_bp)

    return app
