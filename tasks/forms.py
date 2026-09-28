"""Forms for the Task Manager.

The login form is deliberately **not** reimplemented here: Django's
``AuthenticationForm`` (used by ``LoginView``) already validates credentials
correctly. Reimplementing it would be abstracting Django away purely for
appearance, which the assignment explicitly discourages (see ADR-004).
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.utils.text import slugify

from .models import Tag, Task


class RegisterForm(UserCreationForm):
    """Registration form: username + password + password confirmation.

    Inherits Django's password validators and strength checks.
    """

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username",)


class TaskForm(forms.ModelForm):
    """Create/update form for a task.

    Tags are edited as a single free-text field of comma-separated names rather
    than as a multi-select, because the assignment expects an end user to both
    reuse existing labels and invent new ones in the same gesture (RF-10).
    Resolution to ``Tag`` instances happens in :meth:`save`, because a
    ``ModelForm`` cannot persist a ManyToMany from a plain ``CharField``.
    """

    tags_input = forms.CharField(
        required=False,
        label="Etiquetas",
        help_text="Separá por comas. Ejemplo: django, universidad, trabajo",
        widget=forms.TextInput(attrs={"placeholder": "django, universidad"}),
    )

    class Meta:
        model = Task
        fields = ("title", "description", "due_date", "priority", "visibility", "completed")
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "due_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Pre-fill the free-text tag field when editing an existing task.
        if self.instance.pk:
            self.fields["tags_input"].initial = ", ".join(
                self.instance.tags.values_list("name", flat=True)
            )
        # Labels are part of the domain vocabulary, not free-form JSON; set them
        # explicitly so the UI reads in Spanish.
        self.fields["priority"].label = "Prioridad"
        self.fields["visibility"].label = "Visibilidad"
        # Bootstrap classes must be applied here: Django exposes no way to set
        # widget attributes from a template, and django-widget-tweaks is
        # deliberately not a dependency (RNF-12).
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.Select):
                css = "form-select"
            elif isinstance(widget, forms.CheckboxInput):
                css = "form-check-input"
            else:
                css = "form-control"
            existing = widget.attrs.get("class")
            if existing:
                css = f"{existing} {css}"
            widget.attrs["class"] = css

    def clean_tags_input(self):
        """Reject names that cannot become a valid ``Tag``."""
        names = self.cleaned_data.get("tags_input", "")
        cleaned = []
        for raw in names.split(","):
            name = raw.strip()
            if not name:
                continue
            if len(name) > Tag._meta.get_field("name").max_length:
                raise forms.ValidationError(
                    f"La etiqueta «{name}» supera los 50 caracteres."
                )
            if name.lower() in cleaned:
                continue
            cleaned.append(name.lower())
        return cleaned

    def _resolve_tags(self, names):
        """Return ``Tag`` instances for ``names``, reusing existing ones.

        Reuse is case-insensitive: typing ``Django`` when ``django`` already
        exists attaches the existing tag instead of creating a near-duplicate.

        Lookup also covers the slug, because two different names can slugify to
        the same value (``"Python 3"`` and ``"python-3"`` both become
        ``python-3``). Without that second lookup, the unique constraint on
        ``Tag.slug`` would raise ``IntegrityError`` and turn the form into a 500.
        """
        tags = []
        for name in names:
            slug = slugify(name)[:50]
            tag = Tag.objects.matching(name).first() or Tag.objects.filter(slug=slug).first()
            if tag is None:
                tag = Tag.objects.create(name=name, slug=slug)
            tags.append(tag)
        return tags

    def save(self, commit=True):
        task = super().save(commit=commit)
        if commit:
            task.tags.set(self._resolve_tags(self.cleaned_data["tags_input"]))
        return task
