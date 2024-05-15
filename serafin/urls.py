import re

from django.urls import re_path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http.response import HttpResponse
from django.shortcuts import render
from django.views.generic.base import RedirectView

from system.views import export_text, import_text, set_program, set_stylesheet, redirect_media

admin.autodiscover()

favicon_view = RedirectView.as_view(url=settings.STATIC_URL + 'img/favicon.ico', permanent=True)


def not_found_error(request, exception=None):
    return render(request, 'page_not_found_error.html', status=404)


handler404 = not_found_error

urlpatterns = [
    re_path(r'^api/plumbing/', include('plumbing.urls')),
    re_path(r'^api/system/', include('system.urls')),

    re_path(r'^admin/', admin.site.urls),
    re_path(r'^admin/defender/', include('defender.urls')),
    re_path(r'^admin/export_text/', export_text),
    re_path(r'^admin/import_text/', import_text),
    re_path(r'^admin/set_program/$', set_program, name="set_program"),
    re_path(r'^admin/set_stylesheet/$', set_stylesheet, name="set_stylesheet"),
    re_path('i18n/', include('django.conf.urls.i18n')),

    re_path(r'^healthz$', lambda r: HttpResponse()),

    re_path(r'^', include('users.urls')),
    re_path(r'^', include('content.urls')),
    re_path(r'^favicon\.ico$', favicon_view),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += [re_path(r'^%s(?P<path>.*)$' % re.escape(settings.MEDIA_URL.lstrip('/')), redirect_media)]
