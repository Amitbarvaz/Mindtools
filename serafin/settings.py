'''
Django settings for the serafin project.

For more information on this file, see
https://docs.djangoproject.com/en/1.8/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.8/ref/settings/
'''

import os
import sentry_sdk
# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
from collections import OrderedDict
from pathlib import Path

from configurations import Configuration, values
from django.utils.translation import gettext_lazy as _
from sentry_sdk.integrations.django import DjangoIntegration


class Base(Configuration):
    BASE_DIR = Path(__file__).resolve().parent.parent

    # Quick-start development settings - unsuitable for production
    # See https://docs.djangoproject.com/en/1.8/howto/deployment/checklist/

    # SECURITY WARNING: keep the secret key used in production secret!
    SECRET_KEY = values.Value("django-insecure-o-rrch1c#^%2gw!&(acqgb6=(j$%n^6iip7_b7#q2vz^o(a3+u")

    # SECURITY WARNING: don't run with debug turned on in production!
    DEBUG = False
    TEMPLATE_DEBUG = DEBUG
    USERDATA_DEBUG = DEBUG
    RATELIMIT_ENABLE = True

    ALLOWED_HOSTS = values.ListValue([])
    CSRF_TRUSTED_ORIGINS = values.ListValue([])
    CORS_ALLOWED_ORIGINS = values.ListValue([])

    # Application definition

    # from multisite import SiteID
    # SITE_ID = SiteID(default=1)
    SITE_ID = 1

    INSTALLED_APPS = (
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.messages',
        'django.contrib.staticfiles',
        'django.contrib.sites',
        'django_user_agents',
        'django.db.models',
        'request',
        'adminsortable',

        'tokens',
        'users',
        'tasker',
        'events',
        'content',
        'plumbing',
        'system',

        'filer',
        'serafin.apps.SuitConfig',
        'django.contrib.admin',
        'sitetree',
        'django_extensions',
        'rules.apps.AutodiscoverRulesConfig',
        'rest_framework',
        'mptt',
        'easy_thumbnails',
        'huey.contrib.djhuey',
        'import_export',
        'compressor',
        'reversion',
        'constance',
        'raven.contrib.django.raven_compat',
        'serafin.apps.SerafinReConfig',
        'defender',
    )

    MIDDLEWARE = (
        'django.middleware.security.SecurityMiddleware',
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.middleware.locale.LocaleMiddleware',
        'django.middleware.common.CommonMiddleware',
        'django.middleware.csrf.CsrfViewMiddleware',
        'users.middleware.AuthenticationMiddleware',
        'users.middleware.IsAjaxRequestMiddleware',
        'users.middleware.RateLimitMiddleware',
        'django.contrib.messages.middleware.MessageMiddleware',
        'django.middleware.clickjacking.XFrameOptionsMiddleware',
        'django_user_agents.middleware.UserAgentMiddleware',
        'defender.middleware.FailedLoginMiddleware',
        'events.middleware.EventTrackingMiddleware',
        'request.middleware.RequestMiddleware',
        'users.middleware.ForceChangePasswordMiddleware',
        'serafin.middleware.AdminIPRestrictorMiddleware'
    )

    ROOT_URLCONF = 'serafin.urls'

    WSGI_APPLICATION = 'serafin.wsgi.application'

    TEMPLATES = [
        {
            'BACKEND': 'django.template.backends.django.DjangoTemplates',
            'DIRS': [
                os.path.join(BASE_DIR, 'templates')
            ],
            'APP_DIRS': True,
            'OPTIONS': {
                'context_processors': [
                    'django.contrib.messages.context_processors.messages',
                    'django.contrib.auth.context_processors.auth',
                    'django.template.context_processors.request',
                    'django_settings_export.settings_export',
                    'django.template.context_processors.static',
                    # Insert your TEMPLATE_CONTEXT_PROCESSORS here or use this
                    # list if you haven't customized them:
                    'users.context_processors.add_support_email',
                    'users.context_processors.add_basic_user_info'
                ],
            },
        },
    ]

    # Database
    # https://docs.djangoproject.com/en/1.8/ref/settings/#databases
    DATABASES = values.DatabaseURLValue("postgresql://postgres:postgres@db:5432/postgres")
    # Internationalization
    # https://docs.djangoproject.com/en/1.8/topics/i18n/

    LANGUAGE_CODE = 'en'

    LANGUAGES = (
        ('en', _('English')),
        ('he', _('Hebrew')),
    )

    LOCALE_PATHS = (
        os.path.join(BASE_DIR, 'conf/locale'),
    )

    TIME_ZONE = 'Asia/Jerusalem'
    USE_I18N = True
    USE_L10N = True
    USE_TZ = True
    USE_HTTPS = True
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

    # Static files (CSS, JavaScript, Images)
    # https://docs.djangoproject.com/en/1.8/howto/static-files/

    STATIC_URL = '/static/'
    STATIC_ROOT = values.Value(BASE_DIR / 'static')

    COMPRESS_ENABLED = False

    MEDIA_URL = '/media/'
    MEDIA_ROOT = values.Value(BASE_DIR / 'media')

    STATICFILES_DIRS = (
        os.path.join(BASE_DIR, 'staticfiles'),
    )

    STATICFILES_FINDERS = (
        'django.contrib.staticfiles.finders.FileSystemFinder',
        'django.contrib.staticfiles.finders.AppDirectoriesFinder',
        'compressor.finders.CompressorFinder',
        'npm.finders.NpmFinder',
    )

    NPM_FILE_PATTERNS = {
    }

    THUMBNAIL_ALIASES = {
        '': {
            'small': {
                'size': (150, 150),
            },
            'medium': {
                'size': (739, 739),
            },
        }
    }

    THUMBNAIL_QUALITY = 90
    THUMBNAIL_PRESERVE_EXTENSIONS = ('png',)
    THUMBNAIL_TRANSPARENCY_EXTENSION = 'png'

    FILER_DUMP_PAYLOAD = True

    # User model and authentication

    AUTH_USER_MODEL = 'users.User'

    AUTHENTICATION_BACKENDS = (
        'rules.permissions.ObjectPermissionBackend',
        'django.contrib.auth.backends.ModelBackend',
        'users.backends.TokenBackend',
    )

    LOGIN_URL = '/login'
    LOGIN_REDIRECT_URL = '/'

    HOME_URL = LOGIN_URL
    REGISTER_URL = '/register'

    TOKEN_TIMEOUT_DAYS = 1
    SESSION_COOKIE_NAME = 'serafin_session'
    SESSION_COOKIE_AGE = 24 * 60 * 60  # 24 hours

    AUTH_PASSWORD_VALIDATORS = [
        {
            'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
            'OPTIONS': {
                'min_length': 8,
            }
        },
        {
            'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
        },
        {
            'NAME': 'users.backends.DigitPasswordValidator',
        },
    ]

    # Events

    LOG_USER_DATA = True
    LOG_DEVICE_ON_LOGIN = True
    LOG_TIME_PER_PAGE = True
    LOG_MAX_MILLISECONDS = 5 * 60 * 1000  # 5 minutes

    # Email
    EMAIL_BACKEND = values.Value('django.core.mail.backends.smtp.EmailBackend')
    SERVER_EMAIL = values.Value('DigitalLab<no-reply.dplab@welfare.haifa.ac.il>')
    DEFAULT_FROM_EMAIL = values.Value('DigitalLab<no-reply.dplab@welfare.haifa.ac.il>')
    EMAIL_SUBJECT_PREFIX = values.Value('[Mindtools] ')

    EMAIL_TEST_ADDR = values.Value('weizenberg@gmail.com')
    EMAIL_HOST = values.Value('mr1res.haifa.ac.il')
    EMAIL_USE_SSL = values.BooleanValue(False)
    EMAIL_PORT = values.Value(25)
    SUPPORT_EMAIL = values.Value('dplab@welfare.haifa.ac.il')

    # SMS service

    SMS_SERVICE = values.Value('Console')
    TWILIO_ACCOUNT_SID = values.Value()
    TWILIO_AUTH_TOKEN = values.Value()
    TWILIO_FROM_NUMBER = values.Value('HeroOfMind')
    TWILIO_WHATSAPP_FROM_NUMBER = values.Value()
    TEST_TO_SMS = values.Value('+972506370323')

    # Google Analytics

    GOOGLE_ANALYTICS_ID = ''

    REDIS_PASSWORD = values.Value()

    # Huey
    @property
    def HUEY(self):
        return {
            'name': 'serafin',
            'store_none': True,
            'always_eager': False,
            'immediate': False,
            'consumer': {
                'quiet': True,
                'workers': 100,
                'worker_type': 'greenlet',
                'health_check_interval': 60,
            },
            'connection': {
                'host': 'redis',
                'password': self.REDIS_PASSWORD,
                'port': 6379
            }
        }

    # REST Framework

    REST_FRAMEWORK = {
        # Use hyperlinked styles by default.
        # Only used if the `serializer_class` attribute is not set on a view.
        'DEFAULT_MODEL_SERIALIZER_CLASS':
            'rest_framework.serializers.HyperlinkedModelSerializer',

        # Use Django's standard `django.contrib.auth` permissions,
        # or allow read-only access for unauthenticated users.
        'DEFAULT_PERMISSION_CLASSES': [
            'rest_framework.permissions.DjangoModelPermissionsOrAnonReadOnly',
            'rest_framework.permissions.AllowAny',
        ]
    }

    # Admin interface

    # Logging

    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
            },
            'verbose': {
                'format': '%(levelname)s %(asctime)s %(module)s '
                          '%(process)d %(thread)d %(message)s'
            }
        },
        'filters': {
            'require_debug': {
                '()': 'django.utils.log.RequireDebugTrue'
            }
        },
        'handlers': {
            'console': {
                'level': 'INFO',
                'filters': ['require_debug'],
                'class': 'logging.StreamHandler',
                'formatter': 'verbose'
            },
            'file': {
                'level': 'INFO',
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': 'serafin.log',
                'maxBytes': 1024 * 1024 * 5,  # 5 MB
                'backupCount': 3,
                'formatter': 'verbose'
            },
            'debug': {
                'level': 'DEBUG',
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': 'debug.log',
                'maxBytes': 1024 * 1024 * 5,  # 5 MB
                'backupCount': 0,
                'formatter': 'verbose',
                'encoding': 'utf-8'
            },
            'huey': {
                'level': 'INFO',
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': 'huey.log',
                'maxBytes': 1024 * 1024 * 5,  # 5 MB
                'backupCount': 0,
                'formatter': 'standard',
            },
        },
        'loggers': {
            'django': {
                'handlers': ['console'],
                'propagate': True
            },
            'django.db.backends': {
                'level': 'ERROR',
                'handlers': ['file', 'console'],
                'propagate': False
            },
            'django.request': {
                'level': 'ERROR',
                'handlers': ['file', 'console'],
                'propagate': False
            },
            'huey.consumer': {
                'handlers': ['huey'],
                'level': 'INFO',
                'propagate': True,
            },
            'debug': {
                'level': 'DEBUG',
                'handlers': ['debug'],
                'propagate': False
            },
            'users.models': {
                'level': 'INFO',
                'handlers': ['file', 'console'],
                'propagate': True
            }
        }
    }

    # Variables

    RESERVED_VARIABLES = [
        {
            'name': 'email',
            'admin_note': 'Do not use in conditions. Used in registration.',
            'domains': []
        },
        {
            'name': 'phone',
            'admin_note': 'Do not use in conditions. Used in registration.',
            'domains': []
        },
        {
            'name': 'secondary_phone',
            'admin_note': 'Do not use in conditions. Used in registration.',
            'domains': []
        },
        {
            'name': 'password',
            'admin_note': 'Do not use in conditions. Used in registration.',
            'domains': []
        },
        {
            'name': 'force_change_password',
            'admin_note': 'Force the user to change their password.',
            'domains': []
        },
        {
            'name': 'registered',
            'admin_note': 'Returns True if the user is registered',
            'domains': ['user']
        },
        {
            'name': 'enrolled',
            'admin_note': 'Returns True if the user is enrolled with the current Program',
            'domains': ['user']
        },
        {
            'name': 'group',
            'admin_note': 'Returns a list of the Groups the user is a member of',
            'domains': ['user']
        },
        {
            'name': 'current_day',
            'admin_note': 'Returns the current localized weekday as number, where Monday is 1 and Sunday is 7',
            'domains': ['user']
        },
        {
            'name': 'current_time',
            'admin_note': 'Returns the current localized time in iso format, i.e. 12:00:00',
            'domains': ['user']
        },
        {
            'name': 'current_date',
            'admin_note': 'Returns the current localized date in iso format, i.e. 2015-05-01',
            'domains': ['user']
        },
        {
            'name': 'session',
            'admin_note': 'For system use. Returns the id of the current Session.',
            'domains': []
        },
        {
            'name': 'node',
            'admin_note': 'For system use. Returns the current node id (relative to Session).',
            'domains': []
        },
        {
            'name': 'stack',
            'admin_note': 'For system use. Returns a list of stacked (session, node) id pairs.',
            'domains': []
        },
        {
            'name': 'login_link',
            'admin_note': 'For system use. Used in processing login e-mails.',
            'domains': []
        },
        {
            'name': 'reply_session',
            'admin_note': 'For system use. Returns the session to transition from when receiving an SMS reply.',
            'domains': []
        },
        {
            'name': 'reply_node',
            'admin_note': 'For system use. Returns the node to transition from when receiving an SMS reply.',
            'domains': []
        },
        {
            'name': 'reply_variable',
            'admin_note': 'For system use. Returns the name of the last SMS reply variable.',
            'domains': []
        },
        {
            'name': 'timer',
            'admin_note': 'For system use, never accessible. Used for timing page visits.',
            'domains': []
        },
        {
            'name': 'tools',
            'admin_note': 'For the available tools of the user',
            'domains': []
        }
    ]

    # Available stylesheets for the dynamic switcher

    STYLESHEETS = [
        {"name": _("Default stylesheet"), "path": "css/style.css"},
        {"name": _("New-Nalokson"), "path": "css/style-nalokson-ltr.css"},
        {"name": _("RTL-Nalokson"), "path": "css/style-nalokson-rtl.css"},
        {"name": _("Nalokson"), "path": "css/style-nalokson.css"},
        {"name": _("Miksmaster"), "path": "css/style-miksmaster.css"},
        {"name": _("Miksmaster alternate"), "path": "css/style-miksmaster-alt.css"},
    ]

    STYLESHEET_CHOICES = [(ss['path'], ss['name']) for ss in STYLESHEETS]

    # Constance
    CONSTANCE_CONFIG = OrderedDict([
        ('USER_VARIABLE_PROFILE_ORDER', (
            u'session, node, stack, reply_session, reply_node, reply_variable',
            'What user variables to list first on a user\'s object page (comma separated)',
            str
        )),
        ('USER_VARIABLE_EXPORT', (
            u'',
            'What user variables to export from user listing (comma separated, leave blank for all)',
            str
        )),
    ])

    @property
    def CONSTANCE_REDIS_CONNECTION(self):
        return {
            'host': 'redis',
            'password': self.REDIS_PASSWORD,
            'port': 6379
        }

    # Request

    REQUEST_IGNORE_PATHS = (
        r'^admin',
        r'^static',
        r'^api.*(?<!users_stats)$',
    )

    REQUEST_IGNORE_USER_AGENTS = (
        r'^$',  # ignore blank user agent
        r'Googlebot',
        r'bingbot',
        r'YandexBot',
        r'MJ12Bot',
        r'Slurp',
        r'Baiduspider',
    )

    REQUEST_TRAFFIC_MODULES = (
        'request.traffic.UniqueVisitor',
        'request.traffic.UniqueUser',
        'request.traffic.Error',
        'request.traffic.Error404',
    )

    REQUEST_PLUGINS = (
        'request.plugins.TrafficInformation',
        'request.plugins.TopReferrers',
        'request.plugins.TopSearchPhrases',
        'request.plugins.TopBrowsers',
    )

    SETTINGS_EXPORT = [
        'FRONTEND_SENTRY_DSN',
        'SITE_ENVIRONMENT',
        'DEBUG',
        'GOOGLE_ANALYTICS_ID',
        'SUPPORT_EMAIL'
    ]

    @property
    def DEFENDER_REDIS_URL(self):
        return 'redis://:' + self.CONSTANCE_REDIS_CONNECTION['password'] + '@' + self.CONSTANCE_REDIS_CONNECTION[
            'host'] + ':' + str(self.CONSTANCE_REDIS_CONNECTION['port']) \
            + '/0'

    DEFENDER_LOGIN_FAILURE_LIMIT = 5
    DEFENDER_COOLOFF_TIME = 0
    DEFENDER_LOCKOUT_TEMPLATE = 'login_lock.html'
    DEFENDER_LOGIN_FAILURE_LIMIT_IP = 100
    DEFENDER_BEHIND_REVERSE_PROXY = True

    RESTRICT_ADMIN = True
    ALLOWED_ADMIN_IPS = values.ListValue(['127.0.0.1', '::1'])
    ALLOWED_ADMIN_IP_RANGES = values.ListValue(['127.0.0.0/24', '::/1'])
    RESTRICTED_APP_NAMES = values.ListValue(['admin'])
    TRUST_PRIVATE_IP = False

    DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

    AWS_ACCESS_KEY_ID = values.Value('')
    AWS_SECRET_ACCESS_KEY = values.Value('')
    AWS_STORAGE_BUCKET_NAME = values.Value('')
    AWS_S3_CUSTOM_DOMAIN = values.Value('')
    PUBLIC_MEDIA_LOCATION = values.Value('media')

    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    FILE_UPLOAD_PERMISSIONS = 0o644
    FILE_UPLOAD_MAX_MEMORY_SIZE = 104857600
    DATA_UPLOAD_MAX_NUMBER_FIELDS = 5000

    SENTRY_DSN = values.Value('')
    FRONTEND_SENTRY_DSN = values.Value('')
    SITE_ENVIRONMENT = "Development"


