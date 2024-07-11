from django.urls import path
from rest_framework.authtoken.views import obtain_auth_token
from . import views
from .views import EmailTokenView 

app_name = 'api'

urlpatterns = [
    # Auth
    path('auth/token/', EmailTokenView.as_view(), name='token'),

    # Servers (servers use int pk, leave as is)
    path('servers/', views.ServerListView.as_view(), name='server-list'),
    path('servers/<int:pk>/', views.ServerDetailView.as_view(), name='server-detail'),
    path('servers/<int:pk>/sync/', views.ServerSyncView.as_view(), name='server-sync'),
    path('servers/<int:pk>/health/', views.ServerHealthView.as_view(), name='server-health'),

    # Devices
    path('devices/', views.DeviceListView.as_view(), name='device-list'),
    path('devices/<uuid:pk>/', views.DeviceDetailView.as_view(), name='device-detail'),
    path('devices/<uuid:pk>/config/', views.DeviceConfigView.as_view(), name='device-config'),
    path('devices/<uuid:pk>/enable/', views.DeviceActionView.as_view(), {'action': 'enable'}, name='device-enable'),
    path('devices/<uuid:pk>/disable/', views.DeviceActionView.as_view(), {'action': 'disable'}, name='device-disable'),
    path('devices/<uuid:pk>/revoke/', views.DeviceActionView.as_view(), {'action': 'revoke'}, name='device-revoke'),

    # Users
    path('users/', views.UserListView.as_view(), name='user-list'),
    path('users/<int:pk>/', views.UserDetailView.as_view(), name='user-detail'),
    path('users/<int:pk>/suspend/', views.UserActionView.as_view(), {'action': 'suspend'}, name='user-suspend'),
    path('users/<int:pk>/activate/', views.UserActionView.as_view(), {'action': 'activate'}, name='user-activate'),
]