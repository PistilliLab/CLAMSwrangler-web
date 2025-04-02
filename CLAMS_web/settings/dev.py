"""
Development settings to override certain base settings.

To enable run the following command:
export DJANGO_SETTINGS_MODULE="CLAMS_web.settings.dev"
"""
from environs import Env
from .base import *

env = Env()
env.read_env()

SECRET_KEY = env.str('DEV_SECRET_KEY')

DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1']

SESSION_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False
CSRF_COOKIE_SECURE = False

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            # 'level': 'DEBUG',
        },
    },
    'root': {'level': 'INFO'},
}