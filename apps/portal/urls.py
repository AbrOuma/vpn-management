from django.urls import path
from . import views

app_name = 'portal'

urlpatterns = [
    path('',                  views.portal_login_view,     name='login'),
    path('verify/<str:token>/', views.portal_verify,       name='verify'),
    path('dashboard/',        views.portal_dashboard_view, name='dashboard'),
    path('logout/',           views.portal_logout_view,    name='logout'),
]