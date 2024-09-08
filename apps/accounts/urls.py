from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('dashboard/', views.dashboard_home, name='dashboard'),
    path('login/',                               views.login_view,          name='login'),
    path('logout/',                              views.logout_view,         name='logout'),
    path('settings/',                            views.settings_view,       name='settings'),
    path('settings/token/generate/',             views.token_generate,      name='token_generate'),
    path('settings/token/revoke/',               views.token_revoke,        name='token_revoke'),
    path('settings/token/revoke/<int:user_id>/', views.admin_token_revoke,  name='admin_token_revoke'),
    path('admins/',                              views.admin_list,          name='admin_list'),
    path('admins/add/',                          views.admin_add,           name='admin_add'),
    path('admins/<int:pk>/edit/',                views.admin_edit,          name='admin_edit'),
    path('admins/<int:pk>/deactivate/',          views.admin_deactivate,    name='admin_deactivate'),
    path('admins/<int:pk>/activate/',            views.admin_activate,      name='admin_activate'),
    path('admins/<int:pk>/delete/',              views.admin_delete,        name='admin_delete'),
]