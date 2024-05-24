from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.environ.get('SECRET_KEY')

DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'crispy_forms',
    'crispy_bootstrap5',
    'anymail'
]


LOCAL_APPS = [
    'apps.accounts',
    'apps.users',
    'apps.server',
    'apps.devices',
    'apps.invites',
    'apps.portal',
    'apps.api',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
     'OPTIONS': {'min_length': 12}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'accounts.Account'

TEMPLATES[0]['DIRS'] = [BASE_DIR / 'templates']



CRISPY_ALLOWED_TEMPLATE_PACKS = 'bootstrap5'
CRISPY_TEMPLATE_PACK = 'bootstrap5'



# Where to go after login and logout
LOGIN_URL           = '/accounts/login/'
LOGIN_REDIRECT_URL  = '/dashboard/'
LOGOUT_REDIRECT_URL = '/accounts/login/'


# Email
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL')


# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,

    'formatters': {
        'verbose': {
            'format': '{asctime} {levelname} {name} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },

    'handlers': {
        'console': {
            'class':     'logging.StreamHandler',
            'formatter': 'simple',
        },
    },

    'loggers': {
        'wireguard': {
            'handlers':  ['console'],
            'level':     'DEBUG',
            'propagate': False,
        },
        'django': {
            'handlers':  ['console'],
            'level':     'INFO',
            'propagate': False,
        },
    },
}