from flask import Flask
from flask_sqlalchemy import SQLAlchemy

from app.config import Config

db = SQLAlchemy()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)

    from app.routes.patients import bp as patients_bp
    from app.routes.doctors import bp as doctors_bp
    from app.routes.appointments import bp as appointments_bp
    from app.routes.records import bp as records_bp
    from app.routes.exports import bp as exports_bp

    app.register_blueprint(patients_bp, url_prefix='/api')
    app.register_blueprint(doctors_bp, url_prefix='/api')
    app.register_blueprint(appointments_bp, url_prefix='/api')
    app.register_blueprint(records_bp, url_prefix='/api')
    app.register_blueprint(exports_bp, url_prefix='/api')

    from app.utils.errors import register_error_handlers
    register_error_handlers(app)

    with app.app_context():
        db.create_all()
        from app.utils.init_data import init_doctors
        init_doctors()

    return app
