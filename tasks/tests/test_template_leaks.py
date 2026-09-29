"""Defect 9: a multi-line ``{# ... #}`` comment was printed on ``/tasks/``.

Django lexes ``{# ... #}`` as a comment **only when it stays on one line**. A
pair split across two lines is not recognised as a comment at all, so Django
emits it verbatim and the user reads the source on the page. That is exactly
what happened with the filter comment in ``tasks/task_list.html``.

The long-term fix is the repository-wide guard below: any rendered page that
contains a literal ``{#`` or ``{%`` is a template whose comments are broken,
so we assert the absence of both markers on every page in the app.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from . import STRONG_PASSWORD, TaskFactoryTestCase

# Literal template syntax. A rendered page must never contain either one:
# "{#" would be a multi-line {# #} comment that Django failed to lex, and "{%"
# would be a tag whose {% comment %} block is unbalanced.
LEAKED_TEMPLATE_SYNTAX = ["{#", "{%"]


def assert_no_template_leaks(case, response, page):
    """Fail with a readable message if a page leaked template syntax."""
    html = response.content.decode()
    for marker in LEAKED_TEMPLATE_SYNTAX:
        case.assertNotIn(
            marker,
            html,
            f"{page} renders a literal {marker!r}. A multi-line {{# ... #}} "
            f"comment is not lexed as a comment by Django; use "
            f"{{% comment %}}...{{% endcomment %}} for multi-line comments.",
        )


class TemplateLeakTests(TaskFactoryTestCase):
    """Every page in the app must render without leaking template syntax."""

    def setUp(self):
        super().setUp()
        self.user = self.make_user("fuga")
        self.task = self.make_task(self.user, title="Tarea visible")

    def test_the_owner_task_list_does_not_leak_comments(self):
        self.login(self.user)

        response = self.client.get(reverse("tasks:task-list"))

        assert_no_template_leaks(self, response, "/tasks/")

    def test_the_filtered_task_list_does_not_leak_comments(self):
        # The filters branch renders the same comment block as the plain list.
        self.login(self.user)

        response = self.client.get(f"{reverse('tasks:task-list')}?status=pending&sort=priority")

        assert_no_template_leaks(self, response, "/tasks/?status=pending")

    def test_the_empty_task_list_does_not_leak_comments(self):
        user = self.make_user("fuga-vacia")
        self.login(user)

        response = self.client.get(reverse("tasks:task-list"))

        assert_no_template_leaks(self, response, "/tasks/ (vacía)")

    def test_the_other_pages_do_not_leak_comments(self):
        self.login(self.user)

        pages = [
            (reverse("tasks:task-detail", args=[self.task.pk]), "/tasks/<id>/"),
            (reverse("tasks:task-update", args=[self.task.pk]), "/tasks/<id>/edit/"),
            (reverse("tasks:task-delete", args=[self.task.pk]), "/tasks/<id>/delete/"),
            (reverse("tasks:task-create"), "/tasks/create/"),
            (reverse("tasks:public-task-list"), "/tasks/public/"),
            (reverse("tasks:shared-task-list"), "/tasks/shared/"),
        ]

        for url, page in pages:
            with self.subTest(page=page):
                assert_no_template_leaks(self, self.client.get(url), page)

    def test_the_anonymous_pages_do_not_leak_comments(self):
        pages = [
            (reverse("login"), "/login/"),
            (reverse("register"), "/register/"),
            (reverse("tasks:public-task-list"), "/tasks/public/ (anónimo)"),
        ]

        for url, page in pages:
            with self.subTest(page=page):
                assert_no_template_leaks(self, self.client.get(url), page)

    def test_an_invalid_login_does_not_leak_comments(self):
        # Error rendering is a separate code path in the template; cover it.
        response = self.client.post(
            reverse("login"),
            {"username": "no-existe", "password": "equivocada"},
        )

        assert_no_template_leaks(self, response, "/login/ (con errores)")


class MultiLineCommentSyntaxTests(TestCase):
    """Document *why* the guard above exists, by pinning Django's behaviour.

    If a future Django release ever accepts multi-line ``{# #}``, these two
    tests fail and the conversion to ``{% comment %}`` can be revisited. Until
    then they are the executable proof of the root cause.
    """

    def test_a_single_line_brace_comment_is_consumed(self):
        from django.template import Context, Template

        rendered = Template("[{# one line #}]OK").render(Context({}))

        self.assertEqual(rendered, "[]OK")

    def test_a_multi_line_brace_comment_is_emitted_verbatim(self):
        from django.template import Context, Template

        rendered = Template("[{# line one\nline two #}]OK").render(Context({}))

        # This is the defect: the comment survives into the output.
        self.assertIn("{#", rendered)

    def test_a_multi_line_comment_block_is_consumed(self):
        from django.template import Context, Template

        rendered = Template(
            "[{% comment %}\nline one\nline two\n{% endcomment %}]OK"
        ).render(Context({}))

        self.assertEqual(rendered, "[]OK")
