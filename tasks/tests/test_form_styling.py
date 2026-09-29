"""Defect 10: login and register inputs rendered with no Bootstrap classes.

The widget-classing loop lived inside ``TaskForm.__init__`` only, so the two
other forms in the project were unaffected:

* login used Django's ``AuthenticationForm`` (via ``LoginView``), whose widgets
  render as bare ``<input>`` with no ``form-control``;
* register used ``UserCreationForm``, with the same gap.

Both pages therefore looked unstyled next to the rest of the app. Login also
showed English labels ("Username", "Password") on a Spanish-language interface.

The fix extracts :class:`tasks.forms.BootstrapWidgetMixin` and applies it to
every form, and adds :class:`tasks.forms.LoginForm` so ``LoginView`` renders
styled, Spanish-labelled inputs.

The second half matters just as much: Bootstrap hides ``.invalid-feedback``
unless the control itself carries ``.is-invalid``, so a field error rendered as
grey text with no red state and no visible message. The mixin adds
``is-invalid`` only to fields that actually have errors.
"""

from django import forms
from django.test import TestCase

from tasks.forms import BootstrapWidgetMixin, LoginForm, RegisterForm, TaskForm


def widget_classes(form, name):
    return form.fields[name].widget.attrs.get("class", "")


class BootstrapClassesTests(TestCase):
    def test_login_inputs_carry_form_control(self):
        form = LoginForm()

        self.assertIn("form-control", widget_classes(form, "username"))
        self.assertIn("form-control", widget_classes(form, "password"))

    def test_register_inputs_carry_form_control(self):
        form = RegisterForm()

        self.assertIn("form-control", widget_classes(form, "username"))
        self.assertIn("form-control", widget_classes(form, "password1"))
        self.assertIn("form-control", widget_classes(form, "password2"))

    def test_task_form_selects_carry_form_select(self):
        form = TaskForm()

        self.assertIn("form-select", widget_classes(form, "priority"))
        self.assertIn("form-select", widget_classes(form, "visibility"))

    def test_task_form_checkbox_carries_form_check_input(self):
        form = TaskForm()

        self.assertIn("form-check-input", widget_classes(form, "completed"))

    def test_task_form_text_inputs_carry_form_control(self):
        form = TaskForm()

        self.assertIn("form-control", widget_classes(form, "title"))
        self.assertIn("form-control", widget_classes(form, "description"))
        self.assertIn("form-control", widget_classes(form, "tags_input"))


class InvalidStateTests(TestCase):
    """Bootstrap hides `.invalid-feedback` without `.is-invalid` on the control."""

    def test_a_field_with_errors_is_marked_invalid(self):
        form = LoginForm(data={"username": "alguien", "password": ""})

        self.assertFalse(form.is_valid())
        self.assertIn("is-invalid", widget_classes(form, "password"))

    def test_a_valid_field_is_not_marked_invalid(self):
        form = TaskForm(
            data={
                "title": "Una tarea",
                "description": "Con descripción",
                "due_date": "2030-01-01",
                "priority": 1,
                "visibility": "private",
            },
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertNotIn("is-invalid", widget_classes(form, "title"))

    def test_only_the_failing_field_is_marked_invalid(self):
        form = TaskForm(data={"title": "Una tarea", "description": "d", "due_date": ""})

        form.is_valid()

        self.assertIn("is-invalid", widget_classes(form, "due_date"))
        self.assertNotIn("is-invalid", widget_classes(form, "title"))


class LoginLabelTests(TestCase):
    """LoginView used Django's English labels on a Spanish-language app."""

    def test_labels_are_in_spanish(self):
        form = LoginForm()

        self.assertEqual(str(form.fields["username"].label), "Usuario")
        self.assertEqual(str(form.fields["password"].label), "Contraseña")

    def test_password_field_keeps_the_right_autocomplete_token(self):
        # "new-password" here would break browser password managers and
        # silently autofill the login form with a registration password.
        form = LoginForm()

        self.assertEqual(
            form.fields["password"].widget.attrs["autocomplete"],
            "current-password",
        )
        self.assertEqual(
            form.fields["username"].widget.attrs["autocomplete"],
            "username",
        )


class WidgetMixinContractTests(TestCase):
    """The mixin must not clobber classes it did not add."""

    def test_existing_classes_are_preserved(self):
        class Dummy(BootstrapWidgetMixin, forms.Form):
            name = forms.CharField(
                widget=forms.TextInput(attrs={"class": "mi-clase", "data-x": "1"})
            )

            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.apply_bootstrap_classes()

        classes = widget_classes(Dummy(), "name")

        self.assertIn("mi-clase", classes)
        self.assertIn("form-control", classes)
        self.assertEqual(Dummy().fields["name"].widget.attrs["data-x"], "1")

    def test_applying_twice_does_not_duplicate_classes(self):
        class Dummy(BootstrapWidgetMixin, forms.Form):
            name = forms.CharField()

            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.apply_bootstrap_classes()
                self.apply_bootstrap_classes()

        self.assertEqual(
            widget_classes(Dummy(), "name").split().count("form-control"),
            1,
        )
