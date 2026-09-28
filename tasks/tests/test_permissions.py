"""Authorization matrix for the Task Manager.

Every entry point of the app is exercised here, for the three kinds of viewer
(anonymous, authenticated non-owner, owner) and the three visibility levels.

The product policy under test:

* write access belongs to the owner alone, enforced at the queryset level
  (``owned_by``), so a foreign task is never fetched and answers **404**;
* read access follows ``visible_to``: anonymous sees only PUBLIC, a
  registered non-owner sees AUTHENTICATED + PUBLIC, the owner sees all of
  their own.

A 403 anywhere in the write matrix would be a defect: 403 confirms that the
task exists, which is exactly the IDOR leak ``owned_by`` exists to prevent.
"""

from django.contrib.auth.models import AnonymousUser
from django.test import override_settings
from django.urls import reverse

from tasks.models import Task, Visibility

from . import STRONG_PASSWORD, TaskFactoryTestCase

READ_ONLY_MARKER = "Solo lectura"


def fast_passwords(cls):
    """Class decorator: hash test passwords with MD5 instead of PBKDF2.

    This suite creates a couple of users per test and nothing else, so key
    stretching is the dominant cost of an otherwise millisecond-fast run. MD5
    is a Django built-in and keeps ``check_password`` and the login flow
    behaving identically; password *strength* is still enforced by
    ``AUTH_PASSWORD_VALIDATORS``, never by the hasher.
    """
    return override_settings(
        PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
    )(cls)


@fast_passwords
class VisibilityMatrixTestCase(TaskFactoryTestCase):
    """Base fixture: one owner, one registered stranger, three tasks."""

    def setUp(self):
        super().setUp()
        self.owner = self.make_user("duena")
        self.stranger = self.make_user("vecina")
        self.private_task = self.make_task(
            self.owner, title="Diario privado", visibility=Visibility.PRIVATE
        )
        self.shared_task = self.make_task(
            self.owner, title="Diario compartido", visibility=Visibility.AUTHENTICATED
        )
        self.public_task = self.make_task(
            self.owner, title="Diario publico", visibility=Visibility.PUBLIC
        )


class AnonymousReadPolicyTests(VisibilityMatrixTestCase):
    def test_anonymous_gets_404_on_a_private_task(self):
        response = self.client.get(self.detail_url(self.private_task.pk))

        self.assertEqual(response.status_code, 404)

    def test_anonymous_gets_404_on_a_task_shared_with_registered_users(self):
        response = self.client.get(self.detail_url(self.shared_task.pk))

        self.assertEqual(response.status_code, 404)

    def test_anonymous_gets_200_on_a_public_task(self):
        response = self.client.get(self.detail_url(self.public_task.pk))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.public_task.title)

    def test_anonymous_sees_a_read_only_public_task(self):
        response = self.client.get(self.detail_url(self.public_task.pk))

        self.assertContains(response, READ_ONLY_MARKER)
        self.assertNotContains(response, "Eliminar")


class NonOwnerReadPolicyTests(VisibilityMatrixTestCase):
    def setUp(self):
        super().setUp()
        self.login(self.stranger)

    def test_non_owner_gets_404_on_a_private_task(self):
        response = self.client.get(self.detail_url(self.private_task.pk))

        self.assertEqual(response.status_code, 404)

    def test_non_owner_gets_200_read_only_on_a_shared_task(self):
        response = self.client.get(self.detail_url(self.shared_task.pk))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, READ_ONLY_MARKER)
        self.assertNotContains(response, "Eliminar")
        self.assertNotContains(response, self.toggle_url(self.shared_task.pk))

    def test_non_owner_gets_200_read_only_on_a_public_task(self):
        response = self.client.get(self.detail_url(self.public_task.pk))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, READ_ONLY_MARKER)
        self.assertNotContains(response, self.update_url(self.public_task.pk))


class OwnerReadPolicyTests(VisibilityMatrixTestCase):
    def setUp(self):
        super().setUp()
        self.login(self.owner)

    def test_owner_gets_200_on_a_private_task(self):
        response = self.client.get(self.detail_url(self.private_task.pk))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.private_task.title)

    def test_owner_gets_200_on_a_shared_task(self):
        response = self.client.get(self.detail_url(self.shared_task.pk))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.shared_task.title)

    def test_owner_gets_200_on_a_public_task(self):
        response = self.client.get(self.detail_url(self.public_task.pk))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.public_task.title)

    def test_owner_detail_page_exposes_the_write_controls(self):
        response = self.client.get(self.detail_url(self.public_task.pk))

        self.assertContains(response, self.update_url(self.public_task.pk))
        self.assertContains(response, self.delete_url(self.public_task.pk))
        self.assertContains(response, self.toggle_url(self.public_task.pk))
        self.assertContains(response, "Eliminar")


