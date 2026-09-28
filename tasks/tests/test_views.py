"""End-to-end view tests: the happy paths through every CBV.

Authorization lives in ``test_permissions.py``; this file checks that each
view answers 200/302 as documented, that the writes actually land in the
database, and that the ``messages`` framework is wired up.
"""

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse

from tasks.models import Priority, Tag, Task, Visibility

from . import STRONG_PASSWORD, TaskFactoryTestCase

User = get_user_model()


def fast_passwords(cls):
    """Class decorator: hash test passwords with MD5 instead of PBKDF2.

    Key stretching is pure overhead here and asserts nothing about the
    product. Password *strength* still comes from ``AUTH_PASSWORD_VALIDATORS``.
    """
    return override_settings(
        PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
    )(cls)


def rendered_messages(response):
    """Every message queued while handling the request, as plain strings."""
    return [str(message) for message in messages.get_messages(response.wsgi_request)]


@fast_passwords
class RegisterViewTests(TaskFactoryTestCase):
    def test_get_renders_the_registration_form(self):
        response = self.client.get(reverse("register"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "tasks/register.html")
        self.assertContains(response, "Crear cuenta")
        self.assertEqual(
            list(response.context["form"].fields),
            ["username", "password1", "password2"],
        )

    def test_valid_post_creates_the_user_and_redirects_to_login(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "estudiante_nuevo",
                "password1": STRONG_PASSWORD,
                "password2": STRONG_PASSWORD,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("login"))

    def test_valid_post_stores_a_user_that_authenticates(self):
        self.client.post(
            reverse("register"),
            {
                "username": "estudiante_nuevo",
                "password1": STRONG_PASSWORD,
                "password2": STRONG_PASSWORD,
            },
        )

        self.assertTrue(User.objects.filter(username="estudiante_nuevo").exists())
        created = User.objects.get(username="estudiante_nuevo")
        self.assertTrue(created.check_password(STRONG_PASSWORD))

    def test_valid_post_does_not_log_the_new_user_in(self):
        """The view deliberately redirects to the login screen, not to /tasks/."""
        self.client.post(
            reverse("register"),
            {
                "username": "estudiante_nuevo",
                "password1": STRONG_PASSWORD,
                "password2": STRONG_PASSWORD,
            },
        )

        self.assertNotIn("_auth_user_id", self.client.session)

    def test_valid_post_queues_a_success_message(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "estudiante_nuevo",
                "password1": STRONG_PASSWORD,
                "password2": STRONG_PASSWORD,
            },
        )

        self.assertTrue(rendered_messages(response))

    def test_invalid_post_rerenders_the_form_with_errors(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "estudiante_nuevo",
                "password1": STRONG_PASSWORD,
                "password2": "otra-clave-distinta-2026!",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)
        self.assertContains(response, "Los dos campos de contraseña no coinciden.")
        self.assertEqual(User.objects.filter(username="estudiante_nuevo").count(), 0)

    def test_duplicate_username_is_rejected(self):
        self.make_user("estudiante_nuevo")

        response = self.client.post(
            reverse("register"),
            {
                "username": "estudiante_nuevo",
                "password1": STRONG_PASSWORD,
                "password2": STRONG_PASSWORD,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.filter(username="estudiante_nuevo").count(), 1)


@fast_passwords
class LoginViewTests(TaskFactoryTestCase):
    def setUp(self):
        super().setUp()
        self.user = self.make_user("estudiante", STRONG_PASSWORD)

    def test_get_renders_the_login_form(self):
        response = self.client.get(reverse("login"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "registration/login.html")
        self.assertContains(response, "Iniciar sesión")

    def test_valid_post_redirects_and_opens_a_session(self):
        response = self.client.post(
            reverse("login"),
            {"username": self.user.username, "password": STRONG_PASSWORD},
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("_auth_user_id", self.client.session)

    def test_valid_post_honours_the_next_parameter(self):
        response = self.client.post(
            f"{reverse('login')}?next={self.task_list_url()}",
            {"username": self.user.username, "password": STRONG_PASSWORD},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.task_list_url())

    def test_invalid_post_rerenders_with_an_error(self):
        response = self.client.post(
            reverse("login"),
            {"username": self.user.username, "password": "contraseña-equivocada"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No pudimos iniciar tu sesión")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_unknown_username_rerenders_with_an_error(self):
        response = self.client.post(
            reverse("login"),
            {"username": "no-existe", "password": STRONG_PASSWORD},
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)


@fast_passwords
class TaskListViewTests(TaskFactoryTestCase):
    def setUp(self):
        super().setUp()
        self.user = self.make_user("listado")
        self.task = self.make_task(self.user, title="Mi tarea visible")

    def test_the_list_requires_authentication(self):
        response = self.client.get(self.task_list_url())

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_the_list_renders_for_its_owner(self):
        self.login(self.user)

        response = self.client.get(self.task_list_url())

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "tasks/task_list.html")
        self.assertContains(response, self.task.title)

    def test_the_context_exposes_the_filter_state(self):
        self.login(self.user)

        response = self.client.get(self.task_list_url())

        for key in ("tasks", "status", "tag", "sort", "allowed_sorts", "all_tags"):
            with self.subTest(key=key):
                self.assertIn(key, response.context)

    def test_an_empty_list_renders_the_empty_state(self):
        empty = self.make_user("sin_tareas")
        self.login(empty)

        response = self.client.get(self.task_list_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Todavía no tenés tareas")


@fast_passwords
class TaskCreateViewTests(TaskFactoryTestCase):
    def setUp(self):
        super().setUp()
        self.user = self.make_user("creador")
        self.login(self.user)

    def test_get_renders_the_create_form(self):
        response = self.client.get(self.task_create_url())

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "tasks/task_form.html")
        self.assertContains(response, "Nueva tarea")

    def test_get_requires_authentication(self):
        self.logout()

        response = self.client.get(self.task_create_url())

        self.assertEqual(response.status_code, 302)

    def test_valid_post_creates_a_task_owned_by_the_request_user(self):
        response = self.client.post(
            self.task_create_url(),
            self.task_form_data(title="Tarea recién creada", tags_input="estudio"),
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.task_list_url())

        created = Task.objects.get(title="Tarea recién creada")
        self.assertEqual(created.owner, self.user)
        self.assertEqual(created.priority, Priority.MEDIUM)
        self.assertEqual(created.visibility, Visibility.PRIVATE)
        self.assertIs(created.completed, False)

    def test_valid_post_persists_the_parsed_tags(self):
        self.client.post(
            self.task_create_url(),
            self.task_form_data(title="Con etiquetas", tags_input="Django, universidad"),
        )

        created = Task.objects.get(title="Con etiquetas")
        self.assertCountEqual(
            sorted(tag.name for tag in created.tags.all()),
            ["django", "universidad"],
        )

    def test_valid_post_cannot_assign_the_task_to_another_user(self):
        victim = self.make_user("ajeno")

        self.client.post(
            self.task_create_url(),
            self.task_form_data(title="No es del ajeno", owner=victim.pk),
        )

        self.assertEqual(Task.objects.get(title="No es del ajeno").owner, self.user)

    def test_valid_post_queues_a_success_message(self):
        response = self.client.post(
            self.task_create_url(),
            self.task_form_data(title="Tarea con aviso"),
        )

        self.assertTrue(rendered_messages(response))

    def test_invalid_post_rerenders_with_errors_and_creates_nothing(self):
        response = self.client.post(self.task_create_url(), self.task_form_data(title=""))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)
        self.assertEqual(Task.objects.count(), 0)

    def test_the_success_message_is_rendered_on_the_next_page(self):
        self.client.post(self.task_create_url(), self.task_form_data(title="Con aviso"))

        response = self.client.get(self.task_list_url(), follow=True)

        self.assertContains(response, "Tarea creada correctamente.")


@fast_passwords
class TaskDetailViewTests(TaskFactoryTestCase):
    def setUp(self):
        super().setUp()
        self.owner = self.make_user("detalle_duena")
        self.task = self.make_task(
            self.owner,
            title="Tarea detallada",
            description="Contenido de la tarea.",
            visibility=Visibility.PUBLIC,
        )
        self.tag = self.make_tag("django")
        self.task.tags.set([self.tag])

    def test_detail_renders_for_a_readable_task(self):
        response = self.client.get(self.detail_url(self.task.pk))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "tasks/task_detail.html")
        self.assertContains(response, self.task.title)
        self.assertContains(response, self.task.description)
        self.assertContains(response, "django")

    def test_the_context_exposes_the_task_and_the_ownership_hint(self):
        response = self.client.get(self.detail_url(self.task.pk))

        self.assertEqual(response.context["task"], self.task)
        self.assertIs(response.context["is_owner"], False)

    def test_detail_reports_ownership_to_the_owner(self):
        self.login(self.owner)

        response = self.client.get(self.detail_url(self.task.pk))

        self.assertIs(response.context["is_owner"], True)

    def test_an_unknown_pk_returns_404(self):
        response = self.client.get(self.detail_url(self.task.pk + 999))

        self.assertEqual(response.status_code, 404)


@fast_passwords
class TaskUpdateViewTests(TaskFactoryTestCase):
    def setUp(self):
        super().setUp()
        self.owner = self.make_user("editor")
        self.task = self.make_task(self.owner, title="Título original")
        self.login(self.owner)

    def test_get_renders_the_edit_form_prefilled(self):
        response = self.client.get(self.update_url(self.task.pk))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "tasks/task_form.html")
        self.assertContains(response, "Título original")
        self.assertContains(response, "Guardar cambios")

    def test_post_persists_the_changes(self):
        response = self.client.post(
            self.update_url(self.task.pk),
            self.task_form_data(
                title="Título corregido",
                description="Descripción corregida.",
                priority=Priority.HIGH,
                visibility=Visibility.PUBLIC,
            ),
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.task_list_url())

        self.task.refresh_from_db()
        self.assertEqual(self.task.title, "Título corregido")
        self.assertEqual(self.task.description, "Descripción corregida.")
        self.assertEqual(self.task.priority, Priority.HIGH)
        self.assertEqual(self.task.visibility, Visibility.PUBLIC)

    def test_post_keeps_the_same_row_instead_of_creating_a_second_task(self):
        before = Task.objects.count()

        self.client.post(
            self.update_url(self.task.pk),
            self.task_form_data(title="Otro título"),
        )

        self.assertEqual(Task.objects.count(), before)
        self.assertEqual(Task.objects.get(pk=self.task.pk).title, "Otro título")

    def test_post_can_change_the_tags(self):
        self.client.post(self.update_url(self.task.pk), self.task_form_data(tags_input="examen"))

        self.task.refresh_from_db()
        self.assertEqual([tag.name for tag in self.task.tags.all()], ["examen"])

    def test_post_queues_a_success_message(self):
        response = self.client.post(
            self.update_url(self.task.pk),
            self.task_form_data(title="Con aviso"),
        )

        self.assertTrue(rendered_messages(response))

    def test_invalid_post_rerenders_and_keeps_the_stored_task_untouched(self):
        response = self.client.post(self.update_url(self.task.pk), self.task_form_data(title=""))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)
        self.task.refresh_from_db()
        self.assertEqual(self.task.title, "Título original")


