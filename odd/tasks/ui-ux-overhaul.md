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

## Evidence — work-unit commits

Branch: `feat/ui-ux-overhaul` (branched from `master` at 7e52648)

| Commit | Task | Outcome |
| --- | --- | --- |
| `ade544c` | 1 — comment leak | Multi-line `{# #}` → `{% comment %}`. Guard suite added; 3 guards fail on the reintroduced leak. 266 tests. |
| `7ab8cbd` | 2 — form styling | `BootstrapWidgetMixin` + `LoginForm`; `is-invalid` on failing fields. 278 tests. |
| `a4683cc` | 3+4 — design system | `static/css/apple.css` (16 KB) + `static/js/apple.js`, committed together because the JS toggles a CSS class. |
| `ae0b95b` | 5 — restyle | All 11 templates. Reverted a copy change that broke a pinned read-only contract. |
| `561eba5` | 6 — verification | 18 design-system guards; `font-optical-sizing` added after the rationale claimed it but the CSS never set it. 296 tests. |

### Defects found and fixed

1. **Multi-line `{# #}` printed on `/tasks/`** — Django lexes `{# #}` as a comment
   only within a single line.
2. **Login and register inputs unstyled** — widget-classing lived in `TaskForm`
   only; no `form-control`, and English labels on a Spanish app.
3. **Field errors invisible** — Bootstrap hides `.invalid-feedback` without
   `is-invalid` on the control.

### Method notes

Every fix was validated with a **negative control**: the guard was shown to fail
when the defect was reintroduced. Green tests alone do not demonstrate detection
— the pre-existing suite had 249 passing tests while the app served 404s, because
`assertIn(reverse("login"), url)` accepts `/login/` as a substring of the broken
`/accounts/login/?next=/tasks/`. URL assertions here use exact equality.

Two guards failed on first run for test-side reasons (missing login; Django's
test client does not serve `/static/`), both corrected rather than papered over.

