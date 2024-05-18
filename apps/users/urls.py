from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('',                    views.user_list,     name='list'),
    path('add/',                views.user_add,      name='add'),
    path('<uuid:pk>/',          views.user_detail,   name='detail'),
    path('<uuid:pk>/suspend/',  views.user_suspend,  name='suspend'),
    path('<uuid:pk>/activate/', views.user_activate, name='activate'),
    path('<uuid:pk>/delete/', views.user_delete, name='delete'),
    path('departments/',              views.department_list,   name='departments'),
    path('departments/add/',          views.department_add,    name='department_add'),
    path('departments/<int:pk>/delete/', views.department_delete, name='department_delete'),
]