@fast_passwords
class TaskDeleteViewTests(TaskFactoryTestCase):
    def setUp(self):
        super().setUp()
        self.owner = self.make_user("borrador")
        self.task = self.make_task(self.owner, title="Tarea descartable")
        self.login(self.owner)

    def test_get_renders_the_confirmation_page(self):
        response = self.client.get(self.delete_url(self.task.pk))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "tasks/task_confirm_delete.html")
        self.assertContains(response, "¿Eliminar esta tarea?")
        self.assertContains(response, self.task.title)

    def test_get_alone_does_not_delete_anything(self):
        self.client.get(self.delete_url(self.task.pk))

        self.assertTrue(Task.objects.filter(pk=self.task.pk).exists())

    def test_post_deletes_the_task(self):
        response = self.client.post(self.delete_url(self.task.pk))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.task_list_url())
        self.assertFalse(Task.objects.filter(pk=self.task.pk).exists())

    def test_post_queues_a_success_message(self):
        response = self.client.post(self.delete_url(self.task.pk))

        self.assertTrue(rendered_messages(response))

    def test_the_success_message_is_rendered_on_the_next_page(self):
        self.client.post(self.delete_url(self.task.pk))

        response = self.client.get(self.task_list_url(), follow=True)

        self.assertContains(response, "Tarea eliminada correctamente.")

    def test_deleting_a_task_keeps_its_tags_around_for_reuse(self):
        tag = self.make_tag("reutilizable")
        self.task.tags.set([tag])

        self.client.post(self.delete_url(self.task.pk))

        self.assertTrue(Tag.objects.filter(pk=tag.pk).exists())


