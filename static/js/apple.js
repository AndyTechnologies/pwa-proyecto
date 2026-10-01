/*
 * apple.js — the small amount of interaction CSS cannot express.
 *
 * Three jobs, and deliberately no more:
 *
 *   1. Theme: respect the OS preference on first load, and remember a manual
 *      choice in localStorage.
 *   2. Press feedback: acknowledge a press on pointer-*down*, in the same frame,
 *      rather than waiting for click on touch-up.
 *   3. Entry: mark content as entering so CSS can materialize it once.
 *
 * There is no gesture layer here on purpose. Spring physics, momentum
 * projection and velocity handoff earn their keep in drag/swipe/sheet
 * interactions; this app is pointer-and-keyboard, and simulating a flick on a
 * list row would be decoration pretending to be feedback.
 *
 * Everything degrades: with JS off, the page is fully usable and merely static.
 */

(function () {
  "use strict";

  var STORAGE_KEY = "apple-theme";

  function prefersDark() {
    return (
      window.matchMedia &&
      window.matchMedia("(prefers-color-scheme: dark)").matches
    );
  }

  /* ---------------------------------------------------------------------
   * 1. Theme
   * ------------------------------------------------------------------- */

  function applyTheme(theme) {
    document.documentElement.setAttribute("data-bs-theme", theme);
  }

  function storedTheme() {
    try {
      return window.localStorage.getItem(STORAGE_KEY);
    } catch (e) {
      // Private browsing or blocked storage: fall back to the OS preference.
      return null;
    }
  }

  function storeTheme(theme) {
    try {
      window.localStorage.setItem(STORAGE_KEY, theme);
    } catch (e) {
      /* Non-fatal: the theme still applies for this page view. */
    }
  }

  function initTheme() {
    applyTheme(storedTheme() || (prefersDark() ? "dark" : "light"));
  }

  // Follow the OS while the user has not expressed an explicit preference.
  if (window.matchMedia) {
    var scheme = window.matchMedia("(prefers-color-scheme: dark)");
    var onSchemeChange = function (event) {
      if (!storedTheme()) {
        applyTheme(event.matches ? "dark" : "light");
      }
    };
    if (scheme.addEventListener) {
      scheme.addEventListener("change", onSchemeChange);
    } else if (scheme.addListener) {
      scheme.addListener(onSchemeChange);
    }
  }

  /* ---------------------------------------------------------------------
   * 2. Press feedback on pointer-down
   * ------------------------------------------------------------------- */

  /*
   * CSS handles :active already, but :active on a touch device only latches
   * after a delay on some engines. Adding the class on pointerdown makes the
   * acknowledgement immediate and identical across input types.
   */
  function initPressFeedback() {
    var PRESSABLE = "btn, .nav-link, .form-control, .form-select, .badge";

    document.addEventListener(
      "pointerdown",
      function (event) {
        var target = event.target.closest(PRESSABLE);
        if (target) {
          target.classList.add("apple-pressed");
        }
      },
      { passive: true }
    );

    var release = function (event) {
      var target = event.target && event.target.closest
        ? event.target.closest(PRESSABLE)
        : null;
      if (target) {
        target.classList.remove("apple-pressed");
      }
    };

    // pointerup / pointercancel cover mouse, touch and pen through one path.
    document.addEventListener("pointerup", release, { passive: true });
    document.addEventListener("pointercancel", release, { passive: true });

    // Keyboard: Enter/Space on a button also deserves the acknowledgement.
    document.addEventListener("keydown", function (event) {
      if (event.key !== "Enter" && event.key !== " ") return;
      var target = event.target.closest
        ? event.target.closest("button, a.btn, .form-control, .form-select")
        : null;
      if (target) {
        target.classList.add("apple-pressed");
      }
    });

    document.addEventListener("keyup", function (event) {
      if (event.key !== "Enter" && event.key !== " ") return;
      var target = event.target.closest
        ? event.target.closest("button, a.btn, .form-control, .form-select")
        : null;
      if (target) {
        target.classList.remove("apple-pressed");
      }
    });
  }

  /* ---------------------------------------------------------------------
   * 3. Boot
   *
   * The entrance animation is NOT handled here on purpose: the
   * `.apple-enter` wrapper ships in the markup and CSS animates it, which
   * means the entrance works with JavaScript disabled and there is no flash
   * of unstyled content waiting for DOMContentLoaded. Anything this file did
   * to main would also have risked extending the document and raising a
   * scrollbar on a short page.
   * ------------------------------------------------------------------- */

  function boot() {
    initTheme();
    initPressFeedback();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
