import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload size
    
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=60)
    
    TESTING = False

class TestConfig(Config):
    SECRET_KEY = 'test-secret-key'
    TESTING = True
    WTF_CSRF_ENABLED = False
    RATELIMIT_ENABLED = False
