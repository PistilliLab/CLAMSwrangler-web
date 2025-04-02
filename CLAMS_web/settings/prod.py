"""
Production settings to override certain base settings.

To enable run the following command:
export DJANGO_SETTINGS_MODULE="CLAMS_web.settings.prod"
"""
from environs import Env
from .base import *

env = Env()
env.read_env()

SECRET_KEY = env.str('PROD_SECRET_KEY')

DEBUG = False

ALLOWED_HOSTS = ['clams.stuartclayton.me', '127.0.0.1']

SESSION_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_PRELOAD = True
SECURE_HSTS_INCLUDE_SUBDOMAINS = True

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'WARNING',
            'class': 'logging.FileHandler',
            'filename': '/var/log/clamswrangler/django.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'WARNING',
            'propagate': True,
        },
    },
}
