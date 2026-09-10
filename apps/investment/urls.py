from django.urls import path
from . import views

app_name = 'investment'

urlpatterns = [
    path('healthz/', views.healthz, name='healthz'),
    path('', views.investment, name='index'),
    path('create/', views.create_investment, name='create'),
    path('<int:pk>/edit/', views.update_investment, name='update'),
    path('<int:pk>/delete/', views.delete_investment, name='delete'),
]
