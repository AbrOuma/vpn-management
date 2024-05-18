from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView


urlpatterns = [
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