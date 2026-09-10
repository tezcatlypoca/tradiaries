from django.urls import path
from . import views

app_name = 'spot_trading'

urlpatterns = [
    path('', views.spot_trading, name='index'),
    path('create/', views.create_trade, name='create'),
    path('<int:pk>/edit/', views.update_trade, name='update'),
    path('<int:pk>/delete/', views.delete_trade, name='delete'),
]
