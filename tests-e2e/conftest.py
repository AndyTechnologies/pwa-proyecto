"""Shared E2E fixtures.

Deliberately minimal: overriding pytest-django's ``django_db_setup`` or
``django_db_blocker`` here would break ``live_server``, which depends on the
real ones. Anything test-specific lives next to its tests in the test module.
"""

import os

# Playwright's sync API keeps an asyncio loop "running" in the main thread for
# its whole session lifetime (it drives the driver through greenlets, so the
# loop created by sync_playwright().start() never goes idle). Django's
# SynchronousOnlyOperation guard reads that as "async context" and blocks the
# test database setup and fixture writes.
#
# This is a false positive, not async code: everything here is synchronous and
# the live server runs in its own thread. Django documents this variable for
# exactly this case. Without it every E2E test errors at setup.
# Negative control: remove this line -> SynchronousOnlyOperation on every test.
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "1")
