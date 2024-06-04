import environ
from .base import *

env = environ.Env()
environ.Env.read_env(BASE_DIR / '.env')

SECRET_KEY = env('SECRET_KEY')

DEBUG = True

ALLOWED_HOSTS = ['*']

DATABASES = {
    'default': env.db('DATABASE_URL')
}

# Real email sending via SendGrid
EMAIL_BACKEND      = 'anymail.backends.sendgrid.EmailBackend'
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL')
ANYMAIL = {
    'SENDGRID_API_KEY': env('SENDGRID_API_KEY'),
}

STATIC_ROOT = BASE_DIR / 'staticfiles'
