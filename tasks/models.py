"""Domain models for the Task Manager.

The two authorization policies required by the assignment live in
:class:`TaskQuerySet` rather than in the views or templates, so that every entry
point filters through the same code (see ADR-008).
"""

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils.text import slugify


class Priority(models.IntegerChoices):
    """Task priority.

    Stored as an integer so that database-level ordering matches the semantic
    order (LOW < MEDIUM < HIGH) with a plain ``ORDER BY priority`` and without
    any extra mapping table. The labels are translated for display.
    """

    LOW = 1, "Baja"
    MEDIUM = 2, "Media"
    HIGH = 3, "Alta"


class Visibility(models.TextChoices):
    """Who may read a task.

    Visibility never grants write access: only the owner may mutate a task
    (ADR-005, Regla 6).
    """

    PRIVATE = "private", "Privada"
    AUTHENTICATED = "authenticated", "Compartida con registradas"
    PUBLIC = "public", "Pública"


class TagQuerySet(models.QuerySet):
    def matching(self, name):
        """Return tags whose name matches ``name`` case-insensitively.

        Lets the UI reuse an existing tag regardless of the casing the user
        typed, while keeping ``Tag.name`` unique at the database level.
        """
        return self.filter(name__iexact=name.strip())


class Tag(models.Model):
    """A free-form label that can be attached to many tasks."""

    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = TagQuerySet.as_manager()

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Keep the slug in sync with the name so callers never have to think
        # about it. Unique on both fields, so the slug only needs to be derived
        # once per save.
        if not self.slug:
            self.slug = slugify(self.name)[:50]
        super().save(*args, **kwargs)


class TaskQuerySet(models.QuerySet):
    """Query policies for :class:`Task`.

    Keeping them here means a view cannot accidentally implement its own idea
    of who may see what: it either asks for ``owned_by`` or for ``visible_to``.
    """

    def owned_by(self, user):
        """Write policy: only tasks owned by ``user``.

        Used by every mutable view. An unauthorized task is therefore never
        fetched, so it 404s instead of leaking its existence (IDOR defence,
        ADR-008).
        """
        return self.filter(owner=user)

    def visible_to(self, user):
        """Read policy: every task ``user`` is allowed to open.

        Anonymous visitors only see PUBLIC tasks. Authenticated non-owners see
        AUTHENTICATED and PUBLIC tasks. Owners see all of their own tasks
        regardless of visibility.
        """
        if not user.is_authenticated:
            return self.filter(visibility=Visibility.PUBLIC)

        return self.filter(
            Q(owner=user)
            | Q(visibility__in=[Visibility.AUTHENTICATED, Visibility.PUBLIC])
        )


class Task(models.Model):
    """A personal or professional task owned by exactly one user."""

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tasks",
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    due_date = models.DateField()
    priority = models.IntegerField(choices=Priority.choices, default=Priority.MEDIUM)
    completed = models.BooleanField(default=False)
    visibility = models.CharField(
        max_length=20,
        choices=Visibility.choices,
        default=Visibility.PRIVATE,
    )
    tags = models.ManyToManyField(Tag, related_name="tasks", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TaskQuerySet.as_manager()

    class Meta:
        # Deterministic default ordering: the tie-breaker on ``-pk`` prevents
        # unstable pagination when two tasks share due_date and priority.
        ordering = ["due_date", "priority", "-pk"]
        indexes = [
            models.Index(fields=["owner", "due_date"]),
            models.Index(fields=["visibility"]),
        ]

    def __str__(self):
        return self.title

    def is_editable_by(self, user):
        """Whether ``user`` may mutate this task. Presentation hint only.

        Views must still enforce ownership server-side through
        ``Task.objects.owned_by``; this property exists so templates can hide
        actions the viewer is not allowed to perform (RF-37).
        """
        return bool(user.is_authenticated and user.pk == self.owner_id)
