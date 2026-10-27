/* barral.pro theme system (see DESIGN.md > Theme system).
   Loaded as a blocking <script src> at the top of <head>, before any CSS, so the right
   theme is on <html> before first paint. External file because the app's CSP forbids inline scripts. */
(function () {
  var KEY = 'barral-theme';
  var root = document.documentElement;

  function stored() {
    try { return localStorage.getItem(KEY); } catch (error) { return null; }
  }
  function current() {
    var saved = stored();
    if (saved === 'dark' || saved === 'light') return saved;
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }
  function apply(theme) {
    root.classList.toggle('dark', theme === 'dark');
    root.classList.toggle('light', theme !== 'dark');
  }

  apply(current());

  // Back-forward cache restores the old DOM: re-apply the saved choice.
  window.addEventListener('pageshow', function (event) { if (event.persisted) apply(current()); });
  // Keep other tabs in sync through the one shared key.
  window.addEventListener('storage', function (event) { if (event.key === KEY) apply(current()); });
  // Follow the system setting only while the user has not chosen a theme.
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function () {
    if (!stored()) apply(current());
  });

  // Delegated, so the handler never depends on icon nodes (icons switch by CSS only).
  document.addEventListener('click', function (event) {
    if (!event.target.closest || !event.target.closest('#theme-toggle')) return;
    var next = root.classList.contains('dark') ? 'light' : 'dark';
    try { localStorage.setItem(KEY, next); } catch (error) { /* storage blocked: theme still applies */ }
    apply(next);
  });
})();
