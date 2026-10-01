"""Test suite for the Task Manager.

This module only holds shared, dependency-free helpers: every test class in
this package builds its fixtures from :class:`TaskFactoryTestCase`, so the
suite needs nothing beyond ``django.test`` and ``manage.py test``.

No pytest, no factory_boy: the assignment's own runner is the only tool.
"""

from __future__ import annotations

from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from tasks.models import Priority, Tag, Task, Visibility

# A password that satisfies every validator configured in settings
# (MinimumLength, CommonPassword, NumericPassword and the similarity check)
# without being memorable, so tests never depend on a weak password.
STRONG_PASSWORD = "Uni-Segura-2024!"


class TaskFactoryTestCase(TestCase):
    """``TestCase`` with a minimal object factory used from ``setUp``.

    The factory is deliberately explicit about every field the tests care
    about, so a change in a model default shows up as a failing assertion
    rather than as a silently different fixture.
    """

    def setUp(self):
        super().setUp()
        self._sequence = 0

    # ------------------------------------------------------------------
    # Factory helpers
    # ------------------------------------------------------------------
    def _next_label(self, prefix):
        self._sequence += 1
        return f"{prefix}-{self._sequence}"

    def make_user(self, username=None, password=STRONG_PASSWORD, **flags):
        """Create an active user with a known password.

        Extra model flags (``is_staff``, ``is_superuser``) are passed through,
        so permission-dependent tests do not have to drop to the ORM.
        """
        User = get_user_model()
        if username is None:
            username = self._next_label("user")
        return User.objects.create_user(
            username=username, password=password, **flags
        )

    def make_tag(self, name, slug=None):
        return Tag.objects.create(name=name, slug=slug)

    def make_task(
        self,
        owner,
        title=None,
        description="Descripción de prueba.",
        due_date=None,
        priority=Priority.MEDIUM,
        completed=False,
        visibility=Visibility.PRIVATE,
        tags=(),
    ):
        if title is None:
            title = self._next_label("Tarea")
        if due_date is None:
            due_date = date.today() + timedelta(days=30)
        task = Task.objects.create(
            owner=owner,
            title=title,
            description=description,
            due_date=due_date,
            priority=priority,
            completed=completed,
            visibility=visibility,
        )
        if tags:
            task.tags.set(tags)
        return task

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------
    def login(self, user):
        self.client.force_login(user)

    def logout(self):
        self.client.logout()

    def detail_url(self, pk):
        return reverse("tasks:task-detail", args=[pk])

    def update_url(self, pk):
        return reverse("tasks:task-update", args=[pk])

    def delete_url(self, pk):
        return reverse("tasks:task-delete", args=[pk])

    def toggle_url(self, pk):
        return reverse("tasks:task-toggle", args=[pk])

    def task_list_url(self):
        return reverse("tasks:task-list")

    def task_create_url(self):
        return reverse("tasks:task-create")

    def public_list_url(self):
        return reverse("tasks:public-task-list")

    def shared_list_url(self):
        return reverse("tasks:shared-task-list")

    def task_form_data(self, **overrides):
        """A complete, valid ``TaskForm`` payload; ``overrides`` win."""
        data = {
            "title": "Tarea válida",
            "description": "Descripción válida.",
            "due_date": "2030-06-15",
            "priority": Priority.MEDIUM,
            "visibility": Visibility.PRIVATE,
            "tags_input": "django, universidad",
        }
        data.update(overrides)
        return data
