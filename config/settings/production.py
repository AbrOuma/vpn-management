import os
import environ
from .base import *

env = environ.Env()
environ.Env.read_env(BASE_DIR / '.env')

SECRET_KEY    = env('SECRET_KEY')
DEBUG         = False
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS')

DATABASES = {
    'default': env.db('DATABASE_URL')
}

# Email
EMAIL_BACKEND      = 'anymail.backends.sendgrid.EmailBackend'
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL')
ANYMAIL = {
    'SENDGRID_API_KEY': env('SENDGRID_API_KEY'),
}

SECURE_SSL_REDIRECT            = True
SECURE_HSTS_SECONDS            = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SESSION_COOKIE_SECURE          = True
CSRF_COOKIE_SECURE             = True
X_FRAME_OPTIONS                = 'DENY'

# Static files served by whitenoise
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
STATIC_ROOT     = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'