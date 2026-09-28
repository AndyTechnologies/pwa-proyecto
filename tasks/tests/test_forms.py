"""Form-level tests for ``TaskForm`` and ``RegisterForm``.

The form is where the assignment's trickiest rules live: a free-text
``tags_input`` field has to be parsed, normalised and resolved into ``Tag``
rows without ever tripping the ``unique`` constraints on ``Tag.name`` and
``Tag.slug``.
"""

from django import forms
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings

from tasks.forms import RegisterForm, TaskForm
from tasks.models import Priority, Tag, Visibility

from . import STRONG_PASSWORD, TaskFactoryTestCase

User = get_user_model()


def fast_passwords(cls):
    """Class decorator: hash test passwords with MD5 instead of PBKDF2.

    Key stretching dominates this file's runtime and asserts nothing about
    the product. Password *strength* still comes from
    ``AUTH_PASSWORD_VALIDATORS``, not from the hasher.
    """
    return override_settings(
        PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
    )(cls)


@fast_passwords
class TaskFormValidDataTests(TaskFactoryTestCase):
    def setUp(self):
        super().setUp()
        self.owner = self.make_user("form_owner")

    def test_valid_data_passes_validation(self):
        form = TaskForm(data=self.task_form_data())

        self.assertTrue(form.is_valid(), form.errors)

    def test_save_creates_a_task_with_the_submitted_values(self):
        form = TaskForm(data=self.task_form_data())
        self.assertTrue(form.is_valid(), form.errors)
        form.instance.owner = self.owner

        task = form.save()

        self.assertEqual(task.title, "Tarea válida")
        self.assertEqual(task.description, "Descripción válida.")
        self.assertEqual(task.due_date.isoformat(), "2030-06-15")
        self.assertEqual(task.priority, Priority.MEDIUM)
        self.assertEqual(task.visibility, Visibility.PRIVATE)
        self.assertIs(task.completed, False)

    def test_an_unbound_form_exposes_no_cleaned_data(self):
        form = TaskForm()

        self.assertFalse(form.is_bound)
        self.assertEqual(list(form.fields), [
            "title",
            "description",
            "due_date",
            "priority",
            "visibility",
            "completed",
            "tags_input",
        ])

    def test_optional_fields_may_be_omitted(self):
        data = self.task_form_data()
        data.pop("completed", None)
        data.pop("tags_input", None)

        form = TaskForm(data=data)

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["tags_input"], [])

    def test_completed_checkbox_is_accepted_when_submitted(self):
        form = TaskForm(data=self.task_form_data(completed="on"))

        self.assertTrue(form.is_valid(), form.errors)
        self.assertIs(form.cleaned_data["completed"], True)


@fast_passwords
class TaskFormRequiredFieldTests(TaskFactoryTestCase):
    REQUIRED_FIELDS = ("title", "description", "due_date")

    def setUp(self):
        super().setUp()
        self.owner = self.make_user("required_owner")

    def test_title_is_required(self):
        for value in ("", "   "):
            with self.subTest(value=repr(value)):
                form = TaskForm(data=self.task_form_data(title=value))
                self.assertFalse(form.is_valid())
                self.assertIn("title", form.errors)

    def test_title_missing_from_the_payload_is_rejected(self):
        data = self.task_form_data()
        del data["title"]

        form = TaskForm(data=data)

        self.assertFalse(form.is_valid())
        self.assertIn("title", form.errors)

    def test_description_is_required(self):
        for value in ("", "   "):
            with self.subTest(value=repr(value)):
                form = TaskForm(data=self.task_form_data(description=value))
                self.assertFalse(form.is_valid())
                self.assertIn("description", form.errors)

    def test_description_missing_from_the_payload_is_rejected(self):
        data = self.task_form_data()
        del data["description"]

        form = TaskForm(data=data)

        self.assertFalse(form.is_valid())
        self.assertIn("description", form.errors)

    def test_due_date_is_required(self):
        for value in ("", "   "):
            with self.subTest(value=repr(value)):
                form = TaskForm(data=self.task_form_data(due_date=value))
                self.assertFalse(form.is_valid())
                self.assertIn("due_date", form.errors)

    def test_due_date_missing_from_the_payload_is_rejected(self):
        data = self.task_form_data()
        del data["due_date"]

        form = TaskForm(data=data)

        self.assertFalse(form.is_valid())
        self.assertIn("due_date", form.errors)

    def test_every_required_field_reports_an_error_when_the_payload_is_empty(self):
        form = TaskForm(data={})

        self.assertFalse(form.is_valid())
        for field in self.REQUIRED_FIELDS:
            with self.subTest(field=field):
                self.assertIn(field, form.errors)


