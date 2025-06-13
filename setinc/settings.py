import os
import sys
from os import environ, path
from datetime import timedelta

import redis
from firebase_admin import initialize_app

BASE_DIR = path.dirname(path.dirname(path.abspath(__file__)))

SECRET_KEY = environ.get('SECRET_KEY',
                         "UtXxcyXkFnktfTVfQnYMNcNjbeNhoDAARwIEynoFeESwASfxNPJRELMpCFwI")

DEBUG = environ.get('DEBUG', False)
THUMBNAIL_DEBUG = DEBUG

ALLOWED_HOSTS = [ '*']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'HOST': environ.get('DB_HOST'),
        'PORT': environ.get('DB_PORT'),
        'NAME': environ.get('DB_DATABASE'),
        'USER': environ.get('DB_USERNAME'),
        'PASSWORD': environ.get('DB_PASSWORD'),
    }
}
STORAGE_PATHS = {'BASE': ''}

STORAGE_PATHS['IMAGES'] = path.join(STORAGE_PATHS['BASE'], 'images')
STORAGE_PATHS['FILES'] = path.join(STORAGE_PATHS['BASE'], 'files')

# STORAGE_PATHS['IMAGES_SOMETHING'] = path.join(STORAGE_PATHS['IMAGES'], 'something')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'django_dramatiq',
    'rest_framework',
    'drf_yasg',
    'corsheaders',

    'storages',
    'api',
    'rest_framework_simplejwt',
    'fcm_django',
    'task',
    'alarm'
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'setinc.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            path.abspath(path.join(BASE_DIR, 'templates')),
        ],
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

WSGI_APPLICATION = 'setinc.wsgi.application'

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 6,
        },
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        # 'file': {
        #     'level': 'DEBUG',
        #     'class': 'logging.FileHandler',
        #     'filename': path.join(BASE_DIR, 'log/debug.log'),
        # },
        'console-stdout': {
            'class': 'logging.StreamHandler',
            'stream': sys.stdout,
        },
    },
    'loggers': {
        # 'django-file': {
        #     'handlers': ['file'],
        #     'level': 'DEBUG',
        #     'propagate': True,
        # },
        'django.request': {
            'handlers': ['console-stdout'],
        },
    },
}

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Australia/Sydney'

USE_I18N = True

USE_L10N = True

USE_TZ = False

SITE_ID = 1

REST_FRAMEWORK = {
    'EXCEPTION_HANDLER': 'api.exceptions.custom_exception_handler',
    'AUTH_HEADER_TYPES': 'Token',
    'NON_FIELD_ERRORS_KEY': 'object_error',
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
}

CORS_ORIGIN_ALLOW_ALL = True
CORS_ALLOW_CREDENTIALS = True

GRAPH_MODELS = {
    'all_applications': True,
    'group_models': True,
}

AUTH_USER_MODEL = 'api.User'

# UPLOADS
FILE_UPLOAD_MAX_MEMORY_SIZE = 33554432  # 100mb
DATA_UPLOAD_MAX_MEMORY_SIZE = 524288000  # 500mb

# AWS
AWS_S3_ACCESS_KEY_ID = environ.get('S3_KEY')
AWS_S3_SECRET_ACCESS_KEY = environ.get('S3_SECRET')
AWS_STORAGE_BUCKET_NAME = environ.get('S3_BUCKET')
AWS_S3_REGION = environ.get('S3_REGION')
AWS_LOCATION = environ.get('AWS_LOCATION', 'static')
AWS_DEFAULT_ACL = environ.get('AWS_DEFAULT_ACL', 'public-read')
# Cause Python does not parse environment variables to Python objects, it just gets them as strings
_AWS_QUERYSTRING_AUTH = environ.get('AWS_QUERYSTRING_AUTH')
AWS_QUERYSTRING_AUTH = _AWS_QUERYSTRING_AUTH if _AWS_QUERYSTRING_AUTH else False
AWS_S3_CUSTOM_DOMAIN = '%s.s3.amazonaws.com' % AWS_STORAGE_BUCKET_NAME

