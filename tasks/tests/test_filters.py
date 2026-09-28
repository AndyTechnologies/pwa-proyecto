"""Query-string filter, sort and tag tests for ``TaskListView``.

The list view accepts three user-controlled parameters: ``status``, ``sort``
and ``tag``. Each one is validated against a whitelist before it reaches the
ORM, which is what makes ``?sort=owner; DROP TABLE tasks--`` a no-op instead
of an injection point. The tests below assert both the happy path and the
fallback.
"""

from django.test import override_settings

from tasks.models import Priority, Tag, Task, Visibility

from . import TaskFactoryTestCase

# Values that must never reach the ORM as a field name or a status literal.
HOSTILE_SORTS = (
    "owner; DROP TABLE tasks--",
    "' or 1=1--",
    '"; DELETE FROM tasks; --',
    "columna_inexistente",
    "title",
    "",
    "due_date; --",
    "-pk",
)


def fast_passwords(cls):
    """Class decorator: hash test passwords with MD5 instead of PBKDF2."""
    return override_settings(
        PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
    )(cls)


@fast_passwords
class StatusFilterTests(TaskFactoryTestCase):
    def setUp(self):
        super().setUp()
        self.user = self.make_user("filtros")
        self.login(self.user)
        self.pending = self.make_task(self.user, title="Pendiente", completed=False)
        self.other_pending = self.make_task(self.user, title="Otra pendiente", completed=False)
        self.completed = self.make_task(self.user, title="Completada", completed=True)
        self.other_completed = self.make_task(self.user, title="Otra completada", completed=True)

    def titles(self, response):
        return [task.title for task in response.context["tasks"]]

    def test_status_pending_returns_only_unfinished_tasks(self):
        response = self.client.get(self.task_list_url(), {"status": "pending"})

        self.assertEqual(response.status_code, 200)
        self.assertCountEqual(self.titles(response), ["Pendiente", "Otra pendiente"])
        self.assertEqual(response.context["status"], "pending")

    def test_status_completed_returns_only_finished_tasks(self):
        response = self.client.get(self.task_list_url(), {"status": "completed"})

        self.assertEqual(response.status_code, 200)
        self.assertCountEqual(self.titles(response), ["Completada", "Otra completada"])
        self.assertEqual(response.context["status"], "completed")

    def test_status_all_returns_every_task(self):
        response = self.client.get(self.task_list_url(), {"status": "all"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(self.titles(response)), 4)
        self.assertEqual(response.context["status"], "all")

    def test_no_status_parameter_defaults_to_all(self):
        response = self.client.get(self.task_list_url())

        self.assertEqual(response.context["status"], "all")
        self.assertEqual(len(self.titles(response)), 4)

    def test_an_invalid_status_falls_back_to_all(self):
        for value in ("banana", "PENDING", "0", "true", "' or 1=1--", "None"):
            with self.subTest(status=value):
                response = self.client.get(self.task_list_url(), {"status": value})

                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context["status"], "all")
                self.assertEqual(len(self.titles(response)), 4)

    def test_the_status_filter_never_leaks_another_users_tasks(self):
        other = self.make_user("intruso")
        self.make_task(other, title="Tarea ajena al filtro", completed=True)

        response = self.client.get(self.task_list_url(), {"status": "completed"})

        self.assertNotContains(response, "Tarea ajena al filtro")
        self.assertEqual(len(self.titles(response)), 2)


