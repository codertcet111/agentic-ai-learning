#!/usr/bin/env python3
"""One-shot generator for static-blog HTML pages. Output is plain HTML/CSS/JS only."""

from __future__ import annotations

import html
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from content_extension import (
    AGENTIC_DEV_NOTES,
    IMAGE_META,
    IMAGE_PLACEHOLDERS,
    NEW_SECTIONS,
    SECTION_EXTRAS,
)

ROOT = Path(__file__).resolve().parents[1]
ARTICLES = Path(__file__).resolve().parent / "articles"

# Public URL of the deployed site, without a trailing slash.
# For GitHub Pages this is usually https://<username>.github.io/<repo-name>
# Override without editing: SITE_URL=https://you.github.io/blog python3 scripts/generate_pages.py
import os
SITE_URL = os.environ.get("SITE_URL", "https://codertcet111.github.io/agentic-ai-learning").rstrip("/")

_DESC_RE = re.compile(r"^\s*<!--\s*desc:\s*(.*?)\s*-->\s*", re.S)


def load_article(section: str, slug: str) -> tuple[str | None, str | None]:
    """Return (description, body_html) from scripts/articles/<section>/<slug>.html, if present."""
    path = ARTICLES / section / f"{slug}.html"
    if not path.exists():
        return None, None
    text = path.read_text(encoding="utf-8")
    m = _DESC_RE.match(text)
    if m:
        return m.group(1).strip(), text[m.end():]
    return None, text


def reading_time(body: str) -> int:
    words = len(re.sub(r"<[^>]+>", " ", body).split())
    return max(1, round(words / 220))


