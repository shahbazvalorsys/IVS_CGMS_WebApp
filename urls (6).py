from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("accounts/login/", views.LoginView.as_view(), name="login"),
    path("accounts/logout/", LogoutView.as_view(), name="logout"),
    path("accounts/password/", views.PasswordChangeView.as_view(), name="password_change"),
    path("audit/", views.audit_list, name="audit_list"),
    path("i18n/setlang/", views.set_language, name="set_language"),
]