@fast_passwords
class TaskCompleteToggleViewTests(TaskFactoryTestCase):
    def setUp(self):
        super().setUp()
        self.owner = self.make_user("alternador")
        self.task = self.make_task(self.owner, completed=False)
        self.login(self.owner)

    def test_post_flips_pending_to_completed(self):
        response = self.client.post(self.toggle_url(self.task.pk))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.detail_url(self.task.pk))
        self.task.refresh_from_db()
        self.assertIs(self.task.completed, True)

    def test_post_flips_completed_back_to_pending(self):
        self.client.post(self.toggle_url(self.task.pk))

        self.client.post(self.toggle_url(self.task.pk))

        self.task.refresh_from_db()
        self.assertIs(self.task.completed, False)

    def test_post_queues_a_message_about_the_new_state(self):
        response = self.client.post(self.toggle_url(self.task.pk))

        self.assertIn(
            "Tarea marcada como completada.",
            rendered_messages(response),
        )

    def test_post_leaves_the_other_fields_untouched(self):
        self.client.post(self.toggle_url(self.task.pk))

        self.task.refresh_from_db()
        self.assertEqual(self.task.title, self.task.title)
        self.assertEqual(self.task.priority, Priority.MEDIUM)
        self.assertEqual(self.task.visibility, Visibility.PRIVATE)


