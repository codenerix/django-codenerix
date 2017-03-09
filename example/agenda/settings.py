# Django settings for agenda project.
import os
from agenda.debug import codenerix_statics, autoload as autoload_debug, autourl as autourl_debug

VERSION = "0.1"


DEBUG = True
CODENERIXSOURCE = True
SPAGHETTI = False
ROSETTA = False
ADMINSITE = True
DEBUG_TOOLBAR = False
DEBUG_PANEL = False
SNIPPET_SCREAM = False
GRAPH_MODELS = False

# Behaviour
# Behavior configuration
USERNAME_MIN_SIZE = 6
PASSWORD_MIN_SIZE = 8
ALARMS_LOOPTIME = 15000     # Refresh alarms every 15 seconds (15.000 miliseconds)
ALARMS_QUICKLOOP = 1000     # Refresh alarms every 1 seconds (1.000 miliseconds) when the system is on quick loop processing (without focus)
ALARMS_ERRORLOOP = 5000     # Refresh alarms every 5 seconds (5.000 miliseconds) when the http request fails
CONNECTION_ERROR = 60000    # Connection error after 60 seconds (60.000 miliseconds)
ALL_PAGESALLOWED = True

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.4/ref/settings/#allowed-hosts
ALLOWED_HOSTS = [
    'demotest.codenerix.com',
    'www.demotest.codenerix.com',
    'demo.codenerix.com',
    'www.demo.codenerix.com',
    'rbecerra.centrologic.net',
    'www.rbecerra.centrologic.net',
    '127.0.0.1',
    'localhost',
]

RECAPTCHA_PUBLIC_KEY = '6Ld-qxUUAAAAAN26LtGvceifXdltI985Y_AXlKXZ'
RECAPTCHA_PRIVATE_KEY = '6Ld-qxUUAAAAAI4qGY4wDlYGEJkIC-mCNUzw4mdv'
NOCAPTCHA = True
RECAPTCHA_USE_SSL = True

CODENERIX_CSS = '<link href="/static/codenerix/codenerix.css" rel="stylesheet">'
CODENERIX_JS = '<script type="text/javascript" src="/static/codenerix/codenerix.js"></script>'
CODENERIX_JS += '<script type="text/javascript" src="/static/codenerix/codenerix.extra.js"></script>'

# Define base dir
BASE_DIR = os.path.split(os.path.abspath(os.path.dirname(__file__)))[0]


ADMINS = (
    ('Nobody', 'nobody@domain.dom'),
)

# SECRET KEY
SECRET_KEY = '&^+@ldfCODENERIX-CODENERIX-CODENERIX-hfvb5bgx2'
HTTPS_SUPPORT = False

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'democodenerix.db'),
    }
}

MANAGERS = ADMINS

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
# TIME_ZONE = 'Europe/Madrid'
TIME_ZONE = 'UTC'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
# LANGUAGE_CODE = 'es-es'
LANGUAGE_CODE = 'en-us'

ugettext = lambda s: s
LANGUAGES = (
    ('es', ugettext('Spanish')),
    ('en', ugettext('English')),
)

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = False

# Use this serializer to be able to serialize timezone dates
SESSION_SERIALIZER = 'django.contrib.sessions.serializers.PickleSerializer'

