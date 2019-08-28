from django.urls import path, re_path
from django.conf.urls import url, include
from django.contrib.auth import login
from django.contrib import admin

urlpatterns = [
    path('', include('interface.urls')),
    path('admin/', admin.site.urls),
]