"""Regression guard for the reported scrollbar bug.

Symptom (user-reported): a vertical scrollbar appeared once the window was
wider than ~990px, and never below that, for the same page and same content.

Cause: ``<main>`` carried ``py-4 py-lg-5``. At Bootstrap's lg breakpoint
(992px) the vertical padding jumps from 24px to 48px per side, the document
grows past 100dvh, and content that fit below the breakpoint stops fitting
above it. Reproduced with exactly 5 tasks: no scrollbar at 991px, scrollbar
at 993px.

The contract: whether the page scrolls must depend on the *content*, never on
the window width. The first test pins the cause (padding must not change at
the breakpoint); the second pins the original phase-2 guarantee (an empty list
never scrolls, at any width).
"""

import pytest


def scroll_metrics(page):
    return page.evaluate(
        """() => {
            const d = document.documentElement;
            return {
                v: d.scrollHeight > d.clientHeight,
                h: d.scrollWidth > d.clientWidth,
            };
        }"""
    )


@pytest.mark.django_db
class TestScrollContract:

    def test_main_vertical_padding_is_width_independent(
        self, page, server_url, regular_user, login
    ):
        login(regular_user.username)

        paddings = {}
        for width in (991, 993):
            page.set_viewport_size({"width": width, "height": 720})
            page.goto(f"{server_url}/tasks/")
            page.wait_for_load_state("networkidle")
            paddings[width] = page.evaluate(
                "getComputedStyle(document.querySelector('main')).paddingTop"
            )

        assert paddings[991] == paddings[993], (
            f"main's vertical padding changes at the lg breakpoint: {paddings}. "
            "The same content then fits at 991px and overflows at 993px, "
            "which is exactly the reported scrollbar bug (py-lg-5)."
        )

    def test_empty_list_has_no_scroll_at_any_width(
        self, page, server_url, regular_user, login
    ):
        # regular_user was just created: no tasks, so nothing may scroll.
        login(regular_user.username)

        for width in (800, 991, 993, 1280):
            page.set_viewport_size({"width": width, "height": 720})
            page.goto(f"{server_url}/tasks/")
            page.wait_for_load_state("networkidle")
            m = scroll_metrics(page)

            assert not m["v"], (
                f"vertical scrollbar on an empty list at {width}px"
            )
            assert not m["h"], (
                f"horizontal scrollbar on an empty list at {width}px"
            )