# Other definitions about dates, hours
DATETIME_FORMAT = "Y-m-d H:i"
DATETIME_INPUT_FORMATS = ("%Y-%m-%d %H:%M",)
TIME_FORMAT = "H:i"
TIME_INPUT_FORMATS = ("%H:%M","%H%M")
DATETIME_RANGE_FORMAT = ("%Y-%m-%d","YYYY-MM-DD") # ATENCION: el formato que llega a la funcion es mayor
DATERANGEPICKER_OPTIONS = "{{"
DATERANGEPICKER_OPTIONS += "    format: '{Format}',"
DATERANGEPICKER_OPTIONS += "    timePicker:true,"
DATERANGEPICKER_OPTIONS += "    timePicker12Hour:false,"
DATERANGEPICKER_OPTIONS += "    showDropdowns: true,"
DATERANGEPICKER_OPTIONS += "    locale: {{"
DATERANGEPICKER_OPTIONS += "        firstDay:1,"
DATERANGEPICKER_OPTIONS += "        fromLabel:'{From}',"
DATERANGEPICKER_OPTIONS += "        toLabel:'{To}',"
DATERANGEPICKER_OPTIONS += "        applyLabel:'{Apply}',"
DATERANGEPICKER_OPTIONS += "        cancelLabel:'{Cancel}',"
DATERANGEPICKER_OPTIONS += "        daysOfWeek: ['{Su}', '{Mo}', '{Tu}', '{We}', '{Th}', '{Fr}','{Sa}'],"
DATERANGEPICKER_OPTIONS += "        monthNames: ['{January}', '{February}', '{March}', '{April}', '{May}', '{June}', '{July}', '{August}', '{September}', '{October}', '{November}', '{December}'],"
DATERANGEPICKER_OPTIONS += "    }},"
DATERANGEPICKER_OPTIONS += "}}"

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

# LOCALE_PATHS
LOCALE_PATHS = (
    os.path.join(BASE_DIR, 'conf/locale'),
)

# URL for login
LOGIN_URL = '/login/'
# After doing login, where to go
LOGIN_REDIRECT_URL = '/'

# SSL Support forced
# SECURE_REQUIRED_PATHS = ('/',)
SECURE_REQUIRED_PATHS = ()
HTTPS_SUPPORT = False

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = '/media/'

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = os.path.join(BASE_DIR, 'static/')

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

MIDDLEWARE = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'codenerix.authbackend.TokenAuthMiddleware',
    'codenerix.authbackend.LimitedAuthMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'codenerix.middleware.SecureRequiredMiddleware',
    'codenerix.middleware.CurrentUserMiddleware',
)

ROOT_URLCONF = 'agenda.urls'
WSGI_APPLICATION = 'agenda.wsgi.application'

# Python dotted path to the WSGI application used by Django's runserver.

AUTHENTICATION_BACKENDS=(
#    "django.contrib.auth.backends.ModelBackend",   # Django's default
    "codenerix.authbackend.TokenAuth",                # TokenAuth
    "codenerix.authbackend.LimitedAuth",            # LimitedAuth
)
AUTHENTICATION_TOKEN = {
#              'key': 'hola',
#  'master_unsigned': True,
#    'master_signed': True,
#    'user_unsigned': True,
#      'user_signed': True,
#     'otp_unsigned': True,
#       'otp_signed': True,
}

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'multi_email_field',
    # Internal
    'djng',
    'codenerix',
    # Project
    'agenda.base',
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

# EMAILS GENERAL CONFIGURATION
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'


LIMIT_FOREIGNKEY = 25
MAX_REGISTERS = 100
USER_DEFAULT = 'demo'
PASSWORD_DEFAULT = 'demo'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'agenda/templates'),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                # Insert your TEMPLATE_CONTEXT_PROCESSORS here or use this
                # list if you haven't customized them:
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages',
                'codenerix.context.codenerix',
                'codenerix.context.codenerix_js',
            ],
        },
    },
]


(CODENERIX_CSS, CODENERIX_JS) = codenerix_statics(CODENERIXSOURCE, DEBUG)

# Autoload for DEBUG system
autourl = lambda URLPATTERNS: autourl_debug(URLPATTERNS, DEBUG, ROSETTA, ADMINSITE, SPAGHETTI)

(INSTALLED_APPS, MIDDLEWARE) = autoload_debug(INSTALLED_APPS, MIDDLEWARE, DEBUG, SPAGHETTI, ROSETTA, ADMINSITE, DEBUG_TOOLBAR, DEBUG_PANEL, SNIPPET_SCREAM, GRAPH_MODELS)