class NonOwnerWritePolicyTests(VisibilityMatrixTestCase):
    """A stranger must get 404 - never 403 - on every mutable entry point."""

    def setUp(self):
        super().setUp()
        self.login(self.stranger)
        self.other_task = self.public_task

    def assert_not_authorized(self, response):
        self.assertEqual(response.status_code, 404)
        self.assertNotEqual(response.status_code, 403)

    def test_non_owner_gets_404_not_403_on_the_edit_page(self):
        response = self.client.get(self.update_url(self.other_task.pk))

        self.assert_not_authorized(response)

    def test_non_owner_gets_404_not_403_on_the_delete_page(self):
        response = self.client.get(self.delete_url(self.other_task.pk))

        self.assert_not_authorized(response)

    def test_non_owner_gets_404_not_403_when_posting_the_delete_form(self):
        response = self.client.post(self.delete_url(self.other_task.pk))

        self.assert_not_authorized(response)

    def test_non_owner_gets_404_not_403_when_posting_the_toggle(self):
        response = self.client.post(self.toggle_url(self.other_task.pk))

        self.assert_not_authorized(response)

    def test_a_rejected_toggle_leaves_the_task_untouched(self):
        self.other_task.completed = False
        self.other_task.save(update_fields=["completed"])

        self.client.post(self.toggle_url(self.other_task.pk))
        self.other_task.refresh_from_db()

        self.assertIs(self.other_task.completed, False)

    def test_a_rejected_delete_leaves_the_task_untouched(self):
        self.client.post(self.delete_url(self.other_task.pk))

        self.assertTrue(Task.objects.filter(pk=self.other_task.pk).exists())


class AnonymousWritePolicyTests(VisibilityMatrixTestCase):
    def setUp(self):
        super().setUp()
        self.public_task_url = self.detail_url(self.public_task.pk)

    def test_anonymous_is_redirected_from_the_task_list(self):
        response = self.client.get(self.task_list_url())

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f"{reverse('login')}?next={self.task_list_url()}")

    def test_anonymous_is_redirected_from_the_create_page(self):
        response = self.client.get(self.task_create_url())

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f"{reverse('login')}?next={self.task_create_url()}")

    def test_anonymous_is_redirected_from_the_shared_list(self):
        response = self.client.get(self.shared_list_url())

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f"{reverse('login')}?next={self.shared_list_url()}")

    def test_anonymous_is_redirected_when_posting_a_new_task(self):
        response = self.client.post(self.task_create_url(), {"title": "Intrusa"})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Task.objects.filter(title="Intrusa").count(), 0)

    def test_anonymous_is_redirected_when_posting_a_toggle(self):
        response = self.client.post(self.toggle_url(self.public_task.pk))

        self.assertEqual(response.status_code, 302)
        self.public_task.refresh_from_db()
        self.assertIs(self.public_task.completed, False)

    def test_anonymous_may_reach_the_public_list(self):
        response = self.client.get(self.public_list_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.public_task.title)

    def test_anonymous_may_reach_a_public_detail(self):
        response = self.client.get(self.public_task_url)

        self.assertEqual(response.status_code, 200)


class ToggleMethodPolicyTests(VisibilityMatrixTestCase):
    def setUp(self):
        super().setUp()
        self.login(self.owner)

    def test_get_on_the_toggle_url_returns_405(self):
        response = self.client.get(self.toggle_url(self.private_task.pk))

        self.assertEqual(response.status_code, 405)

    def test_get_on_the_toggle_url_never_changes_the_task(self):
        self.private_task.completed = False
        self.private_task.save(update_fields=["completed"])

        self.client.get(self.toggle_url(self.private_task.pk))
        self.private_task.refresh_from_db()

        self.assertIs(self.private_task.completed, False)

    def test_post_on_the_toggle_url_is_accepted(self):
        response = self.client.post(self.toggle_url(self.private_task.pk))

        self.assertEqual(response.status_code, 302)


@fast_passwords
class LogoutMethodPolicyTests(TaskFactoryTestCase):
    def setUp(self):
        super().setUp()
        self.user = self.make_user("sesion")
        self.login(self.user)

    def test_get_on_logout_returns_405(self):
        response = self.client.get(reverse("logout"))

        self.assertEqual(response.status_code, 405)

    def test_get_on_logout_keeps_the_session_open(self):
        self.client.get(reverse("logout"))

        self.assertIn("_auth_user_id", self.client.session)

    def test_post_on_logout_succeeds_and_closes_the_session(self):
        response = self.client.post(reverse("logout"))

        self.assertEqual(response.status_code, 302)
        self.assertNotIn("_auth_user_id", self.client.session)