class Development(Base):
    DEBUG = True
    TEMPLATE_DEBUG = DEBUG
    USERDATA_DEBUG = DEBUG
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    DATABASES = values.DatabaseURLValue("postgresql://serafin_user:serafin_pass@localhost:5433/serafin_db")
    HUEY = {
        'name': 'serafin',
        'store_none': True,
        'always_eager': False,
        'immediate': True,
        'consumer': {
            'quiet': True,
            'workers': 100,
            'worker_type': 'greenlet',
            'health_check_interval': 60,
        },
        'connection': {
            'host': 'redis',
            'port': 6379
        }
    }
    CONSTANCE_REDIS_CONNECTION = {
        'host': 'redis',
        'port': 6379
    }
    DEFENDER_REDIS_URL = 'redis://' + CONSTANCE_REDIS_CONNECTION['host'] + ':' + str(CONSTANCE_REDIS_CONNECTION['port']) \
                         + '/0'

    TRUST_PRIVATE_IP = True
    USE_HTTPS = False
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False


class Testing(Base):
    BASE_DIR = Path(__file__).resolve().parent.parent
    TEST_RUNNER = 'django.test.runner.DiscoverRunner'
    TEST_DISCOVER_TOP_LEVEL = BASE_DIR
    TEST_DISCOVER_ROOT = BASE_DIR
    TEST_DISCOVER_PATTERN = 'test_*'
    DATABASES = values.DatabaseURLValue("postgresql://serafin_user:serafin_pass@localhost:5433/serafin_db")
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    HUEY = {
        'name': 'serafin',
        'store_none': True,
        'always_eager': True,
        'immediate': True,
        'consumer': {
            'quiet': True,
            'workers': 100,
            'worker_type': 'greenlet',
            'health_check_interval': 60,
        },
        'connection': {
            'host': 'localhost',
            'port': 6379
        }
    }

    CONSTANCE_REDIS_CONNECTION = {
        'host': 'localhost',
        'port': 6379
    }
    DEFENDER_REDIS_URL = 'redis://' + CONSTANCE_REDIS_CONNECTION['host'] + ':' + str(CONSTANCE_REDIS_CONNECTION['port']) \
                         + '/0'

    TRUST_PRIVATE_IP = True
    USE_HTTPS = False
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False


