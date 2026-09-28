"""Regression tests for the defects found and fixed during development.

The assignment requires that every vulnerability or defect discovered while
building the application becomes a regression test (§38), so this file is not
a catch-all: each test below corresponds to a specific, documented defect and
names it in its docstring. If one of these ever fails again, the corresponding
fix has been undone.

The seven defects were all found between the Semana 5 and Semana 7 cuts and are
narrated in ``docs/milestones/week-7.md``.
"""

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase
from django.urls import NoReverseMatch, reverse

from tasks.forms import TaskForm
from tasks.models import Priority, Tag, Task, Visibility

from . import STRONG_PASSWORD, TaskFactoryTestCase


class IsEditableByRegressions(TaskFactoryTestCase):
    """Defect 1: ``is_editable_by`` was declared as a ``@property``.

    It takes a ``user`` argument, and a property cannot receive arguments:
    ``property.__get__`` calls the function with only the instance, so every
    task detail page raised ``TypeError: is_editable_by() missing 1 required
    positional argument: 'user'``. It must be a plain method.
    """

    def setUp(self):
        super().setUp()
        self.owner = self.make_user("defecto1-owner")
        self.other = self.make_user("defecto1-other")
        self.task = self.make_task(self.owner, title="Detalle")

    def test_is_editable_by_is_a_method_and_not_a_property(self):
        # A property would return a callable bound-method-like object instead of
        # a bool, so assert the return type is genuinely a bool.
        self.assertIsInstance(self.task.is_editable_by(self.owner), bool)

    def test_owner_is_editable_and_non_owner_is_not(self):
        self.assertTrue(self.task.is_editable_by(self.owner))
        self.assertFalse(self.task.is_editable_by(self.other))
        self.assertFalse(self.task.is_editable_by(AnonymousUser()))

    def test_task_detail_renders_for_every_actor(self):
        self.login(self.owner)
        self.assertEqual(
            self.client.get(reverse("tasks:task-detail", args=[self.task.pk])).status_code,
            200,
        )

    def test_task_detail_renders_for_anonymous_on_a_public_task(self):
        public = self.make_task(self.owner, title="Pública", visibility=Visibility.PUBLIC)
        response = self.client.get(reverse("tasks:task-detail", args=[public.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["is_owner"])

    def test_is_owner_context_is_true_only_for_the_owner(self):
        self.login(self.owner)
        response = self.client.get(reverse("tasks:task-detail", args=[self.task.pk]))
        self.assertTrue(response.context["is_owner"])


class AllTagsContextRegressions(TaskFactoryTestCase):
    """Defect 2: ``all_tags`` queried the wrong model.

    The view used ``self.request.user.tasks.order_by("name")``. The reverse
    accessor ``user.tasks`` returns a ``Task`` queryset, and ``Task`` has no
    ``name`` field, so the main task list raised ``FieldError`` for every
    request. The context must contain ``Tag`` instances.
    """

    def setUp(self):
        super().setUp()
        self.user = self.make_user("defecto2-owner")
        self.used_tag = self.make_tag("django")
        self.make_task(self.user, title="Etiquetada", tags=[self.used_tag])

    def test_task_list_renders_without_field_error(self):
        self.login(self.user)
        response = self.client.get(reverse("tasks:task-list"))
        self.assertEqual(response.status_code, 200)

    def test_all_tags_contains_tag_instances(self):
        self.login(self.user)
        response = self.client.get(reverse("tasks:task-list"))

        for tag in response.context["all_tags"]:
            self.assertIsInstance(tag, Tag)

    def test_all_tags_is_scoped_to_the_viewers_own_tasks(self):
        stranger = self.make_user("defecto2-stranger")
        self.make_task(stranger, title="Ajena", tags=[self.make_tag("ajena")])

        self.login(self.user)
        response = self.client.get(reverse("tasks:task-list"))
        names = list(response.context["all_tags"].values_list("name", flat=True))

        self.assertIn("django", names)
        self.assertNotIn("ajena", names)


class RegisterRouteRegressions(TaskFactoryTestCase):
    """Defect 3: the ``register`` route was missing.

    ``base.html`` and the login page link to ``{% url 'register' %}``. With no
    route registered, ``NoReverseMatch`` turned every page reachable by an
    anonymous visitor into a 500, including the public task list.
    """

    def test_register_url_reverses(self):
        self.assertEqual(reverse("register"), "/register/")

    def test_register_page_is_reachable(self):
        self.assertEqual(self.client.get(reverse("register")).status_code, 200)

    def test_anonymous_pages_render_without_a_missing_route_error(self):
        # These are the pages that contain {% url 'register' %}.
        self.assertEqual(self.client.get(reverse("login")).status_code, 200)
        self.assertEqual(self.client.get(reverse("tasks:public-task-list")).status_code, 200)

    def test_registering_creates_a_usable_account(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "nuevo",
                "password1": STRONG_PASSWORD,
                "password2": STRONG_PASSWORD,
            },
        )

        self.assertRedirects(response, reverse("login"))
        user = get_user_model().objects.get(username="nuevo")
        self.assertTrue(user.check_password(STRONG_PASSWORD))
        # Deliberately NOT logged in: registration redirects to the login page
        # instead of opening a session (ADR-004).
        self.assertFalse(response.wsgi_request.user.is_authenticated)


class UpdateViewContextRegressions(TaskFactoryTestCase):
    """Defect 4: ``TaskUpdateView`` had no ``context_object_name``.

    Without it the object was exposed as ``object``, so ``{% if task %}`` in
    ``task_form.html`` was always false and the edit page announced itself as
    "Nueva tarea" while editing an existing one.
    """

    def setUp(self):
        super().setUp()
        self.owner = self.make_user("defecto4-owner")
        self.task = self.make_task(self.owner, title="Para editar")
        self.login(self.owner)

    def test_edit_form_receives_the_task_in_context(self):
        response = self.client.get(reverse("tasks:task-update", args=[self.task.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["task"], self.task)

    def test_edit_page_shows_the_edit_title_not_the_create_one(self):
        response = self.client.get(reverse("tasks:task-update", args=[self.task.pk]))
        self.assertContains(response, "Editar tarea")
        self.assertNotContains(response, "Nueva tarea")

    def test_create_form_has_no_task_in_context(self):
        response = self.client.get(reverse("tasks:task-create"))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("task", response.context)
        self.assertContains(response, "Nueva tarea")

    def test_edit_form_prefills_the_tag_input(self):
        self.task.tags.set([self.make_tag("django")])
        response = self.client.get(reverse("tasks:task-update", args=[self.task.pk]))
        self.assertContains(response, "django")


class BootstrapWidgetRegressions(TaskFactoryTestCase):
    """Defect 5: form widgets rendered without Bootstrap classes.

    Django exposes no way to set widget attributes from a template and
    ``django-widget-tweaks`` is an unjustified dependency (RNF-12), so the
    classes must be applied in ``TaskForm.__init__``.
    """

    def setUp(self):
        super().setUp()
        self.owner = self.make_user("defecto5-owner")

    def test_select_widgets_carry_form_select(self):
        form = TaskForm()
        for name in ("priority", "visibility"):
            self.assertIn("form-select", form.fields[name].widget.attrs["class"])

    def test_text_widgets_carry_form_control(self):
        form = TaskForm()
        for name in ("title", "description", "due_date", "tags_input"):
            self.assertIn("form-control", form.fields[name].widget.attrs["class"])

    def test_checkbox_widget_carries_form_check_input(self):
        form = TaskForm()
        self.assertIn("form-check-input", form.fields["completed"].widget.attrs["class"])

    def test_no_unrelated_dependency_was_introduced(self):
        from django.conf import settings

        installed = {app.split(".")[0] for app in settings.INSTALLED_APPS}
        self.assertNotIn("widget_tweaks", installed)

    def test_bootstrap_select_widget_is_a_real_forms_select(self):
        # Guards against a fix that hardcodes markup instead of using the
        # correct widget class.
        form = TaskForm()
        self.assertIsInstance(form.fields["priority"].widget, forms.Select)


class TagSlugCollisionRegressions(TaskFactoryTestCase):
    """Defect 6: distinct tag names can collide on the unique ``Tag.slug``.

    ``"Python 3"`` and ``"python-3"`` both slugify to ``python-3``. The form
    resolved tags by case-insensitive *name* only, so submitting the second
    name created a row whose slug already existed and raised
    ``IntegrityError``, turning the create form into a 500. Resolution must
    also consider the slug.
    """

    def setUp(self):
        super().setUp()
        self.owner = self.make_user("defecto6-owner")

    def form_payload(self, tags):
        return {
            "title": "Con etiquetas",
            "description": "Descripción.",
            "due_date": "2030-06-01",
            "priority": Priority.MEDIUM,
            "visibility": Visibility.PRIVATE,
            "completed": False,
            "tags_input": tags,
        }

    def test_colliding_slug_does_not_raise(self):
        self.make_tag("python-3", slug="python-3")

        form = TaskForm(data=self.form_payload("Python 3"))
        self.assertTrue(form.is_valid(), form.errors)

        task = form.save(commit=False)
        task.owner = self.owner
        task.save()
        form.save()

        self.assertEqual(list(task.tags.values_list("name", flat=True)), ["python-3"])

    def test_colliding_slug_creates_no_duplicate_tag_row(self):
        self.make_tag("python-3", slug="python-3")

        form = TaskForm(data=self.form_payload("Python 3"))
        self.assertTrue(form.is_valid(), form.errors)
        task = form.save(commit=False)
        task.owner = self.owner
        task.save()
        form.save()

        self.assertEqual(Tag.objects.filter(slug="python-3").count(), 1)

    def test_several_colliding_names_in_one_payload(self):
        self.make_tag("python-3", slug="python-3")

        # Both names lowercase to distinct strings (so ``clean_tags_input``
        # keeps both) yet slugify to the same value, so both must resolve to
        # the single existing tag instead of racing to insert it.
        form = TaskForm(data=self.form_payload("Python 3, python-3"))
        self.assertTrue(form.is_valid(), form.errors)
        task = form.save(commit=False)
        task.owner = self.owner
        task.save()
        form.save()

        self.assertEqual(task.tags.count(), 1)
        self.assertEqual(Tag.objects.count(), 1)

    def test_genuinely_different_tags_are_not_merged(self):
        # "C#" slugifies to "c" and "c-sharp" to "c-sharp": different slugs,
        # so these are two real, distinct tags and must stay separate.
        form = TaskForm(data=self.form_payload("C#, c-sharp"))
        self.assertTrue(form.is_valid(), form.errors)
        task = form.save(commit=False)
        task.owner = self.owner
        task.save()
        form.save()

        self.assertEqual(task.tags.count(), 2)


class UrlMountingRegressions(TaskFactoryTestCase):
    """Defect 7: ``tasks.urls`` was mounted at ``""`` instead of ``"tasks/"``.

    With the include at the root the real routes were ``/<pk>/`` and
    ``/create/``, so the URLs described by the assignment (§36:
    ``/tasks/``, ``/tasks/create/``, ``/tasks/<id>/edit/``) did not exist and
    every link 404'd.
    """

    def setUp(self):
        super().setUp()
        self.owner = self.make_user("defecto7-owner")
        self.task = self.make_task(self.owner, title="Montada")

    def test_every_task_route_sits_under_the_tasks_prefix(self):
        self.assertEqual(reverse("tasks:task-list"), "/tasks/")
        self.assertEqual(reverse("tasks:task-create"), "/tasks/create/")
        self.assertEqual(reverse("tasks:public-task-list"), "/tasks/public/")
        self.assertEqual(reverse("tasks:shared-task-list"), "/tasks/shared/")
        self.assertEqual(
            reverse("tasks:task-detail", args=[self.task.pk]),
            f"/tasks/{self.task.pk}/",
        )
        self.assertEqual(
            reverse("tasks:task-update", args=[self.task.pk]),
            f"/tasks/{self.task.pk}/edit/",
        )
        self.assertEqual(
            reverse("tasks:task-delete", args=[self.task.pk]),
            f"/tasks/{self.task.pk}/delete/",
        )
        self.assertEqual(
            reverse("tasks:task-toggle", args=[self.task.pk]),
            f"/tasks/{self.task.pk}/toggle/",
        )

    def test_detail_is_not_reachable_at_the_root_path(self):
        # The un-prefixed path must not resolve to the task detail.
        self.assertEqual(
            self.client.get(f"/{self.task.pk}/").status_code,
            404,
        )

    def test_the_prefixed_detail_actually_resolves(self):
        self.login(self.owner)
        self.assertEqual(
            self.client.get(f"/tasks/{self.task.pk}/").status_code,
            200,
        )
