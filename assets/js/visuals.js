/** Procedural header illustrations (SVG) for articles — no external images. */
(function () {
  const PALETTES = {
    graph: ["#5eead4", "#a78bfa", "#38bdf8"],
    data: ["#fbbf24", "#5eead4", "#f472b6"],
    rag: ["#34d399", "#818cf8", "#5eead4"],
    eval: ["#fb7185", "#a78bfa", "#5eead4"],
    default: ["#5eead4", "#a78bfa", "#94a3b8"],
  };

  function svgForKind(kind) {
    const colors = PALETTES[kind] || PALETTES.default;
    const [c1, c2, c3] = colors;
    if (kind === "graph") {
      return `<svg viewBox="0 0 640 160" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Graph orchestration diagram">
        <rect width="640" height="160" fill="#121820"/>
        <circle cx="80" cy="80" r="18" fill="${c1}" opacity="0.9"/>
        <circle cx="220" cy="50" r="14" fill="${c2}"/>
        <circle cx="220" cy="110" r="14" fill="${c2}"/>
        <circle cx="380" cy="80" r="16" fill="${c3}"/>
        <circle cx="520" cy="80" r="20" fill="${c1}"/>
        <path d="M98 80 H202 M220 64 V96 M238 80 H364 M396 80 H500" stroke="${c1}" stroke-width="2" fill="none" opacity="0.6"/>
      </svg>`;
    }
    if (kind === "data") {
      return `<svg viewBox="0 0 640 160" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Document store pattern">
        <rect width="640" height="160" fill="#121820"/>
        ${[0, 1, 2, 3].map((i) => `<rect x="${120 + i * 100}" y="40" width="70" height="90" rx="6" fill="none" stroke="${i % 2 ? c2 : c1}" stroke-width="2"/>
        <line x1="${135 + i * 100}" y1="60" x2="${185 + i * 100}" y2="60" stroke="${c3}" stroke-width="2"/>`).join("")}
      </svg>`;
    }
    return `<svg viewBox="0 0 640 160" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Abstract AI motif">
      <rect width="640" height="160" fill="#121820"/>
      <path d="M0 120 Q160 40 320 100 T640 80" fill="none" stroke="${c1}" stroke-width="3" opacity="0.7"/>
      <path d="M0 100 Q200 140 400 60 T640 110" fill="none" stroke="${c2}" stroke-width="2" opacity="0.5"/>
    </svg>`;
  }

  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-visual]").forEach((el) => {
      const kind = el.getAttribute("data-visual") || "default";
      el.classList.add("article-art");
      el.innerHTML = svgForKind(kind);
    });
  });
})();
