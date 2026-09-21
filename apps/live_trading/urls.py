from django.urls import path
from . import views

app_name = 'live_trading'

urlpatterns = [
    path('', views.live_trading, name='index'),
    path('open/', views.open_position, name='open'),
    path('ohlc.json', views.ohlc_json, name='ohlc_json'),
    path('<str:kind>/<int:pk>/close/', views.close_position, name='close'),
    path('positions.json', views.positions_json, name='positions_json'),
]
