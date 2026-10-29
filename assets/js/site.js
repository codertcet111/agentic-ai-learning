/**
 * Agentic Field Notes: Topics menu and reading progress.
 *
 * Progress is kept in one cookie in this browser ("afn_progress"), as a list of
 * short article ids. Nothing is sent to a server; GitHub Pages ignores the cookie.
 */
(function () {
  document.documentElement.classList.add("js");

  /* ---------------- Topics menu ---------------- */

  const panel = document.getElementById("topics-panel");
  const toggles = Array.from(document.querySelectorAll("[data-menu-toggle]"));
  let lastToggle = null;

  function setMenu(open, source) {
    if (!panel) return;
    panel.hidden = !open;
    toggles.forEach((t) => t.setAttribute("aria-expanded", open ? "true" : "false"));
    document.documentElement.classList.toggle("menu-open", open);
    if (open) {
      lastToggle = source || toggles[0];
      const first = panel.querySelector("a");
      if (first && source && source.classList.contains("menu-toggle")) first.focus();
    }
  }

  if (panel && toggles.length) {
    toggles.forEach((t) =>
      t.addEventListener("click", (e) => {
        e.stopPropagation();
        setMenu(panel.hidden, t);
      })
    );
    document.addEventListener("click", (e) => {
      if (!panel.hidden && !panel.contains(e.target)) setMenu(false);
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && !panel.hidden) {
        setMenu(false);
        if (lastToggle) lastToggle.focus();
      }
    });
    panel.addEventListener("click", (e) => {
      if (e.target.closest("a")) setMenu(false);
    });
  }

  /* ---------------- Reading progress (cookie) ---------------- */

  const COOKIE = "afn_progress";
  const MAX_AGE = 60 * 60 * 24 * 365 * 2; // two years

  // Site root path, worked out from this script's own src ("../../assets/js/site.js").
  const script = document.currentScript;
  const rootPrefix = script ? script.getAttribute("src").replace(/assets\/js\/site\.js.*$/, "") : "";
  const rootPath = new URL(rootPrefix || "./", window.location.href).pathname;

  function readDone() {
    const match = document.cookie.split("; ").find((c) => c.startsWith(COOKIE + "="));
    if (!match) return new Set();
    const value = decodeURIComponent(match.slice(COOKIE.length + 1));
    return new Set(value.split(".").filter((id) => /^[a-z0-9]{4}$/.test(id)));
  }

  function writeDone(done) {
    const value = Array.from(done).sort().join(".");
    const secure = window.location.protocol === "https:" ? "; Secure" : "";
    if (value) {
      document.cookie = `${COOKIE}=${value}; Max-Age=${MAX_AGE}; Path=${rootPath}; SameSite=Lax${secure}`;
    } else {
      document.cookie = `${COOKIE}=; Max-Age=0; Path=${rootPath}; SameSite=Lax${secure}`;
    }
  }

  function render() {
    const done = readDone();

    document.querySelectorAll("input[data-progress-id]").forEach((box) => {
      const checked = done.has(box.dataset.progressId);
      box.checked = checked;
      const row = box.closest("[data-progress-row]");
      if (row) row.classList.toggle("is-done", checked);
    });

    document.querySelectorAll("[data-progress-ids]").forEach((el) => {
      const ids = el.dataset.progressIds.split(" ").filter(Boolean);
      const count = ids.filter((id) => done.has(id)).length;
      const total = ids.length;
      const pct = total ? Math.round((count / total) * 100) : 0;

      const fill = el.querySelector(".progress-fill");
      if (fill) fill.style.width = pct + "%";
      const bar = el.querySelector("[role='progressbar']");
      if (bar) {
        bar.setAttribute("aria-valuenow", String(count));
        bar.setAttribute("aria-valuemax", String(total));
        bar.setAttribute("aria-valuetext", `${count} of ${total} complete`);
      }
      const text = el.querySelector("[data-progress-text]");
      if (text) {
        if (count === 0 && el.dataset.emptyText) text.textContent = el.dataset.emptyText;
        else if (count === total && total > 0) text.textContent = `All ${total} complete`;
        else text.textContent = `${count} of ${total} complete`;
      }
      el.classList.toggle("has-progress", count > 0);
      el.classList.toggle("is-complete", total > 0 && count === total);
    });

    document.querySelectorAll("[data-progress-reset]").forEach((btn) => {
      btn.hidden = done.size === 0;
    });
  }

  document.addEventListener("change", (e) => {
    const box = e.target;
    if (!(box instanceof HTMLInputElement) || !box.dataset.progressId) return;
    const done = readDone();
    if (box.checked) done.add(box.dataset.progressId);
    else done.delete(box.dataset.progressId);
    writeDone(done);
    render();
  });

  document.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-progress-reset]");
    if (!btn) return;
    if (window.confirm("Clear your reading progress in this browser?")) {
      writeDone(new Set());
      render();
    }
  });

  // Another tab may have changed progress; refresh when this one becomes visible,
  // and when the page is restored from the back/forward cache.
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") render();
  });
  window.addEventListener("pageshow", render);

  render();
})();

/**
 * Career timeline: lay the bars out against the current month, so the
 * timeline always runs from July 2017 to the month the page is opened.
 */
(function () {
  const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  const toIndex = (ym) => {
    const [y, m] = ym.split("-").map(Number);
    return y * 12 + (m - 1);
  };
  const label = (i) => `${MONTHS[i % 12]} ${Math.floor(i / 12)}`;
  const duration = (months) => {
    const y = Math.floor(months / 12);
    const m = months % 12;
    return [y ? `${y} yr${y > 1 ? "s" : ""}` : "", m ? `${m} mo${m > 1 ? "s" : ""}` : ""].filter(Boolean).join(" ") || "1 mo";
  };

  document.querySelectorAll(".journey").forEach((root) => {
    const today = new Date();
    const nowIndex = today.getFullYear() * 12 + today.getMonth();
    const start = toIndex(root.dataset.start);
    const end = nowIndex + 1;
    const span = Math.max(1, end - start);
    const pct = (i) => ((i - start) / span) * 100;

    root.querySelectorAll(".j-bar").forEach((bar) => {
      const a = toIndex(bar.dataset.from);
      const b = bar.dataset.to === "now" ? end : toIndex(bar.dataset.to) + 1;
      bar.style.left = pct(a) + "%";
      bar.style.width = pct(b) - pct(a) + "%";
      const name = bar.closest(".j-row").querySelector(".j-label").firstChild.textContent.trim();
      const to = bar.dataset.to === "now" ? "now" : label(b - 1);
      bar.title = `${name}: ${label(a)} to ${to} (${duration(b - a)})`;
    });

    const track = root.querySelector(".j-axis-track");
    if (track) {
      track.querySelectorAll(".j-tick").forEach((t) => t.remove());
      const nowEl = track.querySelector("[data-j-now]");
      for (let y = Math.floor(start / 12) + 1; y <= today.getFullYear(); y++) {
        if (pct(y * 12) >= 90) continue; // leave room for the "now" label
        const t = document.createElement("span");
        t.className = "j-tick";
        t.style.left = pct(y * 12) + "%";
        t.textContent = String(y);
        track.insertBefore(t, nowEl);
      }
      if (nowEl) nowEl.textContent = label(nowIndex);
    }
  });
})();
