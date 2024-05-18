from django.urls import path
from . import views

app_name = 'invites'

urlpatterns = [
    path('<str:token>/',          views.redeem_invite,   name='redeem'),
    path('<str:token>/download/', views.download_config, name='download'),
]