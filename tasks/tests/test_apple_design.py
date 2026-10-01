"""Guards for the Apple system palette, the type scale, and the scroll contract.

The first pass of this design system was "Bootstrap plus a blur filter". These
tests exist so it cannot quietly return to that: they pin the Apple system
colours, the non-monotonic tracking scale, and the structural rules that keep a
short page from growing a scrollbar.
"""

import re
from pathlib import Path

from django.test import TestCase

STATIC_ROOT = Path(__file__).resolve().parents[2] / "static"
CSS_FILE = STATIC_ROOT / "css" / "apple.css"


def css():
    return CSS_FILE.read_text(encoding="utf-8")


COMMENT = re.compile(r"/\*.*?\*/", re.S)


def rules(source):
    """Yield (selector_list, body) for every brace-free rule in the sheet.

    Comments are stripped first: otherwise a block comment sitting above a
    rule gets captured as part of that rule's selector and no selector ever
    matches. A rule inside a media query is yielded too, which is what these
    tests want: they assert about declarations, not about nesting.
    """
    source = COMMENT.sub("", source)
    for match in re.finditer(r"([^{}]+)\{([^{}]+)\}", source):
        selector = match.group(1).strip()
        if not selector or selector.startswith("@"):
            continue
        yield selector, match.group(2)


def rule(source, selector, must_contain=None):
    """Return the body of the rule whose selector list includes ``selector``.

    The stylesheet declares `body` more than once (shell and typography) and
    many selectors are comma-separated lists, so a naive
    `split("body {")[1]` silently returns the wrong block. Matching on the
    selector list, and optionally requiring a marker declaration, keeps a test
    from passing or failing against the wrong rule.
    """
    for selectors, body in rules(source):
        parts = [s.strip() for s in selectors.split(",")]
        if selector not in parts:
            continue
        if must_contain is None or must_contain in body:
            return body
    return ""


class ApplePaletteTests(TestCase):
    """Bootstrap's own tokens are replaced, not worked around per component."""

    def setUp(self):
        self.css = css()

    def test_light_mode_system_colors(self):
        for color in [
            "#007aff",  # systemBlue
            "#34c759",  # systemGreen
            "#ff9500",  # systemOrange
            "#ff3b30",  # systemRed
            "#af52de",  # systemPurple
        ]:
            with self.subTest(color=color):
                self.assertIn(color, self.css)

    def test_dark_mode_uses_the_high_chroma_variants(self):
        dark = self.css.split('[data-bs-theme="dark"]')[1]
        for color in ["#0a84ff", "#30d158", "#ff9f0a", "#ff453a", "#bf5af2"]:
            with self.subTest(color=color):
                self.assertIn(color, dark)

    def test_grouped_background_is_apple_grouped_grey(self):
        self.assertIn("#f2f2f7", self.css)
        self.assertIn("#000000", self.css)

    def test_labels_use_apple_semitransparent_greys(self):
        # Apple's secondary label is a 60% black, not a flat grey.
        self.assertIn("rgb(60 60 67 / 0.6)", self.css)
        self.assertIn("rgb(60 60 67 / 0.3)", self.css)

    def test_bootstrap_tokens_are_overridden(self):
        # Overriding --bs-* is what makes every component Apple without
        # rewriting a single template.
        for token in [
            "--bs-body-bg",
            "--bs-body-color",
            "--bs-secondary-color",
            "--bs-link-color",
            "--bs-border-color",
            "--bs-primary",
            "--bs-danger",
            "--bs-success",
        ]:
            with self.subTest(token=token):
                self.assertIn(f"{token}:", self.css)

    def test_both_themes_declare_colour_scheme(self):
        self.assertIn("color-scheme: light", self.css)
        self.assertIn("color-scheme: dark", self.css)


class TypographyScaleTests(TestCase):
    """Apple's tracking is not monotonic, and that is the point."""

    def setUp(self):
        self.css = css()

    def test_the_type_system_uses_apple_faces(self):
        self.assertIn("SF Pro Text", self.css)
        self.assertIn("SF Pro Display", self.css)

    def test_system_font_comes_first(self):
        body = rule(self.css, "body", must_contain="font-family")
        self.assertIn("-apple-system", body)
        self.assertLess(
            body.index("-apple-system"),
            body.index("SF Pro Text"),
        )

    def test_large_title_tracking_is_positive(self):
        # Apple's 34pt Large Title tracks POSITIVE. A generic "tighten your
        # headings" rule would get this backwards.
        block = rule(self.css, ".apple-page-title")
        tracking = re.search(r"letter-spacing:\s*(-?[\d.]+)em", block)

        self.assertIsNotNone(tracking, "no letter-spacing on the page title")
        self.assertGreater(
            float(tracking.group(1)),
            0,
            "the largest type should track positive, as at 34pt",
        )

    def test_body_tracking_is_negative(self):
        body = rule(self.css, "body", must_contain="font-family")
        tracking = re.search(r"letter-spacing:\s*(-?[\d.]+)em", body)

        self.assertIsNotNone(tracking)
        self.assertLess(float(tracking.group(1)), 0)

    def test_small_caps_tracking_is_positive_again(self):
        # 11pt tracks +0.066: the scale turns back up at the small end.
        block = rule(self.css, ".text-uppercase")
        tracking = re.search(r"letter-spacing:\s*(-?[\d.]+)em", block)

        self.assertIsNotNone(tracking, block)
        self.assertGreater(float(tracking.group(1)), 0)

    def test_the_scale_is_actually_non_monotonic(self):
        """Guard against collapsing back to a single tracking value."""
        values = [
            float(v)
            for v in re.findall(r"letter-spacing:\s*(-?[\d.]+)em", self.css)
        ]
        signs = {v > 0 for v in values if v != 0}

        self.assertIn(
            True,
            signs,
            "expected at least one positive tracking value",
        )
        self.assertIn(
            False,
            signs,
            "expected at least one negative tracking value; if every size "
            "tracks the same way the Apple scale has been flattened",
        )

    def test_optical_sizing_is_enabled(self):
        self.assertIn("font-optical-sizing: auto", self.css)

    def test_text_size_adjust_is_set(self):
        # Respects the user's Dynamic Type setting instead of overriding it.
        self.assertIn("text-size-adjust: 100%", self.css)