def _section_id(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def png_size(path: Path) -> tuple[int, int]:
    import struct
    with open(path, "rb") as f:
        head = f.read(24)
    return struct.unpack(">II", head[16:24])


def figure_img(depth: int, filename: str, alt: str, caption: str) -> str:
    prefix = "../" * depth
    path = f"{prefix}assets/images/langfuse/{html.escape(filename)}"
    w, h = png_size(ROOT / "assets" / "images" / "langfuse" / filename)
    return f"""<figure class="screenshot-figure">
  <a href="{path}" class="screenshot-link" target="_blank" rel="noopener noreferrer">
    <img src="{path}" alt="{html.escape(alt)}" loading="lazy" decoding="async" width="{w}" height="{h}">
  </a>
  <figcaption>{html.escape(caption)}</figcaption>
</figure>"""


def expand_body(body: str, depth: int) -> str:
    out = body
    for placeholder, filename in IMAGE_PLACEHOLDERS.items():
        alt, caption = IMAGE_META[filename]
        out = out.replace(placeholder, figure_img(depth, filename, alt, caption))
    return out


def all_other_sections() -> dict[str, dict]:
    merged: dict[str, dict] = dict(OTHER_SECTIONS)
    for section in NEW_SECTIONS:
        sid = _section_id(section["title"])
        if sid == "langfuse-lab":
            sid = "langfuse-lab"
        # Map titles to folder names explicitly
        folder_map = {
            "Langfuse Lab": "langfuse-lab",
            "LLM Engineering": "llm-engineering",
            "Prompts & Tools": "prompts-tools",
            "Security for AI": "security-ai",
            "Testing as an AI Dev": "testing-ai-dev",
        }
        sid = folder_map.get(section["title"], sid)
        merged[sid] = {
            "title": section["title"],
            "index_intro": section["index_intro"],
            "pages": list(section["pages"]),
        }
    for sid, extras in SECTION_EXTRAS.items():
        if sid in merged:
            merged[sid]["pages"].extend(extras)
    return merged

AGENTIC_STEPS: list[dict] = [
    {
        "slug": "01-orchestration-plane",
        "title": "Step 1 — Draw the orchestration boundary",
        "desc": "Separate the LLM control plane from your domain APIs before writing code.",
        "body": """
<p>Production agentic systems rarely fail because the model is weak. They fail because responsibilities blur: business rules leak into prompts, permissions live in graph state, and the orchestrator becomes a second monolith.</p>
<p>Start with a hard line. Your <strong>domain service</strong> owns data, authorization, and transactional writes. Your <strong>orchestration service</strong> owns conversation memory, routing, tool selection, and natural-language framing. The orchestrator calls the domain through a narrow invoke contract; it never re-implements payroll, inventory, or HR policy in Python strings.</p>
<div class="callout">If a rule must hold even when the model is offline, it belongs in the domain layer—not in a system prompt.</div>
<p>This pattern mirrors how mature API gateways work: translate intent, don't duplicate logic. Your chat UI talks to the orchestrator; the orchestrator fans out to existing REST or RPC surfaces with the same tokens the UI would use.</p>
""",
        "jargon": {
            "Orchestration plane": "The service that runs the LLM workflow, stores chat state, and calls tools—without owning business data.",
            "Domain service": "The system of record that enforces permissions and mutates business entities.",
            "Invoke contract": "A stable HTTP/RPC surface tools call with typed arguments and explicit success envelopes.",
        },
    },
    {
        "slug": "02-layered-architecture",
        "title": "Step 2 — Layer API, services, agents, providers",
        "desc": "Keep imports one-directional so the graph stays testable.",
        "body": """
<p>A maintainable agentic backend stacks four layers: HTTP routes, application services, graph/agents, and outbound providers. Routes validate transport concerns and call services. Services admit turns, persist transcripts, and run the graph. Graph nodes plan and invoke capabilities. Providers serialize HTTP to upstream systems.</p>
<pre><code>API → Services → Agents / Graph → Providers → Upstream APIs
Persistence &amp; cache sit beside services, not inside nodes.</code></pre>
<p>Graph nodes should not import FastAPI. Providers should not call the LLM. That separation lets you run the graph in unit tests with fakes while API tests exercise full envelopes.</p>
""",
        "jargon": {
            "Application service": "Use-case layer that coordinates persistence, cache, and graph execution.",
            "Provider": "Adapter that translates a capability call into an upstream HTTP request.",
            "Capability": "A catalog entry describing one tool: id, schema, provider, and side-effect class.",
        },
    },
    {
        "slug": "03-request-context",
        "title": "Step 3 — Keep auth in request context, not graph state",
        "desc": "Credentials must never be checkpointed or sent to the model.",
        "body": """
<p>LangGraph checkpoints serialize state. Anything in <code>GraphState</code> can land in Mongo, logs, or traces. Therefore authorization tokens, cookies, and employee identifiers used only for forwarding must live in <code>config[\"configurable\"][\"request_context\"]</code>, populated per run from middleware.</p>
<p>Shared HTTP clients should reject cookie jars on the pool so concurrent users cannot bleed sessions. Each outbound call re-attaches headers from context. Redaction helpers scrub mappings before logging.</p>
<div class="callout">Advertised capability ≠ authorized capability. Check at invoke time, and let the upstream check again.</div>
""",
        "jargon": {
            "Request context": "Per-request struct with correlation id, locale, org scope, and forwarded auth.",
            "Checkpoint": "Persisted graph snapshot used to resume or audit a workflow.",
            "Redaction": "Removing secrets and PII from structures before logging or exporting traces.",
        },
    },
    {
        "slug": "04-sessions-conversations",
        "title": "Step 4 — Model sessions and conversations",
        "desc": "Separate who is chatting from which thread they are in.",
        "body": """
<p>A <strong>session</strong> binds an authenticated principal to TTL, org scope, and pinned catalog versions. A <strong>conversation</strong> is one chat thread with revision counters, message limits, and lifecycle (active, deactivated).</p>
<p>Sessions are created at login or handoff; conversations are created when the user opens a new thread. Index session id on conversations for list views. Never store raw tokens on either document—only opaque ids and metadata the UI needs.</p>
""",
        "jargon": {
            "Session document": "Durable record of a signed-in chat principal and expiry.",
            "Conversation revision": "Monotonic counter used to reject stale client writes.",
            "Deactivation": "Terminal state when limits are hit or the user ends the thread.",
        },
    },
    {
        "slug": "05-turn-admission",
        "title": "Step 5 — Admit turns with leases and fences",
        "desc": "Mongo is authoritative; Redis only advises.",
        "body": """
<p>Each user message is a <strong>turn</strong>. Before running the graph, acquire a conversation fence with compare-and-set on the expected revision. Use a turn ledger document to record in-progress, completed, and cancelled states.</p>
<p>Redis leases can short-circuit duplicate work but must never be the sole gate—if Redis is down, Mongo still decides correctness. Replay exact client request ids before rejecting revisions so mobile clients recover cleanly.</p>
""",
        "jargon": {
            "Turn ledger": "Per-turn record of status, run id, and idempotency metadata.",
            "Fence CAS": "Conditional update that fails if another writer advanced the conversation.",
            "Advisory cache": "Redis structure that speeds up checks without owning truth.",
        },
    },
    {
        "slug": "06-mongo-collections-map",
        "title": "Step 6 — Map Mongo collections to roles",
        "desc": "One collection per concern; register indexes at startup.",
        "body": """
<p>A typical orchestration database includes: messages, sessions, conversations, graph checkpoints, pending interactions, turn ledger, step results, usage counters, failure records, and catalog version pins. Transcripts may be normalized into messages with monotonic <code>sequence</code> per conversation.</p>
<p>Define collection names and <code>IndexModel</code> lists in one module; create indexes during lifespan bootstrap, never at import time. Partial unique indexes enforce idempotency only when optional fields exist.</p>
""",
        "jargon": {
            "Partial index": "Mongo index with a filter expression so uniqueness applies only to matching docs.",
            "Lifespan bootstrap": "FastAPI startup hook that opens clients and ensures indexes.",
            "Step result": "Persisted output of a graph step for debugging or UI replay.",
        },
    },
    {
        "slug": "07-messages-transcripts",
        "title": "Step 7 — Append messages, don't mutate arrays",
        "desc": "Ordered, idempotent appends scale better than giant documents.",
        "body": """
<p>Store one document per message with <code>conversation_id</code>, <code>sequence</code>, role, payload, and optional <code>idempotency_key</code>. Unique compound indexes prevent duplicate appends on retry. Assistant payloads can embed structured UI blocks (forms, tables) separate from plain text.</p>
<p>Reads order by sequence. Avoid unbounded arrays on a conversation document—they fight Mongo's document size limit and complicate concurrent writes.</p>
""",
        "jargon": {
            "Idempotency key": "Client-supplied token so retries do not duplicate messages.",
            "Sequence": "Monotonic integer establishing deterministic transcript order.",
            "Payload": "Structured message body including tool calls and UI metadata.",
        },
    },
    {
        "slug": "08-pending-interactions",
        "title": "Step 8 — Pending forms and exact resume",
        "desc": "Only a typed form submission continues a paused workflow.",
        "body": """
<p>When the graph needs user input, create a <strong>pending interaction</strong> with id, revision, and schema. The UI renders it; ordinary chat text must not silently resume the old form—that would merge incompatible intents.</p>
<p>Resume only through <code>form_submission</code> naming the pending id and revision. Supersede pending state when the user sends free text to start a new workflow. Clean legacy checkpoints only when migration requires it.</p>
""",
        "jargon": {
            "Pending interaction": "Durable pause point waiting for structured user input.",
            "Supersede": "Mark an old interaction inactive when a new user intent arrives.",
            "Form submission": "Control message that validates against the pending schema.",
        },
    },
    {
        "slug": "09-capability-catalog",
        "title": "Step 9 — Merge and pin the capability catalog",
        "desc": "Tools advertised to the planner must match what invoke can reach.",
        "body": """
<p>Upstream services publish capability JSON (id, parameters, provider, risk). The orchestrator merges catalogs, normalizes schemas, hashes versions, and pins the hash on the session so a mid-chat deploy does not change tool shapes unexpectedly.</p>
<p>Refresh catalogs on a schedule or webhook. Cache in Redis with TTL; on miss, reload from upstream and Mongo version store. Coverage reports show catalog capabilities no active agent exposes—fix drift before users hit dead ends.</p>
""",
        "jargon": {
            "Catalog hash": "Fingerprint of merged tool definitions used for routing consistency.",
            "Normalizer": "Code that converts upstream JSON into typed internal models.",
            "Coverage report": "Diff between catalog tools and agent registrations.",
        },
    },
    {
        "slug": "10-providers-invoke",
        "title": "Step 10 — Provider adapters and invoke",
        "desc": "One client pool, explicit timeouts, circuit breakers per upstream.",
        "body": """
<p>Each provider implements <code>invoke(capability_id, arguments, context)</code> with shared HTTP machinery: connect/read timeouts, bounded retries on transient errors, per-upstream circuit breakers, and typed parsing of success envelopes.</p>
<p>Writes require <code>explicit_action</code> flags and stable operation ids derived from the request and step—not from model-generated arguments. That prevents duplicate payroll runs when the user double-taps send.</p>
""",
        "jargon": {
            "Circuit breaker": "Pattern that stops calling a failing upstream until it recovers.",
            "Explicit action": "Flag proving the user confirmed a mutating tool call.",
            "Operation id": "Dedupe key for side-effecting capabilities.",
        },
    },
    {
        "slug": "11-langgraph-skeleton",
        "title": "Step 11 — Wire LangGraph with a checkpointer",
        "desc": "Compile once at startup; persist checkpoints in Mongo.",
        "body": """
<p>Build a <code>StateGraph</code> with typed state, add nodes as plain async callables, and route with functions that read state but never mutate it. Attach an async Mongo checkpointer so workflows survive process restarts.</p>
<p>Thread id should identify checkpoint lineage for a run; do not overload it with auth or tenant ids. Compile the graph in lifespan after repositories exist.</p>
""",
        "jargon": {
            "StateGraph": "LangGraph structure of nodes and conditional edges.",
            "Checkpointer": "Saver that writes graph state snapshots between nodes.",
            "Thread id": "Stable key grouping checkpoints for one workflow lineage.",
        },
    },
    {
        "slug": "12-graph-nodes-flow",
        "title": "Step 12 — Walk the node pipeline",
        "desc": "Load, route, plan, resolve, invoke, branch, compose.",
        "body": """
<p>A production pipeline often runs:</p>
<ol>
<li><strong>load_session</strong> — hydrate capabilities and persona.</li>
<li><strong>route_request</strong> — direct recipes vs model path.</li>
<li><strong>plan_next_step</strong> — choose capability or ask for input.</li>
<li><strong>resolve_arguments</strong> — fill parameters; lookups add trace, not chosen ids.</li>
<li><strong>invoke_capability</strong> — provider call with auth checks.</li>
<li><strong>evaluate_condition</strong> — branch on structured results.</li>
<li><strong>request_input</strong> — pause for forms.</li>
<li><strong>compose_response</strong> — user-visible text in en/ar.</li>
</ol>
<p>Sub-agent handoffs may use <code>next_agent_step</code> without duplicating the outer graph.</p>
""",
        "jargon": {
            "Direct recipe": "Deterministic command matched before any LLM call.",
            "Lookup trace": "Recorded search results so the planner picks real ids.",
            "Compose": "Final natural-language packaging for the user.",
        },
    },
    {
        "slug": "13-typed-llm-schemas",
        "title": "Step 13 — Typed Pydantic outputs for every LLM call",
        "desc": "Never prompt for raw JSON blobs without a schema.",
        "body": """
<p>Each model call maps to a Pydantic model in a shared schemas module: planner decisions, argument fills, condition evaluations, and compose payloads. The LLM client validates JSON into these types; invalid output triggers repair or safe failure.</p>
<p>Policy text lives in one definition module per concern—node rules in graph definition, voice in agent prompts. Avoid duplicating "never do X" across schema notes and prompts.</p>
""",
        "jargon": {
            "Structured output": "Model response parsed into a validated object, not free text.",
            "Planner": "LLM step that selects the next capability or completion.",
            "Repair loop": "Retry or fallback when validation fails.",
        },
    },
    {
        "slug": "14-argument-resolution",
        "title": "Step 14 — Resolve arguments without smuggling ids",
        "desc": "Resolvers enrich context; the model still chooses.",
        "body": """
<p>Resolution merges user text, prior step results, and lookup responses into invoke arguments. When a parameter needs an entity id, run a lookup capability, append the full result to <code>lookup_trace</code>, and replan—do not auto-pick the first row.</p>
<p>Grounding modules can post-process mutation arguments against domain rules (dates, quantities) before invoke.</p>
""",
        "jargon": {
            "Argument resolver": "Graph node that prepares tool parameters from state.",
            "Grounding": "Deterministic validation of model-produced mutation fields.",
            "Replan": "Second planner pass after new evidence arrives.",
        },
    },
    {
        "slug": "15-routing-recipes",
        "title": "Step 15 — Known commands before the model",
        "desc": "Bind exact phrases for safety-critical or demo paths.",
        "body": """
<p>Register English and Arabic aliases for commands like "reset conversation" or "show usage." Exact matches bind the actor and return deterministic responses—they never fall through to the LLM.</p>
<p>This cuts cost, improves reliability for support scripts, and gives security teams predictable behavior for sensitive operations.</p>
""",
        "jargon": {
            "Alias map": "Locale-specific strings mapped to internal command ids.",
            "Actor binding": "Attaching the command to the current session principal.",
            "Fallthrough": "Accidentally sending deterministic traffic to the LLM.",
        },
    },
    {
        "slug": "16-presentation-modes",
        "title": "Step 16 — Presentation modes and bilingual compose",
        "desc": "UI-rendered results still need fallback text.",
        "body": """
<p>Structured results (tables, charts, forms) set <code>presentation.mode</code> so the client picks a renderer. Compose runs when the user needs words: always provide English and Arabic fallback strings even if the UI is primary.</p>
<p><code>response_finalized</code> gates whether compose executes again on subsequent nodes.</p>
""",
        "jargon": {
            "Presentation mode": "Hint telling the client how to render a capability result.",
            "Fallback text": "Plain-language summary if the rich UI cannot load.",
            "Locale": "User language preference driving compose output.",
        },
    },
    {
        "slug": "17-redis-cache-patterns",
        "title": "Step 17 — Redis for catalog, caps, and locks",
        "desc": "Namespace keys, TTL everything, rebuild on miss.",
        "body": """
<p>Cache merged catalogs, per-user capability snapshots, and short-lived conversation locks. Keys must include version prefix, tenant slug, and entity id. Document TTL beside each use.</p>
<p>On Redis failure, degrade gracefully: load from Mongo or upstream, never drop messages. Locks are advisory—Mongo turn admission remains decisive.</p>
""",
        "jargon": {
            "Degrading cache": "Wrapper that bypasses Redis when unavailable.",
            "TTL": "Time-to-live after which a key expires automatically.",
            "Namespace": "Prefix preventing cross-tenant key collisions.",
        },
    },
    {
        "slug": "18-observability-tracing",
        "title": "Step 18 — Trace requests, nodes, and LLM calls",
        "desc": "Correlate X-Request-Id → conversation → run → spans.",
        "body": """
<p>Emit spans for <code>agent.request</code>, <code>langgraph.run</code>, each <code>langgraph.node</code>, <code>llm.call</code>, and <code>capability.invoke</code>. Export to your tracing backend (e.g. Langfuse-style exporters) with pseudonymized user ids.</p>
<p>Pattern alerts on repeated planner failures or invoke 403 spikes. Never attach tokens to span attributes.</p>
""",
        "jargon": {
            "Span": "Single timed operation within a distributed trace.",
            "Pseudonym": "Reversible or hashed identifier safe for third-party SaaS.",
            "Exporter": "Component that ships traces to an observability backend.",
        },
    },
    {
        "slug": "19-rag-knowledge-hooks",
        "title": "Step 19 — Add RAG without breaking the graph",
        "desc": "Retrieval is another capability—or a dedicated sub-agent.",
        "body": """
<p>Company knowledge bases (policies, handbooks) fit as retrieval capabilities with citation metadata. Index chunks in a vector or hybrid store; expose <code>search_documents</code> to the planner. Keep chunk text out of checkpoints when possible—store references and fetch on demand.</p>
<p>Evaluate retrieval with labeled questions before enabling auto-answers. Fuse lexical and vector search when your content is acronym-heavy.</p>
""",
        "jargon": {
            "RAG": "Retrieval-augmented generation—fetch context before answering.",
            "Chunk": "Small passage stored with embedding and source metadata.",
            "Hybrid search": "Combining keyword and vector similarity scores.",
        },
    },
    {
        "slug": "20-evaluation-golden-suite",
        "title": "Step 20 — Golden evals and regression gates",
        "desc": "Freeze behavior with JSON cases, not vibes.",
        "body": """
<p>Store golden cases as JSON: user message, expected capability sequence or outcome class, and safety tags. Run them in CI with stubbed LLMs for plumbing cases and selective live runs nightly.</p>
<p>Track multi-turn flows (leaves, attendance, billing) separately from single-shot Q&A. Publish HTML or Markdown reports from the runner. Block releases when critical safety cases fail.</p>
<p>Tech choices that work well here: pytest as runner, schema-validated fixtures, optional Langfuse for trace compare, and Bedrock or OpenAI-compatible endpoints behind LiteLLM for portability.</p>
""",
        "jargon": {
            "Golden case": "Recorded scenario with expected orchestration behavior.",
            "Stub LLM": "Deterministic model double returning canned structured output.",
            "Regression gate": "CI job that fails when behavior drifts from approved baselines.",
        },
    },
]

OTHER_SECTIONS: dict[str, dict] = {
    "graph-orchestration": {
        "title": "Graph & Orchestration",
        "index_intro": "LangGraph patterns, routing functions, and multi-agent handoffs—explained for builders.",
        "pages": [
            ("conditional-routing", "Conditional routing without side effects", "graph", """
<p>Routing functions inspect <code>GraphState</code> and return the next node name. They never write state—that happens in nodes. This keeps diagrams truthful and tests simple: given state X, expect edge Y.</p>
""", {"Routing function": "Pure selector between graph nodes.", "Edge": "Named transition emitted by a router."}),
            ("checkpointing", "Checkpointing and recovery", "graph", """
<p>Checkpoints capture channel values after each node. On crash, resume from the last successful node. Cap checkpoint size by storing references to large tool results in Mongo instead of inline blobs.</p>
""", {"Channel": "Named slice of graph state LangGraph merges.", "Recovery": "Resuming a run from persisted checkpoint data."}),
            ("multi-agent", "Multi-agent delegation", "graph", """
<p>Register sub-agents in a JSON registry seeded at boot. The orchestrator passes capability subsets per agent card. Hand off with <code>next_agent_step</code> when a specialized persona should own the thread.</p>
""", {"Agent card": "Metadata describing a sub-agent's scope and voice.", "Handoff": "Transferring control to another agent definition."}),
            ("human-in-the-loop", "Human-in-the-loop pauses", "graph", """
<p>Use pending interactions for approvals and forms. Time-bound expirations with fingerprinted keys so stale UI cannot submit. Emit transition messages when expiring.</p>
""", {"HITL": "Workflow pause until a human confirms or supplies data.", "Fingerprint": "Hash detecting outdated client UI state."}),
        ],
    },
    "data-patterns": {
        "title": "Mongo for AI",
        "index_intro": "Schema patterns for chat, tools, eval artifacts, and knowledge metadata.",
        "pages": [
            ("chat-schema", "Chat message schema", "data", """
<p>Prefer append-only messages with sequence numbers. Embed tool call ids linking to <code>step_results</code> for auditor-friendly replays.</p>
""", {"Append-only": "Storage pattern that only inserts new rows.", "Tool call id": "Correlation between assistant action and provider request."}),
            ("interaction-schema", "Interaction and form schema", "data", """
<p>Pending interactions store JSON Schema or custom field defs, revision, and expiry. Index by conversation id and status for fast lookups.</p>
""", {"JSON Schema": "Machine-readable description of allowed form fields.", "Revision": "Incremented when the server changes the form."}),
            ("usage-metering", "Usage counters and quotas", "data", """
<p>Increment token and invoke counters per org and day. Use upserts with capped TTL for dashboards; never use counters as billing without reconciliation.</p>
""", {"Upsert": "Update or insert in one atomic operation.", "Quota": "Soft or hard limit on model or tool usage."}),
            ("failure-records", "Failure records for support", "data", """
<p>Persist sanitized failure documents with request id, conversation id, and error class—not raw upstream bodies.</p>
""", {"Error class": "Stable code mapping for support runbooks.", "Sanitize": "Strip secrets before persistence."}),
            ("vector-metadata", "Vector metadata alongside Mongo", "data", """
<p>Store chunk ids, source uri, acl scope, and embedding model version in Mongo while vectors live in Pinecone, pgvector, or OpenSearch. Keep ACL checks in the domain API.</p>
""", {"ACL scope": "Who may retrieve a chunk at query time.", "Embedding version": "Model id used to produce vectors."}),
        ],
    },
    "rag-knowledge": {
        "title": "RAG & Knowledge",
        "index_intro": "Retrieval design for policy bots, support assistants, and in-app copilots.",
        "pages": [
            ("chunking", "Chunking strategies", "rag", """
<p>Split on headings and paragraphs; overlap 10–15% for continuity. Store page numbers and section titles for citations.</p>
""", {"Overlap": "Repeated tokens between adjacent chunks to preserve context.", "Citation": "Pointer to source location shown to the user."}),
            ("retrieval-api", "Expose retrieval as a tool", "rag", """
<p>Let the planner call retrieval instead of silently injecting context every turn—saves tokens and makes traces legible.</p>
""", {"Tool exposure": "Making retrieval visible in planner traces.", "Silent injection": "Automatic context prepend without logging."}),
            ("freshness", "Freshness and re-indexing", "rag", """
<p>Version documents when upstream CMS changes. Background jobs diff content hashes and re-embed only changed chunks.</p>
""", {"Re-embed": "Recompute vectors after text changes.", "Content hash": "Fingerprint detecting document edits."}),
            ("safety", "RAG safety and ACL", "rag", """
<p>Filter chunks by principal permissions before the model sees them. Log retrieval sets for audit.</p>
""", {"Pre-filter": "Permission check applied before ranking.", "Audit log": "Record of which chunks influenced an answer."}),
        ],
    },
    "evaluation": {
        "title": "Eval & Observability",
        "index_intro": "Measuring planner quality, tool accuracy, and latency budgets.",
        "pages": [
            ("golden-files", "Golden JSON cases", "eval", """
<p>One file per scenario with tags (domain, risk, multi-turn). Validate against a JSON Schema in CI.</p>
""", {"Tag": "Label for filtering suites in CI.", "Fixture": "Static input/output pair for tests."}),
            ("llm-judges", "LLM-as-judge—with guardrails", "eval", """
<p>Use judges only for rubric scores, not safety allow/deny. Prefer deterministic asserts on capability ids for writes.</p>
""", {"Rubric": "Scoring criteria given to a judge model.", "Deterministic assert": "Exact match expectation in tests."}),
            ("trace-compare", "Trace compare across releases", "eval", """
<p>Export spans per golden run; diff node sequences when refactoring graphs.</p>
""", {"Span diff": "Comparison of node order between two runs.", "Baseline": "Approved trace from a known-good release."}),
            ("observability-stack", "Observability stack choices", "eval", """
<p>Pair structured logs (request id), APM traces, and LLM observability (Langfuse-class tools). Rollbar or Sentry for uncaught exceptions with redaction.</p>
""", {"APM": "Application performance monitoring with distributed tracing.", "LLM observability": "Products specialized in prompt/response logging."}),
        ],
    },
    "build-guides": {
        "title": "Build Guides",
        "index_intro": "From a single feature to a small product—practical recipes.",
        "pages": [
            ("feature-slice", "Ship one copilot feature", "default", """
<p>Pick one read-only capability, one compose template, and a narrow agent card. Stub the LLM in CI; ship behind a feature flag.</p>
""", {"Feature flag": "Runtime toggle isolating new behavior.", "Read-only capability": "Tool that does not mutate domain data."}),
            ("write-path", "Add a confirmed write", "default", """
<p>Require explicit_action, show a confirmation form, and dedupe with operation ids. Test double-submit aggressively.</p>
""", {"Double-submit": "Duplicate user action causing repeated writes.", "Confirmation form": "UI step proving intent."}),
            ("local-dev", "Local dev topology", "default", """
<p>Run Mongo and Redis locally, point providers at a sandbox API, use LLM_STUB for graph tests. Mirror production headers in .env.</p>
""", {"LLM stub": "Fake model returning fixed structured responses.", "Sandbox API": "Non-production upstream with test data."}),
            ("cost-controls", "Cost and rate limits", "default", """
<p>Cap tokens per turn, circuit-break noisy tools, and cache catalog merges. Industry benchmarks (ADB-class tasks) justify per-tenant rate limits.</p>
""", {"Token cap": "Maximum model tokens consumed per user turn.", "Rate limit": "Throttle on requests per time window."}),
        ],
    },
}


# ---------------------------------------------------------------------------
# Site identity
# ---------------------------------------------------------------------------

SITE_NAME = "Agentic Field Notes"
# Shown in the byline, footer and About section. Leave empty for a generic byline.
AUTHOR_NAME = os.environ.get("AUTHOR_NAME", "")
AUTHOR_ROLE = "AI application developer"
GITHUB_URL = "https://github.com/codertcet111"
REPO_URL = "https://github.com/codertcet111/agentic-ai-learning"

TOPIC_GROUPS: list[tuple[str, list[tuple[str, str, str]]]] = [
    ("Build the system", [
        ("agentic-development", "Agentic Development", "Twenty steps from a blank repo to a production agent backend"),
        ("graph-orchestration", "Graph & Orchestration", "Routing, checkpoints, multi-agent handoffs and pauses"),
        ("data-patterns", "Mongo for AI", "Schemas for chat, turns, forms, usage and vectors"),
        ("build-guides", "Build Guides", "Ship a first feature, add writes, run it locally, control cost"),
    ]),
    ("Models and knowledge", [
        ("llm-engineering", "LLM Engineering", "Gateways, structured outputs, stubs, context windows"),
        ("prompts-tools", "Prompts & Tools", "Tool descriptions, planner policy, lookups, two languages"),
        ("rag-knowledge", "RAG & Knowledge", "Chunking, retrieval as a tool, freshness and access control"),
    ]),
    ("Quality and safety", [
        ("evaluation", "Eval & Observability", "Golden cases, judges, trace diffs, monitoring stack"),
        ("langfuse-lab", "Langfuse Lab", "A screenshot tour of traces, spans, tokens and budgets"),
        ("testing-ai-dev", "Testing as an AI Dev", "Graph specs, fakes, golden runner, tracing tests"),
        ("security-ai", "Security for AI", "Token forwarding, layered authorization, safe writes"),
    ]),
]
TOPIC_INFO = {sid: (title, desc) for _, items in TOPIC_GROUPS for sid, title, desc in items}

LOGO_SVG = (
    '<svg viewBox="0 0 30 22" aria-hidden="true">'
    '<path d="M6 16 L15 6 L24 16" fill="none" stroke="#12152b" stroke-width="2.2" stroke-linecap="round"/>'
    '<circle cx="6" cy="16" r="4" fill="#2b3cff"/>'
    '<circle cx="15" cy="6" r="4" fill="#12152b"/>'
    '<circle cx="24" cy="16" r="4" fill="#ffe066" stroke="#12152b" stroke-width="1.6"/>'
    "</svg>"
)

CHEVRON = (
    '<svg class="chev" viewBox="0 0 12 12" aria-hidden="true">'
    '<path d="M2 4.5 L6 8 L10 4.5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>'
)

CURRENT_ATTR = ' aria-current="page"'


def esc(text: str) -> str:
    return html.escape(text, quote=True)


def public_url(canonical_path: str) -> str:
    return SITE_URL + canonical_path.replace("/static-blog", "", 1)


def author_label() -> str:
    return AUTHOR_NAME or f"an {AUTHOR_ROLE}"


def header_html(prefix: str, current: str | None) -> str:
    groups = []
    for gtitle, items in TOPIC_GROUPS:
        lis = "".join(
            f'<li><a href="{prefix}{sid}/index.html"'
            f'{CURRENT_ATTR if sid == current else ""}>'
            f'<span class="topic-name">{esc(title)}</span>'
            f'<span class="topic-desc">{esc(desc)}</span></a></li>'
            for sid, title, desc in items
        )
        groups.append(f'<div class="topic-group"><h2>{esc(gtitle)}</h2><ul>{lis}</ul></div>')
    start_current = CURRENT_ATTR if current == "agentic-development" else ""
    groups_html = "".join(groups)
    return f"""<header class="site-header">
  <div class="header-inner">
    <a class="logo" href="{prefix}index.html">{LOGO_SVG}<span>{SITE_NAME}</span></a>
    <nav class="primary-nav" aria-label="Primary">
      <a class="nav-link" href="{prefix}agentic-development/index.html"{start_current}>Start here</a>
      <button type="button" class="nav-button" data-menu-toggle aria-expanded="false" aria-controls="topics-panel">Topics {CHEVRON}</button>
      <a class="nav-link" href="{prefix}index.html#about">About</a>
      <button type="button" class="nav-button menu-toggle" data-menu-toggle aria-expanded="false" aria-controls="topics-panel">Menu</button>
    </nav>
  </div>
  <div class="topics-panel" id="topics-panel" hidden>
    <div class="topics-inner">
      <div class="topics-mobile-links"><a class="primary" href="{prefix}agentic-development/index.html">Start the 20-step path</a><a href="{prefix}index.html#about">About</a></div>
      {groups_html}
    </div>
  </div>
</header>"""


def footer_html(prefix: str) -> str:
    who = f"<strong>{esc(AUTHOR_NAME)}</strong>" if AUTHOR_NAME else "<strong>Agentic Field Notes</strong>"
    return f"""<footer class="site-footer">
  <div class="footer-inner">
    <div class="footer-author">
      <img src="{prefix}assets/images/author/avatar.jpg" alt="" width="48" height="48" loading="lazy">
      <div>{who}Notes on building AI agents, written by {esc(author_label())}.</div>
    </div>
    <nav class="footer-links" aria-label="Footer">
      <a href="{prefix}agentic-development/index.html">20-step path</a>
      <a href="{GITHUB_URL}">GitHub</a>
      <a href="{prefix}sitemap.xml">Sitemap</a>
    </nav>
  </div>
</footer>"""


def breadcrumb_html(items: list[tuple[str, str | None]]) -> str:
    parts = []
    for label, href in items:
        parts.append(f'<a href="{href}">{esc(label)}</a>' if href else f'<span aria-current="page">{esc(label)}</span>')
    return '<nav class="breadcrumb" aria-label="Breadcrumb">' + '<span class="sep">/</span>'.join(parts) + "</nav>"


def jargon_html(jargon: dict[str, str]) -> str:
    if not jargon:
        return ""
    items = "".join(f"<dt>{esc(k)}</dt><dd>{esc(v)}</dd>" for k, v in jargon.items())
    return f"""<section class="jargon" aria-labelledby="jargon-heading">
  <h2 id="jargon-heading">Terms on this page</h2>
  <dl>{items}</dl>
</section>"""


def document(*, title: str, description: str, canonical_path: str, depth: int,
             main: str, current: str | None, schema: dict, og_type: str = "article",
             full_title: str | None = None) -> str:
    import json
    prefix = "../" * depth
    url = public_url(canonical_path)
    og_image = f"{SITE_URL}/assets/images/og-default.png"
    page_title = full_title or f"{title} | {SITE_NAME}"
    schema_json = json.dumps(schema, ensure_ascii=False)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(page_title)}</title>
  <meta name="description" content="{esc(description)}">
  <meta name="author" content="{esc(AUTHOR_NAME or AUTHOR_ROLE)}">
  <meta name="robots" content="index, follow">
  <meta name="theme-color" content="#ffffff">
  <link rel="canonical" href="{esc(url)}">
  <link rel="icon" href="{prefix}assets/images/favicon.svg" type="image/svg+xml">
  <meta property="og:site_name" content="{SITE_NAME}">
  <meta property="og:title" content="{esc(title)}">
  <meta property="og:description" content="{esc(description)}">
  <meta property="og:type" content="{og_type}">
  <meta property="og:url" content="{esc(url)}">
  <meta property="og:image" content="{og_image}">
  <meta name="twitter:card" content="summary_large_image">
  <link rel="preload" href="{prefix}assets/fonts/bricolage-grotesque.woff2" as="font" type="font/woff2" crossorigin>
  <link rel="preload" href="{prefix}assets/fonts/literata.woff2" as="font" type="font/woff2" crossorigin>
  <link rel="stylesheet" href="{prefix}assets/css/site.css">
  <script type="application/ld+json">{schema_json}</script>
