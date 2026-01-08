from django.contrib import admin
from django.urls import path, re_path
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from bokeh_django import autoload, static_extensions

from lc_viz import views

bokeh_apps = [
    autoload("lc", views.lc_panel_app),
]

urlpatterns = [
    path("lc/", views.lc_page, name="lc_page"),
    path("admin/", admin.site.urls),
]

urlpatterns += static_extensions()
urlpatterns += staticfiles_urlpatterns()

ext_patterns = static_extensions()

# Add normal extension routes
_ext = static_extensions()
urlpatterns += _ext
urlpatterns += staticfiles_urlpatterns()

# Duplicate extension route under /lc/
# static_extensions defines a single regex route: r"^static/extensions/(?P<path>.*)$"
# We reuse the same view callable.
ext_view = _ext[0].callback
urlpatterns += [
    re_path(r"^lc/static/extensions/(?P<path>.*)$", ext_view),
]