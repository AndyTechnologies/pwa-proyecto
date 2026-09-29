# Feature: UI/UX overhaul + comment-leak fix

**Feature doc:** `odd/tasks/ui-ux-overhaul.md`
**Engram mirror:** `odd/ui-ux-overhaul/tasks`
**Branch:** `feat/ui-ux-overhaul`
**Design reference:** the `apple-design` skill (WWDC *Designing Fluid Interfaces*, *The Details of UI Typography*) applied over vendored Bootstrap 5.

## Goal

Fix the visible defect on `/tasks/` and bring the whole interface up to an
Apple-style bar: instant press feedback, spring easing, translucent materials,
size-specific typography, and honest reduced-motion support — without adding a
single Python dependency and without touching the authorization model.

## Non-goals

- No gesture layer (no drag, no swipe, no momentum projection). The skill is
  written for touch surfaces; this app is pointer-and-keyboard on the web, and
  a synthesized drag would be decoration, not feedback.
- No Spring/Motion/Framer library. The interaction set here is press feedback
  and enter transitions, both of which CSS expresses faithfully with the
  critically-damped curve the skill specifies.
- No change to views, models, URLs, permissions or the test contract beyond
  what the new guard tests require.
- No dark-mode rewrite of every component. Bootstrap 5.3 already ships
  `data-bs-theme`; we use it rather than rebuilding it.

## Root cause of the reported defect

Django's `{# ... #}` comment is **single-line only**. A `{# #}` pair spanning
two lines is not lexed as a comment at all — Django emits it as literal text.
`templates/tasks/task_list.html:22` had exactly that, so the comment printed
on the page.

Confirmed empirically before fixing:

```
single-line -> '[]OK'
multi-line  -> '[{# line one\nline two #}]OK'
```

The fix is `{% comment %}...{% endcomment %}`, which does span lines. A
repository-wide guard test now asserts no rendered page contains a literal
`{#` or `{%`, so this class of defect cannot return silently.

## Second defect found during review

`AuthenticationForm` and `RegisterForm` widgets never received Bootstrap
classes — the widget-classing loop lives in `TaskForm.__init__` only. Login and
register therefore rendered unstyled native inputs. Centralized in
`tasks/forms.py`.

## Tasks

1. Fix the leaked comment; add the template guard test.
2. Fix missing Bootstrap classes on login/register widgets.
3. Add `static/css/apple.css` design system.
4. Wire CSS + `static/js/apple.js` into `base.html`.
5. Restyle all 11 templates onto the system.
6. Verify: full suite, no comment leaks, reduced-motion, no regressions.

## Design decisions

- **Critically damped by default.** The skill's house style is damping 1.0 for
  UI that was not thrown by a flick. Every transition here uses it; nothing
  overshoots.
- **Response 0.3–0.4 s**, matching the skill's table for move/panel work.
- **Translucency only on the navbar.** The skill warns that stacking a light
  translucent surface on another collapses legibility. The navbar is the only
  floating chrome, so it is the only blurred surface.
- **Typography tracking is size-specific** — `-0.02em` on headings, `0` on
  body. A single fixed `letter-spacing` is wrong somewhere, per the skill.
- **System font stack first**, per the skill: it already ships optical sizing
  and legibility tuning.
- **Every animation gated on `prefers-reduced-motion`**, plus separate
  `prefers-reduced-transparency` and `prefers-contrast` handling.

## Acceptance

- `GET /tasks/` renders no `{#` or `{%` in the HTML.
- No template anywhere emits literal template syntax.
- Login/register inputs carry `form-control` / `form-select`.
- Full suite green.
