import os

class Config:
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max
    ALLOWED_EXTENSIONS = {'csv'}
    SECRET_KEY = os.environ.get('SECRET_KEY', 'kopokop-finder-secret-key-dev')
