import os

files = {
    "requirements.txt": """Flask==3.0.0
Flask-WTF==1.2.1
python-dotenv==1.0.0
boto3==1.33.0
botocore==1.33.0
pytest==7.4.3
gunicorn==21.2.0
reportlab==4.0.7
""",
    ".env.example": """FLASK_APP=run.py
FLASK_ENV=development
SECRET_KEY=replace-this-with-a-secure-secret
AWS_DEFAULT_REGION=us-east-1
""",
    ".gitignore": """venv/
__pycache__/
*.pyc
.env
.pytest_cache/
""",
    "run.py": """from app import create_app
app = create_app()
if __name__ == '__main__':
    app.run(debug=True)
""",
    "app/__init__.py": """from flask import Flask, render_template
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
""",
    "app/config.py": """import os
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-fallback-secret')
    TESTING = False
class TestConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
""",
    "app/extensions.py": """from flask_wtf.csrf import CSRFProtect
csrf = CSRFProtect()
""",
    "app/blueprints/__init__.py": "",
    "app/blueprints/public.py": """from flask import Blueprint, render_template
public_bp = Blueprint('public', __name__)
@public_bp.route('/')
def index(): return render_template('public/landing.html')
""",
    "app/blueprints/auth.py": "from flask import Blueprint\nauth_bp = Blueprint('auth', __name__)",
    "app/blueprints/patient.py": "from flask import Blueprint\npatient_bp = Blueprint('patient', __name__)",
    "app/blueprints/doctor.py": "from flask import Blueprint\ndoctor_bp = Blueprint('doctor', __name__)",
    "app/blueprints/admin.py": "from flask import Blueprint\nadmin_bp = Blueprint('admin', __name__)",
    "app/blueprints/support.py": "from flask import Blueprint\nsupport_bp = Blueprint('support', __name__)",
    "app/blueprints/api.py": "from flask import Blueprint\napi_bp = Blueprint('api', __name__)",
    "app/static/css/style.css": """:root { --med-primary: #0ea5e9; --med-secondary: #0284c7; --med-bg: #f8fafc; --med-text: #334155; }
body { background-color: var(--med-bg); color: var(--med-text); font-family: 'Segoe UI', system-ui, sans-serif; display: flex; flex-direction: column; min-height: 100vh; }
.navbar-brand { color: var(--med-primary) !important; font-size: 1.5rem; font-weight: bold; }
""",
    "app/static/js/main.js": "console.log('MedTrack loaded');\n",
    "app/templates/base.html": """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}MedTrack{% endblock %}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-light bg-white border-bottom">
        <div class="container">
            <a class="navbar-brand" href="/">MedTrack</a>
        </div>
    </nav>
    <main class="container my-4">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ 'success' if category == 'success' else 'danger' }} alert-dismissible fade show">{{ message }}<button type="button" class="btn-close" data-bs-dismiss="alert"></button></div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        {% block content %}{% endblock %}
    </main>
    <footer class="bg-light py-4 mt-auto border-top text-center text-muted">
        <div class="container"><small>&copy; 2026 MedTrack. All rights reserved.</small></div>
    </footer>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script src="{{ url_for('static', filename='js/main.js') }}"></script>
</body>
</html>""",
    "app/templates/public/landing.html": """{% extends 'base.html' %}
{% block content %}
<div class="text-center py-5">
    <h1>Welcome to MedTrack</h1>
    <p class="lead">Your complete cloud healthcare platform.</p>
</div>
{% endblock %}""",
    "tests/conftest.py": """import pytest
from app import create_app
from app.config import TestConfig

@pytest.fixture
def app():
    app = create_app(TestConfig)
    yield app

@pytest.fixture
def client(app):
    return app.test_client()""",
    "tests/test_scaffold.py": """def test_app_starts_and_index_returns_200(client):
    res = client.get('/')
    assert res.status_code == 200
    assert b'Welcome to MedTrack' in res.data

def test_404_error_handler(client):
    res = client.get('/non-existent-route')
    assert res.status_code == 404
    assert b'Error 404' in res.data""",
    "README.md": """# MedTrack

Production-Grade Cloud Healthcare Management System (AWS Cloud Practitioner Capstone).

## Setup
1. Create virtual environment: `python -m venv venv`
2. Activate it: `.\\venv\\Scripts\\Activate.ps1`
3. Install dependencies: `pip install -r requirements.txt`
4. Run the app: `flask run`

## Phases Completed
- **Phase 1 (Scaffold):** Set up Flask application factory, blueprints, error pages, and design system.
"""
}

errors = ['400', '401', '403', '404', '429', '500']
for e in errors:
    files[f"app/templates/errors/{e}.html"] = f"{{% extends 'base.html' %}}\n{{% block content %}}\n<div class='text-center py-5'><h1>Error {e}</h1><p>Something went wrong.</p><a href='/' class='btn btn-primary'>Go Home</a></div>\n{{% endblock %}}"

for path, content in files.items():
    dir_name = os.path.dirname(path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