</head>
<body>
  <a class="skip-link" href="#main">Skip to content</a>
  {header_html(prefix, current)}
  <main id="main">
{main}
  </main>
  {footer_html(prefix)}
  <script src="{prefix}assets/js/site.js" defer></script>
</body>
</html>
"""


def author_schema() -> dict:
    return {"@type": "Person", "name": AUTHOR_NAME or AUTHOR_ROLE, "url": GITHUB_URL}


def article_page(*, section_id: str, title: str, description: str, canonical_path: str,
                 depth: int, crumbs: list[tuple[str, str | None]], body: str,
                 jargon: dict[str, str], nav_html: str, heading: str | None = None) -> str:
    prefix = "../" * depth
    minutes = reading_time(body)
    byline = (f'<span class="byline"><img src="{prefix}assets/images/author/avatar.jpg" alt="" width="28" height="28">'
              f'{esc(AUTHOR_NAME)}</span>') if AUTHOR_NAME else ""
    main = f"""<header class="page-head grid-paper">
  <div class="page-head-inner">
    {breadcrumb_html(crumbs)}
    <h1>{esc(heading or title)}</h1>
    <p class="lead">{esc(description)}</p>
    <p class="meta">{byline}<span>{minutes} min read</span></p>
  </div>
</header>
<article class="prose">
{body}
{jargon_html(jargon)}
{nav_html}
</article>"""
    schema = {
        "@context": "https://schema.org",
        "@type": "TechArticle",
        "headline": title,
        "description": description,
        "url": public_url(canonical_path),
        "image": f"{SITE_URL}/assets/images/og-default.png",
        "author": author_schema(),
        "isPartOf": {"@type": "WebSite", "name": SITE_NAME, "url": SITE_URL + "/"},
    }
    return document(title=title, description=description, canonical_path=canonical_path,
                    depth=depth, main=main, current=section_id, schema=schema)


def index_page(*, section_id: str, title: str, intro: str, canonical_path: str,
               list_html: str, extra: str = "") -> str:
    main = f"""<header class="page-head grid-paper wide">
  <div class="page-head-inner">
    {breadcrumb_html([("Home", "../index.html"), (title, None)])}
    <h1>{esc(title)}</h1>
    <p class="lead">{esc(intro)}</p>
  </div>
