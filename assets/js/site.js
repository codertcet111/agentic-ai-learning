/**
 * Shared layout: navigation, mobile menu, active tab, relative path fixes.
 */
(function () {
  const NAV = [
    { id: "home", label: "Home", href: "index.html", root: true },
    {
      id: "agentic",
      label: "Agentic Development",
      href: "agentic-development/index.html",
    },
    {
      id: "graph",
      label: "Graph & Orchestration",
      href: "graph-orchestration/index.html",
    },
    {
      id: "data",
      label: "Mongo for AI",
      href: "data-patterns/index.html",
    },
    { id: "rag", label: "RAG & Knowledge", href: "rag-knowledge/index.html" },
    {
      id: "eval",
      label: "Eval & Observability",
      href: "evaluation/index.html",
    },
    { id: "build", label: "Build Guides", href: "build-guides/index.html" },
    { id: "langfuse", label: "Langfuse Lab", href: "langfuse-lab/index.html" },
    { id: "llm", label: "LLM Engineering", href: "llm-engineering/index.html" },
    { id: "prompts", label: "Prompts & Tools", href: "prompts-tools/index.html" },
    { id: "security", label: "Security for AI", href: "security-ai/index.html" },
    { id: "testing", label: "Testing", href: "testing-ai-dev/index.html" },
  ];

  // Work out the path back to the site root from this script's own src
  // (e.g. "../../assets/js/site.js" -> "../../"). This works no matter what
  // the GitHub repository or folder is called.
  const SCRIPT_SRC = (document.currentScript && document.currentScript.getAttribute("src")) || "";
  const ROOT_PREFIX = SCRIPT_SRC.replace(/assets\/js\/site\.js.*$/, "");

  function prefix() {
    return ROOT_PREFIX;
  }

  function resolveHref(href) {
    return prefix() + href;
  }

  function currentSection() {
    const path = window.location.pathname;
    if (path.includes("agentic-development")) return "agentic";
    if (path.includes("graph-orchestration")) return "graph";
    if (path.includes("data-patterns")) return "data";
    if (path.includes("rag-knowledge")) return "rag";
    if (path.includes("evaluation/")) return "eval";
    if (path.includes("build-guides")) return "build";
    if (path.includes("langfuse-lab")) return "langfuse";
    if (path.includes("llm-engineering")) return "llm";
    if (path.includes("prompts-tools")) return "prompts";
    if (path.includes("security-ai")) return "security";
    if (path.includes("testing-ai-dev")) return "testing";
    return "home";
  }

  function injectHeader() {
    const mount = document.getElementById("site-header");
    if (!mount) return;

    const section = currentSection();
    const navLinks = NAV
      .map((item) => {
        const url = resolveHref(item.href);
        const current =
          item.id === section ? ' aria-current="page"' : "";
        return `<a href="${url}"${current}>${item.label}</a>`;
      })
      .join("");

    mount.innerHTML = `
      <div class="header-inner">
        <a class="logo" href="${resolveHref("index.html")}">
          <span class="logo-mark" aria-hidden="true"></span>
          Agentic Field Notes
        </a>
        <button type="button" class="nav-toggle" aria-expanded="false" aria-controls="primary-nav">
          Menu
        </button>
        <nav id="primary-nav" class="site-nav" aria-label="Primary">${navLinks}</nav>
      </div>`;

    const toggle = mount.querySelector(".nav-toggle");
    const nav = mount.querySelector(".site-nav");
    toggle.addEventListener("click", () => {
      const open = nav.classList.toggle("is-open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
  }

  function injectFooter() {
    const mount = document.getElementById("site-footer");
    if (!mount) return;
    const year = new Date().getFullYear();
    mount.innerHTML = `
      <p>Written by an AI application developer · Static field notes · ${year}</p>
      <p><a href="${resolveHref("sitemap.xml")}">Sitemap</a> · <a href="${resolveHref("robots.txt")}">robots.txt</a></p>`;
  }

  document.addEventListener("DOMContentLoaded", () => {
    injectHeader();
    injectFooter();
  });

  window.AgenticBlog = { prefix, resolveHref };
})();
