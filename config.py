import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev_key_fallback_123'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///crm.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = 'uploads'