</header>
<div class="prose wide">
{extra}
{list_html}
</div>"""
    schema = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": title,
        "description": intro,
        "url": public_url(canonical_path),
    }
    return document(title=title, description=intro, canonical_path=canonical_path,
                    depth=1, main=main, current=section_id, schema=schema, og_type="website")


def nav_pair(prev: tuple[str, str] | None, nxt: tuple[str, str] | None) -> str:
    if not prev and not nxt:
        return ""
    parts = []
    if prev:
        parts.append(f'<a class="prev" href="{prev[0]}"><small>Previous</small>{esc(prev[1])}</a>')
    if nxt:
        parts.append(f'<a class="next" href="{nxt[0]}"><small>Next</small>{esc(nxt[1])}</a>')
    return f'<nav class="post-nav" aria-label="More articles">{"".join(parts)}</nav>'


def step_label(title: str) -> str:
    """'Step 3 — Keep auth…' -> 'Keep auth…' for headings and compact lists."""
    return re.sub(r"^Step \d+\s*[—-]\s*", "", title)


def write_agentic_pages() -> list[str]:
    paths: list[str] = []
    section_dir = ROOT / "agentic-development"
    (section_dir / "steps").mkdir(parents=True, exist_ok=True)

    items = []
    for i, s in enumerate(AGENTIC_STEPS, 1):
        d, b = load_article("agentic-development", s["slug"])
        s["_desc"] = d or s["desc"]
        s["_body"] = b or s["body"]
        items.append(
            f'<li><a href="steps/{s["slug"]}.html"><span class="num">{i:02d}</span>'
            f'<span class="title">{esc(step_label(s["title"]))}</span>'
            f'<span class="time">{reading_time(s["_body"])} min</span>'
            f'<span class="desc">{esc(s["_desc"])}</span></a></li>'
        )
    intro_extra = ("<p>Read these in order. Each step builds on the one before, from drawing the boundary "
                   "between your agent and your business APIs to freezing behaviour with golden tests. "
                   "Examples use a fictional HR assistant so you can map the ideas onto your own domain.</p>")
    items_html = "".join(items)
    (section_dir / "index.html").write_text(
        index_page(
            section_id="agentic-development",
            title="Agentic Development",
            intro="A twenty-step path to designing and shipping an agentic backend that holds up in production.",
            canonical_path="/static-blog/agentic-development/",
            list_html=f'<ol class="article-list numbered">{items_html}</ol>',
            extra=intro_extra,
        ),
        encoding="utf-8",
    )
    paths.append("agentic-development/index.html")

    n = len(AGENTIC_STEPS)
    for i, step in enumerate(AGENTIC_STEPS, 1):
        prev = (f'{AGENTIC_STEPS[i - 2]["slug"]}.html', step_label(AGENTIC_STEPS[i - 2]["title"])) if i > 1 else None
        nxt = (f'{AGENTIC_STEPS[i]["slug"]}.html', step_label(AGENTIC_STEPS[i]["title"])) if i < n else None
        dev = AGENTIC_DEV_NOTES.get(step["slug"], "")
        dev_html = f'<div class="callout dev-pov"><strong>Try this:</strong> {esc(dev)}</div>' if dev else ""
        fname = f"steps/{step['slug']}.html"
        (section_dir / fname).write_text(
            article_page(
                section_id="agentic-development",
                title=f"Step {i}: {step_label(step['title'])}",
                heading=step_label(step["title"]),
                description=step["_desc"],
                canonical_path=f"/static-blog/agentic-development/{fname}",
                depth=2,
                crumbs=[("Home", "../../index.html"), ("Agentic Development", "../index.html"), (f"Step {i} of {n}", None)],
                body=step["_body"] + dev_html,
                jargon=step["jargon"],
                nav_html=nav_pair(prev, nxt),
            ),
            encoding="utf-8",
        )
        paths.append(f"agentic-development/{fname}")
    return paths


def write_other_sections() -> list[str]:
    paths: list[str] = []
    for section_id, meta in all_other_sections().items():
        section_dir = ROOT / section_id
        section_dir.mkdir(parents=True, exist_ok=True)
        loaded = []
        for slug, title, _visual, body, jargon in meta["pages"]:
            d, b = load_article(section_id, slug)
            loaded.append((slug, title, d or title, b or body, jargon))

        items = "".join(
            f'<li><a href="{slug}.html"><span class="title">{esc(title)}</span>'
            f'<span class="time">{reading_time(body)} min</span>'
            f'<span class="desc">{esc(desc)}</span></a></li>'
            for slug, title, desc, body, _ in loaded
        )
        (section_dir / "index.html").write_text(
            index_page(
                section_id=section_id,
                title=meta["title"],
                intro=meta["index_intro"],
                canonical_path=f"/static-blog/{section_id}/",
                list_html=f'<ul class="article-list">{items}</ul>',
            ),
            encoding="utf-8",
        )
        paths.append(f"{section_id}/index.html")

        for i, (slug, title, desc, body, jargon) in enumerate(loaded):
            prev = (f"{loaded[i - 1][0]}.html", loaded[i - 1][1]) if i > 0 else None
            nxt = (f"{loaded[i + 1][0]}.html", loaded[i + 1][1]) if i < len(loaded) - 1 else None
            fname = f"{slug}.html"
            (section_dir / fname).write_text(
                article_page(
                    section_id=section_id,
                    title=title,
                    description=desc,
                    canonical_path=f"/static-blog/{section_id}/{fname}",
                    depth=1,
                    crumbs=[("Home", "../index.html"), (meta["title"], "index.html"), (title, None)],
                    body=expand_body(body, 1),
                    jargon=jargon,
                    nav_html=nav_pair(prev, nxt),
                ),
                encoding="utf-8",
            )
            paths.append(f"{section_id}/{fname}")
    return paths


def write_home(counts: dict[str, int]) -> None:
    total = sum(counts.values())
    path_items = "".join(
        f'<li><a href="agentic-development/steps/{s["slug"]}.html">'
        f'<span class="path-num">{i:02d}</span><span class="path-title">{esc(step_label(s["title"]))}</span></a></li>'
        for i, s in enumerate(AGENTIC_STEPS, 1)
    )
    columns = []
    for gtitle, items in TOPIC_GROUPS:
        lis = "".join(
            f'<li><a href="{sid}/index.html"><span class="topic-name">{esc(title)}</span>'
            f'<span class="topic-desc">{esc(desc)}</span>'
            f'<span class="topic-count">{counts.get(sid, 0)} articles</span></a></li>'
            for sid, title, desc in items
        )
        columns.append(f'<div><h3 class="group-title">{esc(gtitle)}</h3><ul>{lis}</ul></div>')
    columns_html = "".join(columns)

    about_name = f"I'm {esc(AUTHOR_NAME)}, an {AUTHOR_ROLE}." if AUTHOR_NAME else f"These notes are written by an {AUTHOR_ROLE}."
    portrait_alt = f"Portrait of {esc(AUTHOR_NAME)}" if AUTHOR_NAME else "Portrait of the author"
    main = f"""<section class="hero grid-paper" aria-labelledby="hero-title">
  <div class="hero-inner">
    <div>
      <h1 id="hero-title">Building agentic systems that survive production</h1>
      <p class="hero-lede">Practical notes on orchestration graphs, MongoDB data planes, retrieval, evaluation and tracing, for engineers shipping copilots and tool-using agents.</p>
      <div class="hero-actions">
        <a class="button primary" href="agentic-development/index.html">Start the 20-step path</a>
        <a class="button secondary" href="#topics">Browse all topics</a>
      </div>
      <ul class="hero-facts">
        <li><strong>{total}</strong> articles</li>
        <li><strong>{len(TOPIC_INFO)}</strong> topics</li>
        <li>Free and open on <a href="{REPO_URL}">GitHub</a></li>
      </ul>
    </div>
    <figure class="portrait">
      <div class="portrait-frame">
        <img class="photo-duo" src="assets/images/author/portrait-duotone.jpg" alt="{portrait_alt}" width="720" height="900" fetchpriority="high">
        <img class="photo-color" src="assets/images/author/portrait.jpg" alt="" width="720" height="900" loading="lazy">
      </div>
      <figcaption class="trace-card" aria-label="An example agent trace">
        <p>chat-turn &middot; 2.8 s</p>
        <ol>
          <li><span>route</span><span class="bar"><i style="--start:0%;--len:12%;--delay:.2s"></i></span><span class="ms">0.3s</span></li>
          <li><span>plan</span><span class="bar"><i style="--start:12%;--len:30%;--delay:.35s"></i></span><span class="ms">0.9s</span></li>
          <li class="child tool"><span>invoke</span><span class="bar"><i style="--start:42%;--len:9%;--delay:.5s"></i></span><span class="ms">0.2s</span></li>
          <li><span>plan</span><span class="bar"><i style="--start:51%;--len:21%;--delay:.65s"></i></span><span class="ms">0.6s</span></li>
          <li><span>compose</span><span class="bar"><i style="--start:72%;--len:28%;--delay:.8s"></i></span><span class="ms">0.8s</span></li>
        </ol>
      </figcaption>
    </figure>
  </div>
