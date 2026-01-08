import os
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")
get_asgi_application()  # ensure Django initializes

from project.routing import application  # noqa: E402
