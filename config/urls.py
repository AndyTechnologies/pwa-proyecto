"""Root URL configuration.

Auth routes are declared explicitly (rather than via ``include()``) so the
Class-Based Views required by the assignment are visible at a glance.
"""

from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from tasks.views import HomeRedirectView, LoginView, RegisterView

urlpatterns = [
    path("", HomeRedirectView.as_view(), name="home"),
    path("admin/", admin.site.urls),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("register/", RegisterView.as_view(), name="register"),
    # Mounted under /tasks/ to match the routes described in the assignment
    # (/tasks/, /tasks/create/, /tasks/<id>/edit/, ...).
    path("tasks/", include("tasks.urls")),
]