@fast_passwords
class SortFilterTests(TaskFactoryTestCase):
    def setUp(self):
        super().setUp()
        self.user = self.make_user("orden_filtros")
        self.login(self.user)

    def titles(self, response):
        return [task.title for task in response.context["tasks"]]

    def test_sort_due_date_orders_by_the_earliest_deadline_first(self):
        far = self.make_task(self.user, title="Lejana", due_date="2031-01-01")
        near = self.make_task(self.user, title="Cercana", due_date="2029-01-01")
        middle = self.make_task(self.user, title="Media", due_date="2030-01-01")

        response = self.client.get(self.task_list_url(), {"sort": "due_date"})

        self.assertEqual(self.titles(response), [near.title, middle.title, far.title])
        self.assertEqual(response.context["sort"], "due_date")

    def test_sort_priority_orders_low_before_high_regardless_of_due_date(self):
        high = self.make_task(
            self.user, title="Alta", due_date="2029-01-01", priority=Priority.HIGH
        )
        low = self.make_task(
            self.user, title="Baja", due_date="2031-01-01", priority=Priority.LOW
        )
        medium = self.make_task(
            self.user, title="Media", due_date="2030-01-01", priority=Priority.MEDIUM
        )

        response = self.client.get(self.task_list_url(), {"sort": "priority"})

        self.assertEqual(self.titles(response), [low.title, medium.title, high.title])
        self.assertEqual(response.context["sort"], "priority")

    def test_no_sort_parameter_defaults_to_due_date(self):
        far = self.make_task(self.user, title="Lejana", due_date="2031-01-01")
        near = self.make_task(self.user, title="Cercana", due_date="2029-01-01")

        response = self.client.get(self.task_list_url())

        self.assertEqual(response.context["sort"], "due_date")
        self.assertEqual(self.titles(response), [near.title, far.title])

    def test_the_allowed_sorts_map_is_exposed_to_the_template(self):
        response = self.client.get(self.task_list_url())

        self.assertEqual(
            sorted(response.context["allowed_sorts"]),
            ["due_date", "priority"],
        )

    def test_an_invalid_sort_falls_back_to_due_date_without_raising(self):
        far = self.make_task(self.user, title="Lejana", due_date="2031-01-01")
        near = self.make_task(self.user, title="Cercana", due_date="2029-01-01")

        for value in HOSTILE_SORTS:
            with self.subTest(sort=value):
                response = self.client.get(self.task_list_url(), {"sort": value})

                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context["sort"], "due_date")
                self.assertEqual(self.titles(response), [near.title, far.title])

    def test_an_injection_attempt_in_the_sort_parameter_does_not_drop_the_table(self):
        before = Task.objects.count()

        response = self.client.get(
            self.task_list_url(),
            {"sort": "owner; DROP TABLE tasks--"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Task.objects.count(), before)
        self.assertEqual(list(Task.objects.values_list("title", flat=True)),
                         [task.title for task in Task.objects.all()])

    def test_an_unknown_sort_column_does_not_reach_the_orm(self):
        """A column that does not exist would raise ``FieldError`` if trusted."""
        self.make_task(self.user, title="Única")

        response = self.client.get(self.task_list_url(), {"sort": "columna_inexistente"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["sort"], "due_date")
        self.assertEqual(self.titles(response), ["Única"])

    def test_the_sort_filter_never_leaks_another_users_tasks(self):
        other = self.make_user("intruso_orden")
        self.make_task(other, title="Ajena al orden", due_date="2020-01-01")

        response = self.client.get(self.task_list_url(), {"sort": "due_date"})

        self.assertNotContains(response, "Ajena al orden")


@fast_passwords
class SortTieBreakerTests(TaskFactoryTestCase):
    def setUp(self):
        super().setUp()
        self.user = self.make_user("empates")
        self.login(self.user)
        self.due = "2030-04-04"

    def titles(self, response):
        return [task.title for task in response.context["tasks"]]

    def test_two_tasks_with_the_same_due_date_and_priority_use_descending_pk(self):
        first = self.make_task(self.user, title="Primera", due_date=self.due)
        second = self.make_task(self.user, title="Segunda", due_date=self.due)

        self.assertLess(first.pk, second.pk)
        response = self.client.get(self.task_list_url(), {"sort": "due_date"})

        self.assertEqual(self.titles(response), ["Segunda", "Primera"])

    def test_the_tie_breaker_holds_for_the_priority_sort_too(self):
        first = self.make_task(
            self.user, title="Primera", due_date=self.due, priority=Priority.HIGH
        )
        second = self.make_task(
            self.user, title="Segunda", due_date=self.due, priority=Priority.HIGH
        )

        self.assertLess(first.pk, second.pk)
        response = self.client.get(self.task_list_url(), {"sort": "priority"})

        self.assertEqual(self.titles(response), ["Segunda", "Primera"])

    def test_repeated_requests_return_the_same_order(self):
        for index in range(4):
            self.make_task(self.user, title=f"Empate-{index}", due_date=self.due)

        orders = [
            self.titles(self.client.get(self.task_list_url(), {"sort": "due_date"}))
            for _ in range(3)
        ]

        self.assertEqual(orders[0], orders[1])
        self.assertEqual(orders[1], orders[2])

    def test_priority_breaks_ties_before_the_pk_tie_breaker(self):
        high = self.make_task(self.user, title="Alta", due_date=self.due, priority=Priority.HIGH)
        low = self.make_task(self.user, title="Baja", due_date=self.due, priority=Priority.LOW)

        response = self.client.get(self.task_list_url(), {"sort": "due_date"})

        self.assertEqual(self.titles(response), [low.title, high.title])


@fast_passwords
class TagFilterTests(TaskFactoryTestCase):
    def setUp(self):
        super().setUp()
        self.user = self.make_user("etiquetas")
        self.login(self.user)
        self.django_tag = self.make_tag("django")
        self.exam_tag = self.make_tag("examen")
        self.python_tag = self.make_tag("python")
        self.tagged = self.make_task(self.user, title="Con django", tags=[self.django_tag])
        self.tagged_both = self.make_task(
            self.user, title="Con django y examen", tags=[self.django_tag, self.exam_tag]
        )
        self.tagged_other = self.make_task(
            self.user, title="Con python", tags=[self.python_tag]
        )
        self.untagged = self.make_task(self.user, title="Sin etiquetas")

    def titles(self, response):
        return [task.title for task in response.context["tasks"]]

    def test_tag_filter_returns_only_the_tasks_carrying_that_slug(self):
        response = self.client.get(self.task_list_url(), {"tag": self.django_tag.slug})

        self.assertEqual(response.status_code, 200)
        self.assertCountEqual(
            self.titles(response), ["Con django", "Con django y examen"]
        )
        self.assertEqual(response.context["tag"], "django")

    def test_a_task_with_several_matching_tags_is_returned_once(self):
        response = self.client.get(self.task_list_url(), {"tag": self.django_tag.slug})

        titles = self.titles(response)
        self.assertEqual(len(titles), len(set(titles)))

    def test_the_tag_filter_accepts_a_name_as_well_as_a_slug(self):
        response = self.client.get(self.task_list_url(), {"tag": "python"})

        self.assertEqual(self.titles(response), ["Con python"])

    def test_the_tag_filter_is_case_insensitive(self):
        response = self.client.get(self.task_list_url(), {"tag": "Django"})

        self.assertCountEqual(
            self.titles(response), ["Con django", "Con django y examen"]
        )

    def test_an_unknown_tag_returns_an_empty_result_without_raising(self):
        for value in ("inexistente", "django-2", "no-existe-nada"):
            with self.subTest(tag=value):
                response = self.client.get(self.task_list_url(), {"tag": value})

                self.assertEqual(response.status_code, 200)
                self.assertEqual(self.titles(response), [])

    def test_an_empty_tag_parameter_is_treated_as_no_filter(self):
        response = self.client.get(self.task_list_url(), {"tag": ""})

        self.assertEqual(len(self.titles(response)), 4)
        self.assertEqual(response.context["tag"], "")

    def test_the_tag_filter_never_leaks_another_users_tasks(self):
        other = self.make_user("intruso_etiquetas")
        foreign_tag = self.make_tag("secreto")
        self.make_task(other, title="Ajuda etiquetada", tags=[foreign_tag])

        response = self.client.get(self.task_list_url(), {"tag": "secreto"})

        self.assertEqual(self.titles(response), [])

    def test_the_context_lists_every_tag_used_by_the_viewer(self):
        response = self.client.get(self.task_list_url())

        self.assertCountEqual(
            [tag.slug for tag in response.context["all_tags"]],
            ["django", "examen", "python"],
        )

    def test_the_context_excludes_tags_used_only_by_other_users(self):
        other = self.make_user("intruso_contexto")
        self.make_tag("solo-ajeno")
        self.make_task(other, title="Ajena", tags=[Tag.objects.get(slug="solo-ajeno")])

        response = self.client.get(self.task_list_url())

        self.assertNotIn("solo-ajeno", [tag.slug for tag in response.context["all_tags"]])


@fast_passwords
class CombinedFilterTests(TaskFactoryTestCase):
    def setUp(self):
        super().setUp()
        self.user = self.make_user("combinado")
        self.login(self.user)
        self.django_tag = self.make_tag("django")
        self.python_tag = self.make_tag("python")

        self.target = self.make_task(
            self.user,
            title="Objetivo",
            due_date="2030-01-01",
            priority=Priority.HIGH,
            completed=False,
            tags=[self.django_tag],
        )
        self.wrong_status = self.make_task(
            self.user,
            title="Ya completada",
            due_date="2030-01-01",
            priority=Priority.LOW,
            completed=True,
            tags=[self.django_tag],
        )
        self.wrong_tag = self.make_task(
            self.user,
            title="Otra etiqueta",
            due_date="2030-01-01",
            priority=Priority.LOW,
            completed=False,
            tags=[self.python_tag],
        )
        self.wrong_priority = self.make_task(
            self.user,
            title="Otra prioridad",
            due_date="2030-01-01",
            priority=Priority.LOW,
            completed=False,
            tags=[self.django_tag],
        )

    def titles(self, response):
        return [task.title for task in response.context["tasks"]]

    def test_status_sort_and_tag_apply_together(self):
        response = self.client.get(
            self.task_list_url(),
            {"status": "pending", "sort": "priority", "tag": "django"},
        )

        self.assertEqual(response.status_code, 200)
        # "Objetivo" (HIGH) and "Otra prioridad" (LOW) both carry the django
        # tag and are both pending, so both match. Priority is a *sort*, not a
        # filter, so LOW is expected first.
        self.assertEqual(self.titles(response), ["Otra prioridad", "Objetivo"])
        self.assertNotIn("Ya completada", self.titles(response))
        self.assertNotIn("Otra etiqueta", self.titles(response))
        self.assertEqual(response.context["status"], "pending")
        self.assertEqual(response.context["sort"], "priority")
        self.assertEqual(response.context["tag"], "django")

    def test_the_combination_keeps_the_requested_ordering(self):
        self.make_task(
            self.user,
            title="Baja pendiente",
            due_date="2030-01-01",
            priority=Priority.LOW,
            completed=False,
            tags=[self.django_tag],
        )

        response = self.client.get(
            self.task_list_url(),
            {"status": "pending", "sort": "priority", "tag": "django"},
        )

        # Three matches, all with the same due_date, so ordering is decided
        # purely by priority. The two LOW tasks tie and are separated by the
        # deterministic ``-pk`` tie-breaker.
        self.assertEqual(
            self.titles(response),
            ["Baja pendiente", "Otra prioridad", "Objetivo"],
        )

    def test_status_completed_with_the_tag_filter(self):
        response = self.client.get(
            self.task_list_url(),
            {"status": "completed", "tag": "django"},
        )

        self.assertEqual(self.titles(response), ["Ya completada"])

    def test_a_combination_with_no_matches_returns_an_empty_list(self):
        response = self.client.get(
            self.task_list_url(),
            {"status": "completed", "tag": "python"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.titles(response), [])

    def test_one_invalid_parameter_falls_back_without_breaking_the_others(self):
        response = self.client.get(
            self.task_list_url(),
            {"status": "no-existe", "sort": "no-existe", "tag": "django"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["status"], "all")
        self.assertEqual(response.context["sort"], "due_date")
        # The two invalid parameters fall back, but the *valid* tag parameter
        # keeps applying: "Otra etiqueta" carries the python tag and must stay
        # out even though the status filter degraded to "all".
        self.assertCountEqual(
            self.titles(response),
            ["Objetivo", "Ya completada", "Otra prioridad"],
        )
        self.assertNotIn("Otra etiqueta", self.titles(response))

    def test_the_combination_never_leaks_another_users_tasks(self):
        other = self.make_user("intruso_combinado")
        self.make_task(
            other, title="Ajena combinada", completed=True, tags=[self.django_tag]
        )

        response = self.client.get(
            self.task_list_url(),
            {"status": "completed", "tag": "django"},
        )

        self.assertEqual(self.titles(response), ["Ya completada"])

    def test_a_filtered_list_keeps_its_visibility_scope(self):
        """A PRIVATE task is still only ever visible to its own owner."""
        self.make_task(self.user, title="Privada filtrable", visibility=Visibility.PRIVATE)
        self.make_task(
            self.user, title="Pública filtrable", visibility=Visibility.PUBLIC
        )

        response = self.client.get(
            self.task_list_url(),
            {"status": "all", "sort": "due_date", "tag": ""},
        )

        self.assertContains(response, "Privada filtrable")
        self.assertContains(response, "Pública filtrable")