class ScrollContractTests(TestCase):
    """A short page must not grow a scrollbar."""

    def setUp(self):
        self.css = css()

    def test_dynamic_viewport_units_are_used(self):
        # 100vh ignores the collapsing mobile toolbar, which both leaves a
        # gap and can force a scrollbar that is not needed.
        self.assertIn("100dvh", self.css)

    def test_vh_is_kept_as_a_fallback(self):
        self.assertRegex(
            self.css,
            r"min-height:\s*100vh;\s*\n\s*min-height:\s*100dvh;",
            "expected 100vh as a declared fallback before 100dvh",
        )

    def test_main_grows_without_being_compressed(self):
        # flex: 1 0 auto absorbs slack (footer to the bottom) while keeping a
        # tall page tall instead of squashing it to fit.
        main = rule(self.css, "main")
        self.assertIn("flex: 1 0 auto", main)

    def test_horizontal_overflow_is_clipped(self):
        # `clip` rather than `hidden`: it prevents a horizontal scrollbar
        # without creating a scroll container.
        self.assertIn("overflow-x: clip", self.css)
        self.assertNotIn("overflow-x: hidden", self.css)

    def test_entrance_does_not_animate_the_outermost_element(self):
        """A translateY on <main> would extend the document and add a scrollbar."""
        main = rule(self.css, "main")
        self.assertNotIn("animation", main)

    def test_entrance_lives_on_the_inner_wrapper(self):
        self.assertIn(".apple-enter {", self.css)
        # And the wrapper is an inner element, not main itself.
        self.assertIn("animation: apple-materialize", self.css)

    def test_the_shell_is_not_fighting_bootstrap_utilities(self):
        """Bootstrap's layout utilities would silently undo the dvh fix.

        ``min-vh-100`` compiles to ``min-height:100vh!important`` and
        ``flex-grow-1`` to ``flex-grow:1!important``. Applied to <body>/<main>
        they outrank apple.css and reintroduce exactly the 100vh behaviour this
        section exists to avoid.
        """
        base = (Path(__file__).resolve().parents[2] / "templates" / "base.html")
        html = base.read_text(encoding="utf-8")

        body = re.search(r"<body([^>]*)>", html).group(1)
        self.assertNotIn("min-vh-100", body)
        self.assertNotIn("d-flex", body, "apple.css owns the body shell")

        main = re.search(r"<main([^>]*)>", html).group(1)
        self.assertNotIn("flex-grow-1", main)

    def test_the_utility_conflict_is_real(self):
        """Pin the Bootstrap behaviour the previous test guards against."""
        bootstrap = (STATIC_ROOT / "css" / "bootstrap.min.css").read_text(
            encoding="utf-8"
        )

        self.assertIn("min-vh-100{min-height:100vh!important", bootstrap)
        self.assertIn("flex-grow-1{flex-grow:1!important", bootstrap)


class MotionPhysicsTests(TestCase):
    """Critically damped by default: nothing here overshoots."""

    def setUp(self):
        self.css = css()

    def test_motion_tokens_are_defined(self):
        self.assertIn("--apple-ease", self.css)
        self.assertIn("--apple-response", self.css)
        self.assertIn("--apple-response-fast", self.css)

    def test_no_overshoot_curves_are_used(self):
        # A back/elastic easing would bounce, which the skill reserves for
        # gesture-driven momentum. No gesture layer exists here.
        for curve in ["back-in", "elastic", "bounce", "back-out"]:
            with self.subTest(curve=curve):
                self.assertNotIn(curve, self.css)

    def test_press_feedback_is_instant(self):
        # 180ms press vs 320ms for movement: the acknowledgement is faster
        # than the rest of the motion vocabulary.
        fast = re.search(r"--apple-response-fast:\s*(\d+)ms", self.css)
        base = re.search(r"--apple-response:\s*(\d+)ms", self.css)

        self.assertIsNotNone(fast)
        self.assertIsNotNone(base)
        self.assertLess(int(fast.group(1)), int(base.group(1)))