# STATIC/MEDIA FILES MANAGMENT
STATICFILES_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
STATIC_URL = 'https://%s/%s/' % (AWS_S3_CUSTOM_DOMAIN, AWS_LOCATION)
MEDIAFILES_LOCATION = 'media'
DEFAULT_FILE_STORAGE = 'setinc.custom_storages.MediaStorage'

ADMIN_MEDIA_PREFIX = STATIC_URL + 'admin/'

STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
)

# Background tasks
REDIS_HOST = environ.get('REDIS_HOST', 'localhost')
REDIS_PORT = environ.get('REDIS_PORT', 6379)
REDIS_URL = environ.get("REDIS_URL", f'redis://{REDIS_HOST}:{REDIS_PORT}/0')

DRAMATIQ_BROKER = {
    "BROKER": "dramatiq.brokers.redis.RedisBroker",
    "OPTIONS": {
        "connection_pool": redis.ConnectionPool.from_url(REDIS_URL),
    },
    "MIDDLEWARE": [
        "dramatiq.middleware.AgeLimit",
        "dramatiq.middleware.TimeLimit",
        "dramatiq.middleware.Retries",
        "django_dramatiq.middleware.AdminMiddleware",
        "django_dramatiq.middleware.DbConnectionsMiddleware",
        "dramatiq.results.middleware.Results",
    ]
}
DRAMATIQ_TASKS_DATABASE = "default"
DRAMATIQ_DEFAULT_QUEUE = environ.get('DRAMATIQ_DEFAULT_QUEUE')
DRAMATIQ_RESULT_BACKEND = {
    "BACKEND": "dramatiq.results.backends.redis.RedisBackend",
    "BACKEND_OPTIONS": {
        "url": REDIS_URL,
    },
    "MIDDLEWARE_OPTIONS": {
        "result_ttl": 60000
    }
}

APSCHEDULER_DEFAULT_QUEUE = environ.get('DRAMATIQ_DEFAULT_QUEUE')

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=10),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,

    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': None,

    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',

    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',

    'JTI_CLAIM': 'jti',

    'SLIDING_TOKEN_REFRESH_EXP_CLAIM': 'refresh_exp',
    'SLIDING_TOKEN_LIFETIME': timedelta(minutes=60),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=1),
}

SWAGGER_SETTINGS = {
    'SECURITY_DEFINITIONS': {
        'Bearer': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header'
        }
    },
    "DEFAULT_AUTO_SCHEMA_CLASS": "setinc.custom_swagger.CustomAutoSchema"
}

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

EMAIL_CONFIRM_URL = environ.get('EMAIL_CONFIRM_URL')
EMAIL_USE_TLS = True
EMAIL_HOST = environ.get('EMAIL_HOST')
EMAIL_HOST_USER = environ.get('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = environ.get('EMAIL_HOST_PASSWORD')
EMAIL_PORT = environ.get('EMAIL_PORT', 587)

APPLE_SANDBOX = environ.get('APPLE_SANDBOX')
APPLE_BUNDLE_ID = environ.get('APPLE_BUNDLE_ID')
APPLE_SHARED_SECRET = environ.get('APPLE_SHARED_SECRET')

GOOGLE_BUNDLE_ID = environ.get('GOOGLE_BUNDLE_ID')
GOOGLE_API_FILE = environ.get('GOOGLE_API_FILE')

FCM_DJANGO_SETTINGS = {
    "FCM_SERVER_KEY": environ.get('FCM_SERVER_KEY')
}

FIREBASE_PATH = os.path.join(BASE_DIR, 'firebase.json') or None

TWILIO_ACCOUNT_SID = environ.get('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = environ.get('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = environ.get('TWILIO_PHONE_NUMBER')

try:
    from .local_settings import *
except ImportError:
    try:
        from local_settings import *
    except ImportError:
        print('Local settings couldn\'t be imported.')
