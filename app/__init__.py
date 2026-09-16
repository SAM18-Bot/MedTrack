from flask import Flask, render_template
from app.config import Config
from app.extensions import csrf

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    csrf.init_app(app)

    from app.blueprints.public import public_bp
    from app.blueprints.auth import auth_bp
    from app.blueprints.patient import patient_bp
    from app.blueprints.doctor import doctor_bp
    from app.blueprints.admin import admin_bp
    from app.blueprints.support import support_bp
    from app.blueprints.api import api_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(patient_bp, url_prefix='/patient')
    app.register_blueprint(doctor_bp, url_prefix='/doctor')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(support_bp, url_prefix='/support')
    app.register_blueprint(api_bp, url_prefix='/api')

    register_error_handlers(app)
    return app

def register_error_handlers(app):
    @app.errorhandler(400)
    def bad_request(e): return render_template('errors/400.html'), 400
    @app.errorhandler(401)
    def unauthorized(e): return render_template('errors/401.html'), 401
    @app.errorhandler(403)
    def forbidden(e): return render_template('errors/403.html'), 403
    @app.errorhandler(404)
    def not_found(e): return render_template('errors/404.html'), 404
    @app.errorhandler(429)
    def too_many_requests(e): return render_template('errors/429.html'), 429
    @app.errorhandler(500)
    def internal_server_error(e): return render_template('errors/500.html'), 500
