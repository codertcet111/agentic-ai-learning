# Agentic Field Notes (static blog)

A self-contained, **HTML + CSS + JS** blog about agentic AI development. No build step is required to read it; optional generator refreshes article HTML from `scripts/generate_pages.py`.

## Structure

```text
static-blog/
├── index.html                 # Home (animated hero)
├── robots.txt / sitemap.xml   # SEO / crawlers
├── llms.txt                   # Hints for LLM crawlers
├── assets/css/site.css
├── assets/js/site.js          # Nav, footer, mobile menu
├── assets/js/hero-canvas.js   # Home animation
├── assets/js/visuals.js       # SVG header art (no image CDN)
├── agentic-development/       # Tab 2 — 20 step pages under steps/
├── graph-orchestration/
├── data-patterns/
├── rag-knowledge/
├── evaluation/
├── build-guides/
├── langfuse-lab/              # Langfuse screenshots + dev walkthroughs
├── llm-engineering/
├── prompts-tools/
├── security-ai/
├── testing-ai-dev/
├── assets/images/langfuse/    # Langfuse screenshots
└── scripts/
    ├── generate_pages.py
    ├── content_extension.py   # Extra sections & Langfuse copy
    └── articles/              # Full article bodies, one file per post
```

## Local preview

From this folder (the one containing `index.html`):

```bash
python3 -m http.server 8080
```

Open `http://localhost:8080/`. On Windows you can use `py -m http.server 8080`.

## Publish free on GitHub Pages

1. Create a new **public** repository on GitHub, for example `static-blog`.
2. Upload the **contents of this folder** so that `index.html` sits at the top level of the repository (not inside another folder). Either drag the files into GitHub's "Add file → Upload files" page, or use git:

   ```bash
   git init
   git add .
   git commit -m "Publish blog"
   git branch -M main
   git remote add origin https://github.com/codertcet111/agentic-ai-learning.git
   git push -u origin main
   ```

3. In the repository go to **Settings → Pages**. Under **Build and deployment**, set **Source** to **Deploy from a branch**, choose branch **main** and folder **/ (root)**, then **Save**.
4. After a minute or two the site is live at `https://codertcet111.github.io/agentic-ai-learning/`. The Pages settings screen shows the exact URL.

The empty `.nojekyll` file tells GitHub to serve the files as they are.

### Set your real URL (for SEO)

Canonical links, `sitemap.xml` and `robots.txt` contain the site's full URL. Regenerate them once you know it:

```bash
SITE_URL=https://codertcet111.github.io/agentic-ai-learning python3 scripts/generate_pages.py
```

On Windows PowerShell:

```powershell
$env:SITE_URL="https://codertcet111.github.io/agentic-ai-learning"; py scripts/generate_pages.py
```

Then commit and push again.

## Writing and editing articles

Each article body lives in its own file:

```text
scripts/articles/<section>/<slug>.html
```

The first line is a comment with the page's meta description:

```html
<!-- desc: One sentence describing the article for search results. -->
<p>Article body…</p>
```

Titles, section membership and the "Terms on this page" glossary are defined in `scripts/generate_pages.py` and `scripts/content_extension.py`. After editing, rebuild all pages:

```bash
python3 scripts/generate_pages.py
```

To add a new article, add an entry to the relevant section's `pages` list in one of those two Python files and create the matching file under `scripts/articles/`.

Langfuse screenshots are referenced with the placeholders `{{IMG_TRACES_LIST}}`, `{{IMG_SPAN_TREE}}` and `{{IMG_TRACE_DETAIL}}` and live in `assets/images/langfuse/`.
