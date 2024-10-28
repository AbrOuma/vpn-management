from django.urls import path
from . import views

app_name = 'devices'

urlpatterns = [
    path('',                       views.device_list,    name='list'),
    path('add/',                   views.device_add,     name='add'),
    path('<uuid:pk>/',             views.device_detail,  name='detail'),
    path('<uuid:pk>/edit/',        views.device_edit,    name='edit'),
    path('<uuid:pk>/delete/',      views.device_delete,  name='delete'),
    path('<uuid:pk>/enable/',      views.device_enable,  name='enable'),
    path('<uuid:pk>/disable/',     views.device_disable, name='disable'),
    path('<uuid:pk>/revoke/',      views.device_revoke,  name='revoke'),
    path('<uuid:pk>/traffic/',     views.device_traffic, name='traffic'),
    path('bulk-action/',           views.device_bulk_action, name='bulk_action'),
    path('status-poll/', views.device_status_poll, name='status_poll'),
]