@fast_passwords
class TaskFormDateParsingTests(TaskFactoryTestCase):
    def setUp(self):
        super().setUp()
        self.owner = self.make_user("date_owner")

    def test_invalid_due_date_string_is_rejected(self):
        for value in ("no-es-una-fecha", "2030-13-45", "20300615", "31/02/2030", "15-06"):
            with self.subTest(value=value):
                form = TaskForm(data=self.task_form_data(due_date=value))
                self.assertFalse(form.is_valid())
                self.assertIn("due_date", form.errors)

    def test_valid_iso_due_date_is_parsed_into_a_date_object(self):
        form = TaskForm(data=self.task_form_data(due_date="2030-06-15"))

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["due_date"].isoformat(), "2030-06-15")

    def test_day_first_format_is_accepted_under_the_spanish_locale(self):
        """``LANGUAGE_CODE = "es"`` makes Django parse ``dd/mm/yyyy``.

        Not a laxness bug: it is the localised ``DATE_INPUT_FORMATS`` list
        doing its job, and the widget still renders ``<input type="date">``.
        """
        form = TaskForm(data=self.task_form_data(due_date="15/06/2030"))

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["due_date"].isoformat(), "2030-06-15")


@fast_passwords
class TaskFormPriorityTests(TaskFactoryTestCase):
    def setUp(self):
        super().setUp()
        self.owner = self.make_user("priority_owner")

    def test_priority_accepts_only_the_three_defined_values(self):
        for value in (Priority.LOW, Priority.MEDIUM, Priority.HIGH):
            with self.subTest(value=value):
                form = TaskForm(data=self.task_form_data(priority=value))
                self.assertTrue(form.is_valid(), form.errors)
                self.assertEqual(form.cleaned_data["priority"], value)

    def test_priority_accepts_the_numeric_strings_a_browser_sends(self):
        for value in ("1", "2", "3"):
            with self.subTest(value=value):
                form = TaskForm(data=self.task_form_data(priority=value))
                self.assertTrue(form.is_valid(), form.errors)
                self.assertIsInstance(form.cleaned_data["priority"], int)

    def test_priority_rejects_values_outside_the_choice_list(self):
        for value in (0, 4, -1, 99):
            with self.subTest(value=value):
                form = TaskForm(data=self.task_form_data(priority=value))
                self.assertFalse(form.is_valid())
                self.assertIn("priority", form.errors)

    def test_priority_rejects_non_numeric_text(self):
        for value in ("alta", "media", "baja", ""):
            with self.subTest(value=value):
                form = TaskForm(data=self.task_form_data(priority=value))
                self.assertFalse(form.is_valid())
                self.assertIn("priority", form.errors)


@fast_passwords
class TaskFormVisibilityTests(TaskFactoryTestCase):
    def setUp(self):
        super().setUp()
        self.owner = self.make_user("visibility_owner")

    def test_visibility_accepts_only_the_three_literals(self):
        expected = {
            Visibility.PRIVATE: Visibility.PRIVATE,
            Visibility.AUTHENTICATED: Visibility.AUTHENTICATED,
            Visibility.PUBLIC: Visibility.PUBLIC,
        }
        for submitted, stored in expected.items():
            with self.subTest(value=submitted):
                form = TaskForm(data=self.task_form_data(visibility=submitted))
                self.assertTrue(form.is_valid(), form.errors)
                self.assertEqual(form.cleaned_data["visibility"], stored)

    def test_visibility_rejects_anything_else(self):
        for value in ("", "PUBLIC", "Public", "privada", "secret", "1"):
            with self.subTest(value=value):
                form = TaskForm(data=self.task_form_data(visibility=value))
                self.assertFalse(form.is_valid())
                self.assertIn("visibility", form.errors)


@fast_passwords
class TaskFormTagsInputCleaningTests(TaskFactoryTestCase):
    """``clean_tags_input`` normalises free text into a list of names."""

    def setUp(self):
        super().setUp()
        self.owner = self.make_user("tags_owner")

    def clean(self, tags_input):
        form = TaskForm(data=self.task_form_data(tags_input=tags_input))
        self.assertTrue(form.is_valid(), form.errors)
        return form.cleaned_data["tags_input"]

    def test_splits_on_commas(self):
        self.assertEqual(self.clean("django,universidad,trabajo"),
                         ["django", "universidad", "trabajo"])

    def test_trims_surrounding_whitespace(self):
        self.assertEqual(self.clean("   django  ,\tuniversidad\n"), ["django", "universidad"])

    def test_ignores_empty_segments(self):
        self.assertEqual(self.clean("django,, ,  ,universidad,"), ["django", "universidad"])

    def test_a_single_tag_without_commas_works(self):
        self.assertEqual(self.clean("django"), ["django"])

    def test_lowercases_every_name(self):
        self.assertEqual(self.clean("Django, UNIVERSIDAD"), ["django", "universidad"])

    def test_deduplicates_case_insensitively_and_keeps_input_order(self):
        self.assertEqual(
            self.clean("Django, django, DJANGO, universidad"),
            ["django", "universidad"],
        )

    def test_whitespace_only_input_yields_an_empty_list(self):
        self.assertEqual(self.clean("   "), [])

    def test_rejects_a_name_longer_than_fifty_characters(self):
        form = TaskForm(data=self.task_form_data(tags_input="a" * 51))

        self.assertFalse(form.is_valid())
        self.assertIn("tags_input", form.errors)

    def test_accepts_a_name_of_exactly_fifty_characters(self):
        name = "a" * 50

        self.assertEqual(self.clean(f"django,{name}"), ["django", name])

    def test_rejects_an_over_long_name_among_valid_ones(self):
        form = TaskForm(data=self.task_form_data(tags_input=f"django,{'b' * 60}"))

        self.assertFalse(form.is_valid())
        self.assertIn("tags_input", form.errors)

    def test_rejected_long_name_creates_no_tag(self):
        form = TaskForm(data=self.task_form_data(tags_input="a" * 51))

        self.assertFalse(form.is_valid())
        self.assertEqual(Tag.objects.count(), 0)


