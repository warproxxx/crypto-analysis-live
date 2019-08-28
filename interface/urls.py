from django.contrib import admin
from django.urls import path
from interface.views import index, coin_page

urlpatterns = [
    path('', index, name="index"),
    path(r'coinwise/<str:symbol>/', coin_page, name="coin_page"),
]
