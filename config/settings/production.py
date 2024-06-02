import os
import environ
from .base import *

env = environ.Env()
environ.Env.read_env(BASE_DIR / '.env', overwrite=True)

SECRET_KEY    = env('SECRET_KEY')
DEBUG         = False
ALLOWED_HOSTS = ['*']

DATABASES = {
    'default': env.db('DATABASE_URL')
}

# Email
EMAIL_BACKEND      = 'anymail.backends.sendgrid.EmailBackend'
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL')
ANYMAIL = {
    'SENDGRID_API_KEY': env('SENDGRID_API_KEY'),
}

# Railway handles SSL termination — don't redirect
SECURE_PROXY_SSL_HEADER        = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT            = False
SESSION_COOKIE_SECURE          = True
CSRF_COOKIE_SECURE             = True
X_FRAME_OPTIONS                = 'DENY'

CSRF_TRUSTED_ORIGINS = [
    'https://vpn-management-production.up.railway.app',
]

# Static files served by whitenoise
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
STATIC_ROOT     = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'