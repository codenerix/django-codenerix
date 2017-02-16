DEBUG=True
ROSETTA = False
ADMINSITE = True
DEBUG_TOOLBAR = False
DEBUG_PANEL = False
SPAGHETTI = False
CODENERIXSOURCE=True
MEMCACHE=False
SNIPPET_SCREAM = False
GRAPH_MODELS = False
#APPEND_SLASH = True

ADMINS = (
    ('Juan Miguel Taboada', 'juanmi@centrologic.com'),
)

USER_DEFAULT = 'demoRt3CJLNcIi'
PASSWORD_DEFAULT = 'demou3MmPohoS'

CLIENTS = ADMINS

# Email server
EMAIL_HOST='192.168.252.1'
EMAIL_HOST_USER='test@centrologic.net'
EMAIL_HOST_PASSWORD='eqGaA8sUV'
DEFAULT_FROM_EMAIL='tcpugest@centrologic.net'

# SECRET KEY
SECRET_KEY = 'xxf%sdfol8$(3w-sa6LVwY7Hdf999f78f1#y6iwMVDBDaYL%_i'
PUBLIC_KEY = {
    'KERNEL': ('fd420b6b39aa4c4cc9418eae4c4577df7eba2047','YNSdv2mAOvnUFJ3cIm07qSpNt8MIMN3V'),
}

# DATABASES
DATABASES = {
    'default':{
        'ENGINE': 'django.db.backends.mysql',   # Engine (Supported: 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle')
        'NAME': 'phonebook',                # Database name
        'USER': 'phonebook',              # Username
        'PASSWORD': 'TkV4mKC2emo1hygA',         # Password
        'HOST': '',                             # Host (empty=localhost)
        'PORT': '',                             # Port (empty=3306)
        'OPTIONS': {
            'init_command': "SET storage_engine=INNODB;"
        }
    },
}

# MEMCACHE
if MEMCACHE:
    CACHE_BACKEND = 'memcached://127.0.0.1:11211/';
    CACHES = {
            'default': {
                'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
                'LOCATION': '127.0.0.1:11211',
                'KEY_PREFIX': 'I',
                'TIMEOUT': 1800,
                },
            'debug-panel': {
                'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
                'LOCATION': '/tmp/debug-panel-cache',
                'TIMEOUT': 300,
                'OPTIONS': {
                    'MAX_ENTRIES': 500
                    }
                }
            }
    
    #SESSION_ENGINE = 'django.contrib.sessions.backends.cache'


# autoload = lambda a,b: return (a,b)
# autourl = lambda a: return a


# Configuration for DEBUGGERS
from agenda.debug import codenerix_statics, DEBUG_TOOLBAR_DEFAULT_PANELS, DEBUG_TOOLBAR_DEFAULT_CONFIG, autoload as autoload_debug, autourl as autourl_debug
(CODENERIX_CSS, CODENERIX_JS) = codenerix_statics(CODENERIXSOURCE, DEBUG)

if DEBUG and DEBUG_TOOLBAR:
    INTERNAL_IPS = ('127.0.0.1', ) # Use: ('',) for everybody
    DEBUG_TOOLBAR_PANELS = DEBUG_TOOLBAR_DEFAULT_PANELS
    DEBUG_TOOLBAR_CONFIG = DEBUG_TOOLBAR_DEFAULT_CONFIG

if DEBUG and ROSETTA:
    ADMIN_MEDIA_PREFIX = '/static/admin/'
    #ROSETTA_ENABLE_TRANSLATION_SUGGESTIONS=True
    #ROSETTA_GOOGLE_TRANSLATE=True

AUTHENTICATION_TOKEN = {
#              'key': 'hola',
#  'master_unsigned': True,
#    'master_signed': True,
#    'user_unsigned': True,
#      'user_signed': True,
#     'otp_unsigned': True,
#       'otp_signed': True,
        }

if DEBUG and SPAGHETTI:
    SPAGHETTI_APPS = []
    SPAGHETTI_APPS.append('base')
    SPAGHETTI_APPS.append('people')
    SPAGHETTI_APPS.append('documentation')
    SPAGHETTI_SAUCE = {
        'apps': SPAGHETTI_APPS,
        'show_fields':False,
        'exclude':{'auth':['user']}
    }

# Graph modellers$
if DEBUG and GRAPH_MODELS:
    GRAPH_MODELS = {
        'all_applications': True,
        'group_models': True,
    }

# Autoload for DEBUG system
autoload = lambda INSTALLED_APPS, MIDDLEWARE_CLASSES: autoload_debug(INSTALLED_APPS, MIDDLEWARE_CLASSES, DEBUG, SPAGHETTI, ROSETTA, ADMINSITE, DEBUG_TOOLBAR, DEBUG_PANEL, SNIPPET_SCREAM, GRAPH_MODELS)
autourl = lambda URLPATTERNS: autourl_debug(URLPATTERNS, DEBUG, ROSETTA, ADMINSITE, SPAGHETTI)


