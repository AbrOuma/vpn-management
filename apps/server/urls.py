from django.urls import path
from . import views

app_name = 'server'

urlpatterns = [
    path('',                        views.server_list,        name='list'),
    path('add/',                    views.server_add,         name='add'),
    path('<int:pk>/',               views.server_overview,    name='overview'),
    path('<int:pk>/setup/',         views.server_setup,       name='setup'),
    path('<int:pk>/repopulate/',    views.repopulate_ip_pool, name='repopulate_pool'),
    path('<int:pk>/import/',        views.import_preview,     name='import'),
    path('<int:pk>/import/commit/', views.import_commit,      name='import_commit'),
    path('<int:pk>/sync/',          views.sync_server,        name='sync'),
    path('<int:pk>/health/',        views.server_health,      name='health'),
    path('<int:pk>/delete/',        views.server_delete,      name='delete'),
    path('<int:pk>/ssh-key/download/', views.download_ssh_key, name='download_ssh_key'),
]