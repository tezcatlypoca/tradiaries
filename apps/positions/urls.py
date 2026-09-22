from django.urls import path
from . import views

app_name = 'positions'

urlpatterns = [
    path('', views.positions, name='index'),
]
