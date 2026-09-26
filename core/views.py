import django
from django.shortcuts import render


def home(request):
    """Render the project landing page."""
    return render(request, "core/home.html", {"django_version": django.get_version()})
