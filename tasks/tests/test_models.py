"""Model-level tests: defaults, ordering, relations and cascade behaviour."""

from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.db import IntegrityError, transaction
from django.test import TestCase

from tasks.models import Priority, Tag, Task, Visibility

from . import TaskFactoryTestCase


class TaskModelCreationTests(TaskFactoryTestCase):
    def setUp(self):
        super().setUp()
        self.owner = self.make_user("ana")

    def test_task_is_created_with_the_expected_values(self):
        task = Task.objects.create(
            owner=self.owner,
            title="Entregar trabajo",
            description="Subir el PDF al aula virtual.",
            due_date=date(2030, 5, 20),
        )

        self.assertEqual(task.owner, self.owner)
        self.assertEqual(task.title, "Entregar trabajo")
        self.assertEqual(task.description, "Subir el PDF al aula virtual.")
        self.assertEqual(task.due_date, date(2030, 5, 20))

    def test_priority_defaults_to_medium(self):
        task = self.make_task(self.owner)

        self.assertEqual(task.priority, Priority.MEDIUM)
        self.assertEqual(task.get_priority_display(), "Media")

    def test_visibility_defaults_to_private(self):
        task = self.make_task(self.owner)

        self.assertEqual(task.visibility, Visibility.PRIVATE)
        self.assertEqual(task.get_visibility_display(), "Privada")

    def test_completed_defaults_to_false(self):
        task = self.make_task(self.owner)

        self.assertIs(task.completed, False)

    def test_tags_are_optional_and_empty_by_default(self):
        task = self.make_task(self.owner)

        self.assertEqual(task.tags.count(), 0)

    def test_created_at_and_updated_at_are_automatic(self):
        task = self.make_task(self.owner)

        self.assertIsNotNone(task.created_at)
        self.assertIsNotNone(task.updated_at)
        # They are populated independently: ``auto_now_add`` and ``auto_now``
        # each stamp their own value during the same INSERT, so they are equal
        # to the microsecond only by accident and must not be asserted equal.
        self.assertLessEqual(task.created_at, task.updated_at)

    def test_updated_at_changes_on_every_save(self):
        task = self.make_task(self.owner)
        created_at = task.created_at

        task.description = "Descripción revisada."
        task.save()
        task.refresh_from_db()

        self.assertGreater(task.updated_at, created_at)
        self.assertEqual(task.created_at, created_at)

    def test_str_of_task_returns_its_title(self):
        task = self.make_task(self.owner, title="Revisar apuntes")

        self.assertEqual(str(task), "Revisar apuntes")

    def test_str_of_tag_returns_its_name(self):
        tag = self.make_tag("django")

        self.assertEqual(str(tag), "django")


class PriorityChoicesTests(TestCase):
    def test_priority_numeric_values(self):
        self.assertEqual(Priority.LOW, 1)
        self.assertEqual(Priority.MEDIUM, 2)
        self.assertEqual(Priority.HIGH, 3)

    def test_priority_semantic_order_is_low_medium_high(self):
        self.assertLess(Priority.LOW, Priority.MEDIUM)
        self.assertLess(Priority.MEDIUM, Priority.HIGH)

    def test_priority_database_order_matches_semantic_order(self):
        """A plain ``ORDER BY priority`` must already read LOW -> HIGH."""
        owner = get_user_model().objects.create_user(username="orden", password="x")
        due = date(2030, 1, 1)
        for value in (Priority.HIGH, Priority.LOW, Priority.MEDIUM):
            Task.objects.create(
                owner=owner,
                title=f"p{value}",
                description="d",
                due_date=due,
                priority=value,
            )

        ordered = list(Task.objects.order_by("priority").values_list("priority", flat=True))

        self.assertEqual(ordered, [Priority.LOW, Priority.MEDIUM, Priority.HIGH])

    def test_visibility_literal_values(self):
        self.assertEqual(Visibility.PRIVATE, "private")
        self.assertEqual(Visibility.AUTHENTICATED, "authenticated")
        self.assertEqual(Visibility.PUBLIC, "public")


