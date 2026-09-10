from django.urls import path

from . import views


app_name = 'settings'

urlpatterns = [
    path('', views.settings_view, name='index'),
    path('api-credentials/create/', views.create_api_credential, name='api_credential_create'),
    path('api-credentials/<int:pk>/delete/', views.delete_api_credential, name='api_credential_delete'),
]