@fast_passwords
class PublicTaskListViewTests(TaskFactoryTestCase):
    def setUp(self):
        super().setUp()
        self.author = self.make_user("autor")
        self.public_task = self.make_task(
            self.author, title="Tarea pública", visibility=Visibility.PUBLIC
        )
        self.private_task = self.make_task(
            self.author, title="Tarea privada", visibility=Visibility.PRIVATE
        )

    def test_the_public_list_renders_for_anonymous_visitors(self):
        response = self.client.get(self.public_list_url())

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "tasks/public_task_list.html")
        self.assertContains(response, self.public_task.title)

    def test_the_public_list_hides_non_public_tasks(self):
        response = self.client.get(self.public_list_url())

        self.assertNotContains(response, self.private_task.title)

    def test_the_public_list_carries_no_write_controls(self):
        """Read-only browsing: no toggle endpoint and no destructive action."""
        response = self.client.get(self.public_list_url())

        self.assertNotContains(response, self.toggle_url(self.public_task.pk))
        self.assertNotContains(response, self.update_url(self.public_task.pk))
        self.assertNotContains(response, self.delete_url(self.public_task.pk))
        self.assertNotContains(response, "Eliminar")

    def test_the_public_list_carries_no_write_controls_for_a_signed_in_visitor(self):
        self.login(self.make_user("curioso"))

        response = self.client.get(self.public_list_url())

        self.assertNotContains(response, self.toggle_url(self.public_task.pk))
        self.assertNotContains(response, "Eliminar")

    def test_the_public_list_still_links_to_the_readable_task(self):
        response = self.client.get(self.public_list_url())

        self.assertContains(response, self.detail_url(self.public_task.pk))

    def test_an_empty_public_list_renders_the_empty_state(self):
        self.public_task.delete()

        response = self.client.get(self.public_list_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Todavía no hay tareas públicas")


@fast_passwords
class SharedTaskListViewTests(TaskFactoryTestCase):
    def setUp(self):
        super().setUp()
        self.viewer = self.make_user("espectadora")
        self.other = self.make_user("colega")
        self.shared_task = self.make_task(
            self.other, title="Tarea de un colega", visibility=Visibility.AUTHENTICATED
        )
        self.login(self.viewer)

    def test_the_shared_list_renders(self):
        response = self.client.get(self.shared_list_url())

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "tasks/shared_task_list.html")
        self.assertContains(response, self.shared_task.title)

    def test_the_shared_list_carries_no_write_controls(self):
        response = self.client.get(self.shared_list_url())

        self.assertNotContains(response, self.toggle_url(self.shared_task.pk))
        self.assertNotContains(response, "Eliminar")

    def test_the_shared_list_requires_authentication(self):
        self.logout()

        response = self.client.get(self.shared_list_url())

        self.assertEqual(response.status_code, 302)