class TaskMetaOrderingTests(TaskFactoryTestCase):
    def setUp(self):
        super().setUp()
        self.owner = self.make_user("orden_owner")

    def test_meta_ordering_is_due_date_then_priority_then_descending_pk(self):
        self.assertEqual(Task._meta.ordering, ["due_date", "priority", "-pk"])

    def test_default_queryset_is_ordered_by_due_date(self):
        far = self.make_task(self.owner, title="Lejana", due_date=date(2030, 12, 31))
        near = self.make_task(self.owner, title="Cercana", due_date=date(2030, 1, 1))
        middle = self.make_task(self.owner, title="Media", due_date=date(2030, 6, 15))

        self.assertEqual(list(Task.objects.all()), [near, middle, far])

    def test_default_queryset_breaks_ties_with_priority(self):
        due = date(2030, 3, 3)
        high = self.make_task(self.owner, title="Alta", due_date=due, priority=Priority.HIGH)
        low = self.make_task(self.owner, title="Baja", due_date=due, priority=Priority.LOW)
        medium = self.make_task(self.owner, title="Media", due_date=due, priority=Priority.MEDIUM)

        self.assertEqual(list(Task.objects.all()), [low, medium, high])

    def test_default_queryset_breaks_ties_with_descending_pk(self):
        due = date(2030, 3, 3)
        first = self.make_task(self.owner, title="Primera", due_date=due)
        second = self.make_task(self.owner, title="Segunda", due_date=due)

        self.assertEqual(list(Task.objects.all()), [second, first])


class TagModelTests(TaskFactoryTestCase):
    def setUp(self):
        super().setUp()
        self.owner = self.make_user("tag_owner")

    def test_slug_is_derived_from_the_name(self):
        tag = self.make_tag("Django Rest Framework")

        self.assertEqual(tag.slug, "django-rest-framework")

    def test_slug_is_derived_from_accents_and_symbols(self):
        tag = self.make_tag("Diseño de Interfaces")

        self.assertEqual(tag.slug, "diseno-de-interfaces")

    def test_created_at_is_automatic(self):
        tag = self.make_tag("django")

        self.assertIsNotNone(tag.created_at)

    def test_tag_name_is_unique_case_sensitively_at_the_database_level(self):
        self.make_tag("django")

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Tag.objects.create(name="django", slug="django-2")

    def test_matching_is_case_insensitive(self):
        tag = self.make_tag("Django")

        self.assertEqual(list(Tag.objects.matching("django")), [tag])
        self.assertEqual(list(Tag.objects.matching("DJANGO")), [tag])
        self.assertEqual(list(Tag.objects.matching("django ")), [tag])

    def test_matching_returns_nothing_for_an_unknown_name(self):
        self.assertEqual(list(Tag.objects.matching("rails")), [])


class TaskTagRelationTests(TaskFactoryTestCase):
    def setUp(self):
        super().setUp()
        self.owner = self.make_user("relation_owner")
        self.tag = self.make_tag("django")

    def test_tags_are_reachable_from_the_task(self):
        task = self.make_task(self.owner, tags=[self.tag])

        self.assertEqual(list(task.tags.all()), [self.tag])

    def test_tasks_are_reachable_from_the_tag(self):
        task = self.make_task(self.owner, tags=[self.tag])

        self.assertEqual(list(self.tag.tasks.all()), [task])

    def test_one_tag_can_be_shared_by_several_tasks(self):
        first = self.make_task(self.owner, title="Primera", tags=[self.tag])
        second = self.make_task(self.owner, title="Segunda", tags=[self.tag])

        self.assertEqual(self.tag.tasks.count(), 2)
        self.assertCountEqual(list(self.tag.tasks.all()), [first, second])
        self.assertEqual(list(second.tags.all()), [self.tag])

    def test_a_task_can_carry_several_tags(self):
        second = self.make_tag("universidad")
        task = self.make_task(self.owner, tags=[self.tag, second])

        self.assertCountEqual(list(task.tags.all()), [self.tag, second])

    def test_deleting_the_owner_cascades_to_its_tasks(self):
        task = self.make_task(self.owner)

        self.owner.delete()

        self.assertFalse(Task.objects.filter(pk=task.pk).exists())

    def test_deleting_a_task_leaves_orphan_tags_intact(self):
        self.make_task(self.owner, tags=[self.tag])
        task = self.make_task(self.owner)

        task.delete()

        self.assertTrue(Tag.objects.filter(pk=self.tag.pk).exists())


class IsEditableByTests(TaskFactoryTestCase):
    def setUp(self):
        super().setUp()
        self.owner = self.make_user("duena")
        self.stranger = self.make_user("extraña")
        self.task = self.make_task(self.owner)

    def test_owner_may_edit_the_task(self):
        self.assertIs(self.task.is_editable_by(self.owner), True)

    def test_authenticated_non_owner_may_not_edit(self):
        self.assertIs(self.task.is_editable_by(self.stranger), False)

    def test_anonymous_may_not_edit(self):
        self.assertIs(self.task.is_editable_by(AnonymousUser()), False)

    def test_is_editable_by_is_a_method_not_a_property(self):
        """Regression guard: it used to be a ``@property`` with an argument.

        A property would make ``task.is_editable_by`` a bool here and blow up
        with ``TypeError`` the moment the view called it with the request user.
        """
        self.assertFalse(callable(getattr(type(self.task), "is_editable_by", None)) is False)
        self.assertTrue(callable(self.task.is_editable_by))
