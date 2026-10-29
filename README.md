# Agentic Field Notes (static blog)

A self-contained **HTML + CSS** blog about building agentic AI systems, published at https://codertcet111.github.io/agentic-ai-learning/. No build step is needed to serve it; `scripts/generate_pages.py` rebuilds the pages after you edit content.

## Structure

```text
├── index.html                 # Home page
├── 404.html                   # Shown by GitHub Pages for missing pages
├── robots.txt / sitemap.xml   # For search engines
├── llms.txt                   # Hints for LLM crawlers
├── assets/
│   ├── css/site.css           # The whole theme
│   ├── js/site.js             # Opens and closes the Topics menu
│   ├── fonts/                 # Bricolage Grotesque, Literata, JetBrains Mono (self-hosted)
│   └── images/
│       ├── author/            # original.jpg plus the cropped portrait and avatar
│       ├── langfuse/          # Langfuse screenshots
│       ├── og-default.png     # Preview image for links shared on social media
│       └── favicon.svg
├── about/                     # About Shubham: experience timeline and profile links
├── agentic-development/       # The 20-step path (steps/ holds each step)
├── graph-orchestration/  data-patterns/  rag-knowledge/  evaluation/
├── build-guides/  langfuse-lab/  llm-engineering/  prompts-tools/
├── security-ai/  testing-ai-dev/
└── scripts/
    ├── generate_pages.py      # Builds every HTML page, the sitemap and robots.txt
    ├── content_extension.py   # Extra sections, glossary terms, screenshot captions
    ├── make_author_images.py  # Rebuilds the author photos and the social preview image
    └── articles/              # Article bodies, one file per post
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

### Search engines (SEO)

The site's address is already built in. Every page has a canonical link, a description, Open Graph tags and a preview image, and `sitemap.xml` and `robots.txt` point to `https://codertcet111.github.io/agentic-ai-learning/`. If the address ever changes, edit `SITE_URL` near the top of `scripts/generate_pages.py`, rebuild and push.

To get the site into Google faster:

1. Open [Google Search Console](https://search.google.com/search-console) and add a **URL prefix** property for `https://codertcet111.github.io/agentic-ai-learning/`.
2. Choose the **HTML file** verification method. Download the file Google gives you (named like `google1234abcd.html`), put it in the top folder of this repository next to `index.html`, push, then press **Verify**.
3. In Search Console open **Sitemaps** and submit `sitemap.xml`.
4. Optionally do the same in [Bing Webmaster Tools](https://www.bing.com/webmasters), which can import the site straight from Search Console.

New sites usually take a few days to a few weeks to appear in results.

## Reading progress

Readers can tick articles as complete, on the article itself or in any list. Progress bars on the home page, section pages and at the end of each article update straight away. Everything is stored in one cookie (`afn_progress`) in the reader's own browser, as short article ids; nothing is sent to a server. Article ids are derived from the section and file name, so renaming an article's file resets its tick. The logic is in `assets/js/site.js`.

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

Titles, section membership and the "Terms on this page" glossary are defined in `scripts/generate_pages.py` and `scripts/content_extension.py`. Your name for the byline, footer and About section is `AUTHOR_NAME` in the site identity block of `scripts/generate_pages.py`. After editing, rebuild all pages:

```bash
python3 scripts/generate_pages.py
```

To add a new article, add an entry to the relevant section's `pages` list in one of those two Python files and create the matching file under `scripts/articles/`.

Langfuse screenshots are referenced with placeholders such as `{{IMG_TRACES_LIST}}` (the full list is `IMAGE_PLACEHOLDERS` in `scripts/content_extension.py`) and live in `assets/images/langfuse/`.

To change the author photo, replace `assets/images/author/original.jpg` and run `python3 scripts/make_author_images.py assets/images/author/original.jpg . path/to/BricolageGrotesque.ttf` (the font is only needed for the social preview image).
