"""Shared E2E fixtures.

Deliberately does not override pytest-django's ``django_db_setup`` or
``django_db_blocker``: ``live_server`` depends on the real ones.
"""

import os

# Playwright's sync API keeps an asyncio loop "running" in the main thread for
# its whole session lifetime (it drives the driver through greenlets, so the
# loop created by sync_playwright().start() never goes idle). Django's
# SynchronousOnlyOperation guard reads that as "async context" and blocks the
# test database setup and fixture writes.
#
# This is a false positive, not async code: everything here is synchronous and
# the live server runs in its own thread. Django documents this variable for
# exactly this case. Without it every E2E test errors at setup.
# Negative control: remove this line -> SynchronousOnlyOperation on every test.
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "1")

import pytest

# The test database is disposable; this password exists only inside it.
E2E_PASSWORD = "E2e-Sup3r!Seguro9"


@pytest.fixture
def server_url(live_server):
    """Server URL bound to the test database."""
    return live_server.url


@pytest.fixture
def staff_user(django_user_model):
    return django_user_model.objects.create_user(
        username="e2e-staff", password=E2E_PASSWORD, is_staff=True
    )


@pytest.fixture
def regular_user(django_user_model):
    return django_user_model.objects.create_user(
        username="e2e-regular", password=E2E_PASSWORD
    )


@pytest.fixture
def login(page, server_url):
    """Log in through the real form, not through the test client."""
    def _login(username):
        page.goto(f"{server_url}/login/")
        page.fill("#id_username", username)
        page.fill("#id_password", E2E_PASSWORD)
        page.click("button[type=submit]")
        page.wait_for_load_state("networkidle")
    return _login
