from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.http import HttpResponse
from django.conf import settings

def debug_settings(request):
    return HttpResponse(f"""
        SETTINGS MODULE: {settings.SETTINGS_MODULE}<br>
        DEBUG: {settings.DEBUG}<br>
        CSRF_TRUSTED_ORIGINS: {getattr(settings, 'CSRF_TRUSTED_ORIGINS', 'NOT SET')}<br>
    """)


urlpatterns = [
    path('debug-settings/', debug_settings),
    path('', RedirectView.as_view(url='/dashboard/', permanent=False), name='home'),
    path('admin/', admin.site.urls),
    path('accounts/', include('apps.accounts.urls')),
    path('dashboard/', include('apps.devices.urls')),
    path('users/', include('apps.users.urls')),
    path('server/', include('apps.server.urls')),
    path('connect/', include('apps.invites.urls')),
    path('portal/', include('apps.portal.urls')),
    path('api/v1/', include('apps.api.urls')),
]