class Staging(Base):
    SITE_ENVIRONMENT = "Staging"

    @classmethod
    def post_setup(cls):
        """Sentry initialization"""
        super(Staging, cls).post_setup()
        sentry_sdk.init(
            dsn=cls.SENTRY_DSN,
            integrations=[DjangoIntegration()],
            traces_sample_rate=0.25,
            environment="staging",
            send_default_pii=True
        )


class Production(Base):
    SITE_ENVIRONMENT = "Production"
    COMPRESS_ENABLED = True

    STATICFILES_FINDERS = (
        'django.contrib.staticfiles.finders.FileSystemFinder',
        'django.contrib.staticfiles.finders.AppDirectoriesFinder',
        'compressor.finders.CompressorFinder'
    )

    FILER_STORAGES = {
        'public': {
            'main': {
                'ENGINE': 'storages.backends.s3boto3.S3Boto3Storage',
                'OPTIONS': {
                    'location': 'media',
                    'default_acl': 'public-read',
                    'file_overwrite': False
                },
                'UPLOAD_TO': 'filer.utils.generate_filename.randomized',
                'UPLOAD_TO_PREFIX': 'public',
            },
            'thumbnails': {
                'ENGINE': 'storages.backends.s3boto3.S3Boto3Storage',
                'OPTIONS': {
                    'location': 'media',
                    'default_acl': 'public-read',
                    'file_overwrite': False
                }
            }
        }
    }

    @classmethod
    def post_setup(cls):
        """Sentry initialization"""
        super(Production, cls).post_setup()
        sentry_sdk.init(
            dsn=cls.SENTRY_DSN,
            integrations=[DjangoIntegration()],
            traces_sample_rate=0.01,
            environment="production",
            send_default_pii=False
        )
