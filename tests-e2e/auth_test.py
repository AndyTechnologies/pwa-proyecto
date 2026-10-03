"""E2E tests: real browser against a real Django server.

Architectural note: these run against pytest-django's ``live_server``, which
serves the **test database**, not the development one. No dev credentials, no
``./run.sh``, and no risk of touching real data. Login goes through the real
form (that is what makes this E2E instead of another client test).

Chromium cannot be installed here: Playwright's CDN answers 403 geographically
(``Access denied ... not available in your location``). Firefox is available,
so run with ``--browser firefox``.
"""

import pytest
from playwright.sync_api import expect

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


def login(page, server_url, username):
    """Log in through the real form, not through the test client."""
    page.goto(f"{server_url}/login/")
    page.fill("#id_username", username)
    page.fill("#id_password", E2E_PASSWORD)
    page.click("button[type=submit]")
    page.wait_for_load_state("networkidle")


@pytest.mark.django_db
class TestHomePage:
    """The shell every page reuses."""

    def test_home_page_loads(self, page, server_url):
        page.goto(server_url)
        page.wait_for_load_state("networkidle")
        assert page.title()
        expect(page.locator("nav")).to_be_visible()

    def test_navigation_has_session_controls(self, page, server_url):
        page.goto(server_url)
        page.wait_for_load_state("networkidle")
        # Anonymous: the nav must offer login, not session controls.
        expect(page.get_by_role("link", name="Iniciar sesión")).to_be_visible()

    def test_anonymous_does_not_see_admin_link(self, page, server_url):
        # /tasks/ redirects anonymous visitors to the login page.
        page.goto(f"{server_url}/tasks/")
        page.wait_for_load_state("networkidle")
        assert not page.get_by_role("link", name="Administrar sitio").is_visible()
        expect(page.locator("#id_username")).to_be_visible()


@pytest.mark.django_db
class TestAdminLinkGate:
    """The nav gate must track is_staff, not merely authentication."""

    def test_staff_user_sees_the_admin_link(self, page, server_url, staff_user):
        login(page, server_url, staff_user.username)

        expect(page.get_by_role("link", name="Administrar sitio")).to_be_visible()

    def test_non_staff_user_does_not_see_it(self, page, server_url, regular_user):
        login(page, server_url, regular_user.username)

        # Negative control for the test itself: the page and nav really are
        # loaded and functional, so "not visible" means the gate, not a 500.
        expect(page.get_by_role("link", name="Mis tareas")).to_be_visible()
        assert not page.get_by_role("link", name="Administrar sitio").is_visible()

    def test_the_admin_link_points_at_the_admin(self, page, server_url, staff_user):
        login(page, server_url, staff_user.username)

        link = page.get_by_role("link", name="Administrar sitio")
        href = link.get_attribute("href")
        assert href is not None and "/admin/" in href