</section>

<section class="home-section" aria-labelledby="path-title">
  <div class="section-head">
    <div>
      <h2 id="path-title">The 20-step path</h2>
      <p>One lesson at a time, from the first architecture decision to a tested, traceable agent.</p>
    </div>
    <a href="agentic-development/index.html">See every step with summaries</a>
  </div>
  <ol class="path-list">{path_items}</ol>
</section>

<section class="home-section" id="topics" aria-labelledby="topics-title">
  <div class="section-head">
    <div>
      <h2 id="topics-title">Topics</h2>
      <p>Deeper dives, grouped by what you are working on.</p>
    </div>
  </div>
  <div class="topic-columns">{columns_html}</div>
</section>

<section class="home-section" id="about" aria-labelledby="about-title">
  <div class="about">
    <img src="assets/images/author/avatar.jpg" alt="" width="96" height="96" loading="lazy">
    <div>
      <h2 id="about-title">About these notes</h2>
      <p>{about_name} I build assistants that plan, call real business APIs and keep conversations consistent under load. This site collects what worked, what broke, and the patterns I would use again.</p>
      <p>Examples stay generic so you can map them to your own stack. The site is plain HTML and CSS, with no tracking and no ads. The source is on <a href="{REPO_URL}">GitHub</a>.</p>
    </div>
  </div>
