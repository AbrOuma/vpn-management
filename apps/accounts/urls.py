from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/',                              views.login_view,          name='login'),
    path('logout/',                             views.logout_view,         name='logout'),
    path('settings/',                           views.settings_view,       name='settings'),
    path('settings/token/generate/',            views.token_generate,      name='token_generate'),
    path('settings/token/revoke/',              views.token_revoke,        name='token_revoke'),
    path('settings/token/revoke/<int:user_id>/', views.admin_token_revoke, name='admin_token_revoke'),
]