@fast_passwords
class TaskFormTagResolutionTests(TaskFactoryTestCase):
    """``save()`` has to turn names into ``Tag`` rows without duplicates."""

    def setUp(self):
        super().setUp()
        self.owner = self.make_user("resolve_owner")

    def save_with_tags(self, tags_input):
        """Submit a form end-to-end, the way the create view does.

        The owner has to be on the instance *before* ``save()`` runs: the form
        only resolves tags inside the ``commit=True`` branch, which is what
        makes a missing owner a database error rather than a silent no-op.
        """
        form = TaskForm(data=self.task_form_data(tags_input=tags_input))
        self.assertTrue(form.is_valid(), form.errors)
        form.instance.owner = self.owner
        return form.save()

    def test_save_creates_one_tag_row_per_name(self):
        task = self.save_with_tags("django, universidad")

        self.assertEqual(Tag.objects.count(), 2)
        self.assertCountEqual(
            sorted(tag.name for tag in task.tags.all()),
            ["django", "universidad"],
        )

    def test_created_tags_get_a_slug_derived_from_the_name(self):
        self.save_with_tags("Diseño de Interfaces")

        self.assertEqual(Tag.objects.get().slug, "diseno-de-interfaces")

    def test_save_with_no_tags_attaches_nothing(self):
        form = TaskForm(data=self.task_form_data(tags_input=""))
        self.assertTrue(form.is_valid(), form.errors)
        form.instance.owner = self.owner

        task = form.save()

        self.assertEqual(task.tags.count(), 0)
        self.assertEqual(Tag.objects.count(), 0)

    def test_save_reuses_an_existing_tag_whatever_the_casing(self):
        existing = self.make_tag("django")

        task = self.save_with_tags("Django")

        self.assertEqual(Tag.objects.count(), 1)
        self.assertEqual(list(task.tags.all()), [existing])

    def test_save_reuses_a_tag_that_only_differs_by_casing_on_disk(self):
        """The stored row keeps the casing someone else typed first."""
        existing = self.make_tag("Django")

        task = self.save_with_tags("django")

        self.assertEqual(Tag.objects.count(), 1)
        self.assertEqual(list(task.tags.all()), [existing])

    def test_save_does_not_duplicate_a_tag_repeated_in_the_input(self):
        existing = self.make_tag("django")

        task = self.save_with_tags("django, DJANGO, Django")

        self.assertEqual(Tag.objects.count(), 1)
        self.assertEqual(list(task.tags.all()), [existing])

    def test_save_shares_an_existing_tag_across_two_tasks(self):
        existing = self.make_tag("django")
        first = self.save_with_tags("django")
        second = self.save_with_tags("Django")

        self.assertEqual(Tag.objects.count(), 1)
        self.assertEqual(existing.tasks.count(), 2)
        self.assertEqual(list(second.tags.all()), list(first.tags.all()))

    def test_save_does_not_raise_when_a_slug_collides_with_a_different_name(self):
        """Regression: ``python-3`` exists, the user types ``Python 3``.

        Both slugify to ``python-3``. Without the slug fallback in
        ``_resolve_tags`` the INSERT violates the unique constraint and the
        form would blow up as a 500 instead of attaching the existing tag.
        """
        existing = self.make_tag("python-3")

        with self.assertRaises(IntegrityError):
            # The bare model save is the thing that would break; the form must
            # never reach it, which is what the following call proves.
            with transaction.atomic():
                Tag.objects.create(name="python 3", slug="python-3")

        task = self.save_with_tags("Python 3")

        self.assertEqual(Tag.objects.count(), 1)
        self.assertEqual(list(task.tags.all()), [existing])

    def test_two_names_in_one_input_that_share_a_slug_do_not_collide(self):
        task = self.save_with_tags("python 3, python-3")

        self.assertEqual(Tag.objects.count(), 1)
        self.assertEqual(task.tags.count(), 1)

    def test_edit_form_prefills_tags_input_with_the_current_names(self):
        tag = self.make_tag("django")
        task = self.make_task(self.owner, tags=[tag])

        form = TaskForm(instance=task)

        self.assertEqual(form.fields["tags_input"].initial, "django")

    def test_save_replaces_the_previous_tags_on_an_existing_task(self):
        old_tag = self.make_tag("viejo")
        task = self.make_task(self.owner, tags=[old_tag])
        form = TaskForm(data=self.task_form_data(tags_input="nuevo"), instance=task)

        self.assertTrue(form.is_valid(), form.errors)
        form.save()

        task.refresh_from_db()
        self.assertEqual([tag.name for tag in task.tags.all()], ["nuevo"])


