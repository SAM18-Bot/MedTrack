import os
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-fallback-secret')
    TESTING = False
class TestConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    RATELIMIT_ENABLED = False