@fast_passwords
class ListScopingTests(VisibilityMatrixTestCase):
    def test_owner_list_never_contains_another_users_tasks(self):
        self.login(self.owner)
        other = self.make_user("otro")
        foreign = self.make_task(other, title="Tarea ajena memorable")

        response = self.client.get(self.task_list_url())

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, foreign.title)
        self.assertNotContains(response, self.detail_url(foreign.pk))

    def test_shared_list_contains_only_other_peoples_tasks(self):
        self.login(self.stranger)

        response = self.client.get(self.shared_list_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.shared_task.title)
        self.assertContains(response, self.public_task.title)
        self.assertNotContains(response, self.private_task.title)

    def test_shared_list_never_contains_the_viewers_own_tasks(self):
        own = self.make_task(self.stranger, title="Mi propia tarea compartida")
        self.login(self.stranger)

        response = self.client.get(self.shared_list_url())

        self.assertNotContains(response, own.title)
        self.assertNotContains(response, self.detail_url(own.pk))

    def test_public_list_contains_only_public_tasks(self):
        self.make_task(self.stranger, title="Privada ajena")

        response = self.client.get(self.public_list_url())

        self.assertContains(response, self.public_task.title)
        self.assertNotContains(response, self.private_task.title)
        self.assertNotContains(response, self.shared_task.title)


@fast_passwords
class QuerysetPolicyTests(VisibilityMatrixTestCase):
    """The policies themselves, asserted directly on the queryset API."""

    def pks(self, queryset):
        return set(queryset.values_list("pk", flat=True))

    # -- write policy --------------------------------------------------
    def test_owned_by_returns_only_that_users_tasks(self):
        other = self.make_user("ajeno")
        self.make_task(other, title="Ajena")

        owned = self.pks(Task.objects.owned_by(self.owner))

        self.assertEqual(
            owned,
            {self.private_task.pk, self.shared_task.pk, self.public_task.pk},
        )

    def test_owned_by_is_empty_for_a_user_without_tasks(self):
        self.assertEqual(list(Task.objects.owned_by(self.stranger)), [])

    def test_owned_by_ignores_visibility_and_only_honours_ownership(self):
        """``owned_by`` is the *write* policy, so visibility is irrelevant."""
        other = self.make_user("sin_relacion")

        for task in (self.private_task, self.shared_task, self.public_task):
            with self.subTest(task=task.title):
                self.assertIn(task.pk, self.pks(Task.objects.owned_by(self.owner)))
        self.assertEqual(list(Task.objects.owned_by(other)), [])

    # -- read policy ---------------------------------------------------
    def test_visible_to_anonymous_returns_only_public_tasks(self):
        visible = self.pks(Task.objects.visible_to(AnonymousUser()))

        self.assertEqual(visible, {self.public_task.pk})

    def test_visible_to_registered_non_owner_returns_shared_and_public(self):
        visible = self.pks(Task.objects.visible_to(self.stranger))

        self.assertEqual(visible, {self.shared_task.pk, self.public_task.pk})

    def test_visible_to_owner_returns_every_own_task(self):
        visible = self.pks(Task.objects.visible_to(self.owner))

        self.assertEqual(
            visible,
            {self.private_task.pk, self.shared_task.pk, self.public_task.pk},
        )

    def test_visible_to_never_returns_another_users_private_task(self):
        for viewer in (AnonymousUser(), self.stranger):
            with self.subTest(viewer=viewer):
                self.assertNotIn(
                    self.private_task.pk,
                    self.pks(Task.objects.visible_to(viewer)),
                )

    def test_is_editable_by_matches_the_owned_by_policy(self):
        """``is_editable_by`` is a presentation hint, never the enforcement."""
        for task in (self.private_task, self.shared_task, self.public_task):
            with self.subTest(task=task.title):
                self.assertTrue(task.is_editable_by(self.owner))
                self.assertFalse(task.is_editable_by(self.stranger))
                self.assertFalse(task.is_editable_by(AnonymousUser()))
                self.assertIn(task.pk, self.pks(Task.objects.owned_by(self.owner)))


@fast_passwords
class AdminUrlReachabilityTests(TaskFactoryTestCase):
    """The nav links every logged-in page renders must resolve."""

    def setUp(self):
        super().setUp()
        self.user = self.make_user("nav")
        self.login(self.user)

    def test_admin_index_and_register_url_names_resolve(self):
        self.assertEqual(reverse("admin:index"), "/admin/")
        self.assertEqual(reverse("register"), "/register/")

    def test_navigation_helpers_produce_the_documented_paths(self):
        task = self.make_task(self.user)

        self.assertEqual(self.detail_url(task.pk), f"/tasks/{task.pk}/")
        self.assertEqual(self.update_url(task.pk), f"/tasks/{task.pk}/edit/")
        self.assertEqual(self.delete_url(task.pk), f"/tasks/{task.pk}/delete/")
        self.assertEqual(self.toggle_url(task.pk), f"/tasks/{task.pk}/toggle/")

    def test_password_helper_constant_is_usable_for_login(self):
        self.assertTrue(self.user.check_password(STRONG_PASSWORD))
