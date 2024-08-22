from django.urls import path
from . import views

app_name = 'server'

urlpatterns = [
    path('',                                  views.server_list,              name='list'),
    path('add/',                              views.server_add,               name='add'),
    path('create/',                           views.create_choice,            name='create_choice'),
    path('create/existing-vm/',               views.provision_existing,       name='provision_existing'),
    path('create/gcp-vm/',                    views.provision_gcp,            name='provision_gcp'),
    path('create/aws-vm/',                    views.provision_aws,            name='provision_aws'),
    path('<int:pk>/',                         views.server_overview,          name='overview'),
    path('<int:pk>/setup/',                   views.server_setup,             name='setup'),
    path('<int:pk>/repopulate/',              views.repopulate_ip_pool,       name='repopulate_pool'),
    path('<int:pk>/import/',                  views.import_preview,           name='import'),
    path('<int:pk>/import/commit/',           views.import_commit,            name='import_commit'),
    path('<int:pk>/sync/',                    views.sync_server,              name='sync'),
    path('<int:pk>/health/',                  views.server_health,            name='health'),
    path('<int:pk>/delete/',                  views.server_delete,            name='delete'),
    path('<int:pk>/delete/wipe-peers/',       views.server_wipe_peers,        name='wipe_peers'),
    path('<int:pk>/delete/destroy-vm/',       views.server_destroy_vm,        name='destroy_vm'),
    path('<int:pk>/provisioning/',            views.provisioning_progress,    name='provisioning_progress'),
    path('<int:pk>/provisioning/status/',     views.ajax_provisioning_status, name='provisioning_status'),
    path('<int:pk>/ssh-key/download/',        views.download_ssh_key,         name='download_ssh_key'),
    path('<int:pk>/ajax/sync/',               views.ajax_sync,                name='ajax_sync'),
    path('<int:pk>/ajax/health/',             views.ajax_health,              name='ajax_health'),
    path('<int:pk>/ajax/repopulate/',         views.ajax_repopulate,          name='ajax_repopulate'),
]