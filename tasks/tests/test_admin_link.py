"""Defect 11: the nav offered "Administrar sitio" to non-staff users.

Every authenticated user saw the admin link, including users with no staff
privileges. Clicking it landed on a redirect to the admin login: a dead end
that also confirmed an administrative area exists.

Hiding the link is a *usability* fix, not the security boundary. The real
boundary is ``django.contrib.admin``'s own permission check
(``AdminSite.has_permission``), which the nav never participated in. The tests
below therefore assert two separate things:

* the link is absent for non-staff and present for staff (usability);
* a non-staff user still cannot reach the admin by typing the URL (security,
  independent of the template).

Keeping both means a future refactor that re-exposes the link cannot be
mistaken for a privilege escalation, and a future bug in the admin middleware
cannot be hidden by the link being absent.
"""

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from . import STRONG_PASSWORD, TaskFactoryTestCase

ADMIN_LINK_LABEL = "Administrar sitio"


class AdminLinkVisibilityTests(TaskFactoryTestCase):
    """The nav should not advertise the admin to users who cannot use it."""

    def setUp(self):
        super().setUp()
        self.staff = self.make_user("con-acceso", is_staff=True)
        self.regular = self.make_user("sin-acceso", is_staff=False)

    def nav(self, url=None):
        return (self.client.get(url or reverse("tasks:task-list"))).content.decode()

    def test_a_non_staff_user_does_not_see_the_admin_link(self):
        self.login(self.regular)

        html = self.nav()

        self.assertNotIn(ADMIN_LINK_LABEL, html)
        self.assertNotIn("/admin/", html)

    def test_a_staff_user_does_see_the_admin_link(self):
        self.login(self.staff)

        self.assertIn(ADMIN_LINK_LABEL, self.nav())

    def test_the_link_points_at_the_admin_index(self):
        self.login(self.staff)

        self.assertIn(reverse("admin:index"), self.nav())

    def test_a_non_staff_user_still_sees_the_rest_of_the_nav(self):
        # Hiding the admin must not take the session controls with it.
        self.login(self.regular)

        html = self.nav()

        self.assertIn("Cerrar sesión", html)
        self.assertIn("Mis tareas", html)
        self.assertIn(self.regular.username, html)

    def test_an_anonymous_visitor_sees_no_admin_link(self):
        self.assertNotIn(ADMIN_LINK_LABEL, self.nav(reverse("login")))

    def test_no_page_exposes_the_admin_url_to_a_non_staff_user(self):
        self.login(self.regular)

        for url in [
            reverse("tasks:task-list"),
            reverse("tasks:task-create"),
            reverse("tasks:public-task-list"),
            reverse("tasks:shared-task-list"),
        ]:
            with self.subTest(url=url):
                self.assertNotIn("/admin/", self.nav(url))


class AdminAccessBoundaryTests(TestCase):
    """The template is not the security boundary; prove the real one holds."""

    def setUp(self):
        self.password = STRONG_PASSWORD
        self.staff = User.objects.create_user(
            "staff", "s@e.com", self.password, is_staff=True
        )
        self.regular = User.objects.create_user(
            "regular", "r@e.com", self.password
        )

    def test_a_non_staff_user_is_refused_by_the_admin(self):
        self.client.login(username="regular", password=self.password)

        response = self.client.get(reverse("admin:index"))

        # Redirected away, never a 200 on the admin index.
        self.assertNotEqual(response.status_code, 200)
        self.assertIn(reverse("admin:login"), response.url)

    def test_a_staff_user_reaches_the_admin_index(self):
        self.client.login(username="staff", password=self.password)

        self.assertEqual(self.client.get(reverse("admin:index")).status_code, 200)

    def test_an_anonymous_visitor_is_refused_by_the_admin(self):
        response = self.client.get(reverse("admin:index"))

        self.assertNotEqual(response.status_code, 200)
        self.assertIn(reverse("admin:login"), response.url)