@fast_passwords
class RegisterFormTests(TaskFactoryTestCase):
    def data(self, **overrides):
        payload = {
            "username": "estudiante_nuevo",
            "password1": STRONG_PASSWORD,
            "password2": STRONG_PASSWORD,
        }
        payload.update(overrides)
        return payload

    def test_valid_registration_passes_validation(self):
        form = RegisterForm(data=self.data())

        self.assertTrue(form.is_valid(), form.errors)

    def test_valid_registration_creates_a_usable_user(self):
        form = RegisterForm(data=self.data())
        self.assertTrue(form.is_valid(), form.errors)

        user = form.save()

        self.assertTrue(User.objects.filter(username="estudiante_nuevo").exists())
        self.assertTrue(user.check_password(STRONG_PASSWORD))

    def test_short_password_is_rejected(self):
        form = RegisterForm(data=self.data(password1="Ab1!", password2="Ab1!"))

        self.assertFalse(form.is_valid())
        self.assertIn("password2", form.errors)

    def test_mismatched_confirmation_is_rejected(self):
        form = RegisterForm(
            data=self.data(password2="Otra-Clave-Distinta-2026!"),
        )

        self.assertFalse(form.is_valid())
        self.assertIn("password2", form.errors)

    def test_purely_numeric_password_is_rejected(self):
        form = RegisterForm(data=self.data(password1="48291573", password2="48291573"))

        self.assertFalse(form.is_valid())
        self.assertIn("password2", form.errors)

    def test_username_is_required(self):
        form = RegisterForm(data=self.data(username=""))

        self.assertFalse(form.is_valid())
        self.assertIn("username", form.errors)

    def test_rejected_registration_creates_no_user(self):
        before = User.objects.count()
        form = RegisterForm(data=self.data(password2="Otra-Clave-Distinta-2026!"))

        self.assertFalse(form.is_valid())
        self.assertEqual(User.objects.count(), before)

    def test_form_declares_exactly_username_and_the_two_passwords(self):
        self.assertEqual(
            list(RegisterForm().fields),
            ["username", "password1", "password2"],
        )


class TaskFormWidgetTests(TestCase):
    """Regression guard: templates cannot mutate ``widget.attrs``."""

    def test_text_inputs_carry_the_bootstrap_control_class(self):
        form = TaskForm()

        for field in ("title", "description", "due_date", "tags_input"):
            with self.subTest(field=field):
                self.assertIn("form-control", form.fields[field].widget.attrs["class"])

    def test_selects_carry_the_bootstrap_select_class(self):
        form = TaskForm()

        for field in ("priority", "visibility"):
            with self.subTest(field=field):
                widget = form.fields[field].widget
                self.assertIsInstance(widget, forms.Select)
                self.assertIn("form-select", widget.attrs["class"])

    def test_the_checkbox_carries_the_bootstrap_check_class(self):
        form = TaskForm()
        widget = form.fields["completed"].widget

        self.assertIsInstance(widget, forms.CheckboxInput)
        self.assertIn("form-check-input", widget.attrs["class"])

    def test_declared_widget_attrs_are_preserved_next_to_the_class(self):
        form = TaskForm()

        self.assertEqual(form.fields["description"].widget.attrs["rows"], 4)
        self.assertEqual(
            form.fields["tags_input"].widget.attrs["placeholder"],
            "django, universidad",
        )

    def test_due_date_renders_a_native_date_input(self):
        """``type="date"`` lives in ``input_type``, not in ``attrs``.

        Django's ``Input.__init__`` pops ``type`` out of ``attrs`` into
        ``input_type``; asserting ``attrs["type"]`` would be asserting an
        implementation detail that never reached the HTML.
        """
        form = TaskForm()
        widget = form.fields["due_date"].widget

        self.assertEqual(widget.input_type, "date")
        self.assertIn('type="date"', widget.render("due_date", None))
