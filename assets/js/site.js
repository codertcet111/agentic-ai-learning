/**
 * Menu behaviour for the Topics panel (desktop dropdown, mobile sheet).
 * Header and footer are plain HTML, so the site works without JavaScript
 * apart from opening this panel.
 */
(function () {
  const panel = document.getElementById("topics-panel");
  const toggles = Array.from(document.querySelectorAll("[data-menu-toggle]"));
  if (!panel || !toggles.length) return;

  let lastToggle = null;

  function setOpen(open, source) {
    panel.hidden = !open;
    toggles.forEach((t) => t.setAttribute("aria-expanded", open ? "true" : "false"));
    document.documentElement.classList.toggle("menu-open", open);
    if (open) {
      lastToggle = source || toggles[0];
      const first = panel.querySelector("a");
      if (first && source && source.classList.contains("menu-toggle")) first.focus();
    }
  }

  toggles.forEach((t) =>
    t.addEventListener("click", (e) => {
      e.stopPropagation();
      setOpen(panel.hidden, t);
    })
  );

  document.addEventListener("click", (e) => {
    if (!panel.hidden && !panel.contains(e.target)) setOpen(false);
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !panel.hidden) {
      setOpen(false);
      if (lastToggle) lastToggle.focus();
    }
  });

  // Close after following an in-page link such as "About".
  panel.addEventListener("click", (e) => {
    if (e.target.closest("a")) setOpen(false);
  });
})();