</section>"""
    schema = {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": SITE_NAME,
        "url": SITE_URL + "/",
        "description": "Practical notes on building agentic AI systems: orchestration graphs, MongoDB patterns, RAG, evaluation and tracing.",
        "author": author_schema(),
    }
    (ROOT / "index.html").write_text(
        document(
            title=SITE_NAME,
            full_title=f"{SITE_NAME}: building agentic AI systems that survive production",
            description="Practical notes on building agentic AI systems: orchestration graphs, MongoDB patterns, RAG, evaluation and tracing.",
            canonical_path="/static-blog/",
            depth=0,
            main=main,
            current=None,
            schema=schema,
            og_type="website",
        ),
        encoding="utf-8",
    )


def write_404() -> None:
    # GitHub Pages serves 404.html for a missing path at any depth, so links here are absolute.
    base = SITE_URL
    page = document(
        title="Page not found",
        description="This page does not exist.",
        canonical_path="/static-blog/404.html",
        depth=0,
        main=f"""<div class="not-found">
  <h1>That page isn't here</h1>
  <p>The link may be old or mistyped. Try the <a href="{base}/">home page</a> or start with the <a href="{base}/agentic-development/index.html">20-step path</a>.</p>
</div>""",
        current=None,
        schema={"@context": "https://schema.org", "@type": "WebPage", "name": "Page not found"},
        og_type="website",
    )
    page = page.replace('href="assets/', f'href="{base}/assets/').replace('src="assets/', f'src="{base}/assets/')
    page = page.replace('href="index.html', f'href="{base}/index.html').replace('href="agentic-development/', f'href="{base}/agentic-development/')
    page = re.sub(r'href="(graph-orchestration|data-patterns|build-guides|llm-engineering|prompts-tools|rag-knowledge|evaluation|langfuse-lab|testing-ai-dev|security-ai)/', rf'href="{base}/\1/', page)
    page = page.replace('href="sitemap.xml"', f'href="{base}/sitemap.xml"')
    page = page.replace('<meta name="robots" content="index, follow">', '<meta name="robots" content="noindex">')
    (ROOT / "404.html").write_text(page, encoding="utf-8")


def write_sitemap(paths: list[str]) -> None:
    from datetime import date
    today = date.today().isoformat()
    urls = "\n".join(
        f"  <url><loc>{SITE_URL}/{p.removesuffix('index.html')}</loc><lastmod>{today}</lastmod></url>"
        for p in paths
    )
    (ROOT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{urls}\n</urlset>\n",
        encoding="utf-8",
    )


def write_robots() -> None:
    (ROOT / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n",
        encoding="utf-8",
    )


def main() -> None:
    paths: list[str] = []
    paths.extend(write_agentic_pages())
    other = write_other_sections()
    paths.extend(other)
    counts = {"agentic-development": len(AGENTIC_STEPS)}
    for p in other:
        sid, name = p.split("/", 1)
        if name != "index.html":
            counts[sid] = counts.get(sid, 0) + 1
    write_home(counts)
    write_404()
    write_sitemap(["index.html"] + paths)
    write_robots()
    (ROOT / ".nojekyll").write_text("", encoding="utf-8")
    print(f"Generated {len(paths) + 2} pages under {ROOT}")


if __name__ == "__main__":
    main()
