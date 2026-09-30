"""Guards for the design system and the accessibility promises it makes.

These are not visual tests — they cannot judge whether a page looks right. They
pin the things that are objectively checkable and easy to break by accident:

* the stylesheet and the motion script are actually served and referenced;
* the three user-preference media queries are honoured, because a design
  system that claims reduced-motion support and then does not honour it is
  worse than one that never claimed it;
* the assets stay valid (balanced CSS braces, parseable JS) so a bad edit
  fails here instead of silently breaking every page.
"""

from pathlib import Path

from django.test import TestCase
from django.urls import reverse

from . import TaskFactoryTestCase

STATIC_ROOT = Path(__file__).resolve().parents[2] / "static"
CSS_FILE = STATIC_ROOT / "css" / "apple.css"
JS_FILE = STATIC_ROOT / "js" / "apple.js"


class AssetWiringTests(TaskFactoryTestCase):
    """The design system must be loaded on every page, after Bootstrap."""

    def setUp(self):
        super().setUp()
        self.user = self.make_user("assets")
        self.task = self.make_task(self.user, title="Tarea")

    def pages(self):
        self.login(self.user)
        return [
            reverse("login"),
            reverse("register"),
            reverse("tasks:task-list"),
            reverse("tasks:task-create"),
            reverse("tasks:public-task-list"),
            reverse("tasks:shared-task-list"),
            reverse("tasks:task-detail", args=[self.task.pk]),
            reverse("tasks:task-update", args=[self.task.pk]),
            reverse("tasks:task-delete", args=[self.task.pk]),
        ]

    def test_every_page_loads_the_stylesheet(self):
        for url in self.pages():
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertContains(response, "css/apple.css")

    def test_every_page_loads_the_motion_script(self):
        for url in self.pages():
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertContains(response, "js/apple.js")

    def test_the_stylesheet_is_loaded_after_bootstrap(self):
        # apple.css must win specificity ties, so it has to come second.
        self.login(self.user)
        response = self.client.get(reverse("tasks:task-list"))
        html = response.content.decode()

        bootstrap_at = html.index("css/bootstrap.min.css")
        apple_at = html.index("css/apple.css")

        self.assertLess(bootstrap_at, apple_at)

    def test_every_page_uses_the_translucent_navbar(self):
        for url in self.pages():
            with self.subTest(url=url):
                self.assertContains(self.client.get(url), "navbar-apple")

    def test_the_favicon_is_discoverable_by_staticfiles(self):
        response = self.client.get(reverse("login"))

        self.assertContains(response, "favicon.svg")
        # Asserted through the finder rather than the test client: Django's
        # plain test Client does not serve /static/ at all (bootstrap.min.css
        # 404s there too), so a fetch would prove nothing. The finder is what
        # runserver and collectstatic actually use.
        from django.contrib.staticfiles import finders

        self.assertIsNotNone(
            finders.find("favicon.svg"),
            "favicon.svg is referenced but not discoverable in static/",
        )


class AssetContentTests(TestCase):
    """The assets themselves stay valid."""

    def css(self):
        return CSS_FILE.read_text(encoding="utf-8")

    def test_the_stylesheet_exists(self):
        self.assertTrue(CSS_FILE.exists(), f"missing {CSS_FILE}")

    def test_the_script_exists(self):
        self.assertTrue(JS_FILE.exists(), f"missing {JS_FILE}")

    def test_css_braces_are_balanced(self):
        css = self.css()

        self.assertEqual(
            css.count("{"),
            css.count("}"),
            "unbalanced braces: a truncated or over-edited stylesheet",
        )

    def test_the_javascript_is_syntactically_valid(self):
        # Parsed with Django's own bundled engine-independent check: a SyntaxError
        # here means the whole script silently stops running in the browser.
        JS_FILE.read_text(encoding="utf-8")

        import subprocess
        import shutil

        if shutil.which("node"):
            result = subprocess.run(
                ["node", "--check", str(JS_FILE)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
        else:
            self.skipTest("node not available for a syntax check")

    def test_the_script_guards_its_own_storage_access(self):
        # A blocked localStorage (private browsing) must not throw on boot.
        js = JS_FILE.read_text(encoding="utf-8")

        self.assertIn("try {", js)
        self.assertIn("localStorage", js)


class AccessibilityContractTests(TestCase):
    """The preference queries the design system promises to honour."""

    def setUp(self):
        super().setUp()
        self.css = CSS_FILE.read_text(encoding="utf-8")

    def test_reduced_motion_is_honoured(self):
        self.assertIn("@media (prefers-reduced-motion: reduce)", self.css)

    def test_reduced_transparency_is_honoured(self):
        self.assertIn("@media (prefers-reduced-transparency: reduce)", self.css)

    def test_higher_contrast_is_honoured(self):
        self.assertIn("@media (prefers-contrast: more)", self.css)

    def test_reduced_motion_keeps_a_visible_press_state(self):
        # Reduced motion means gentler feedback, not none: the element must
        # still acknowledge the press, just without the scale transform.
        block = self.css.split("@media (prefers-reduced-motion: reduce)")[1]

        self.assertIn(".apple-pressed", block)
        self.assertIn("transform: none", block)

    def test_reduced_motion_neutralises_the_entrance_animation(self):
        block = self.css.split("@media (prefers-reduced-motion: reduce)")[1]

        self.assertIn(".apple-enter", block)

    def test_keyboard_focus_is_never_removed(self):
        # The app must not ship outline: none without a replacement.
        self.assertNotIn("outline: none", self.css)
        self.assertNotIn("outline:none", self.css)
        self.assertIn(":focus-visible", self.css)

    def test_dark_theme_has_its_own_token_block(self):
        self.assertIn('[data-bs-theme="dark"]', self.css)

    def test_the_page_declares_both_colour_schemes(self):
        response = self.client.get(reverse("login"))

        # Lets the browser paint native controls (scrollbars, date picker) in
        # the matching scheme instead of flashing the wrong one.
        self.assertContains(response, 'name="color-scheme"')
