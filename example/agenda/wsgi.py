import os
import sys
from django.core.wsgi import get_wsgi_application

path = os.path.split(os.path.abspath(os.path.dirname(__file__)))[0]
if path not in sys.path:
    sys.path.append(path)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "agenda.settings")

application = get_wsgi_application()
