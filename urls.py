from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("platform-admin/", admin.site.urls),
    path("", include("apps.accounts.urls")),
]
