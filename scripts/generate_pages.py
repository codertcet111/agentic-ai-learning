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


def figure_img(depth: int, filename: str, alt: str, caption: str) -> str:
    prefix = "../" * depth
    path = f"{prefix}assets/images/langfuse/{html.escape(filename)}"
    return f"""<figure class="screenshot-figure">
  <a href="{path}" class="screenshot-link" target="_blank" rel="noopener noreferrer">
    <img src="{path}" alt="{html.escape(alt)}" loading="lazy" decoding="async" width="1280" height="720">
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


def page_shell(
    *,
    title: str,
    description: str,
    canonical_path: str,
    depth: int,
    breadcrumb: str,
    body: str,
    jargon: dict[str, str],
    extra_head: str = "",
    visual: str | None = "graph",
    show_meta: bool = False,
) -> str:
    prefix = "../" * depth
    visual_html = (
        f'<div data-visual="{html.escape(visual)}"></div>' if visual else ""
    )
    jargon_html = ""
    if jargon:
        items = "".join(
            f"<dt>{html.escape(k)}</dt><dd>{html.escape(v)}</dd>"
            for k, v in jargon.items()
        )
        jargon_html = f"""
<section class="jargon" aria-labelledby="jargon-heading">
  <h2 id="jargon-heading">Terms on this page</h2>
  <dl>{items}</dl>
</section>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)} | Agentic Field Notes</title>
  <meta name="description" content="{html.escape(description)}">
  <meta name="author" content="AI Application Developer">
  <meta name="robots" content="index, follow">
  <link rel="canonical" href="{html.escape(SITE_URL + canonical_path.replace('/static-blog', '', 1))}">
  <meta property="og:url" content="{html.escape(SITE_URL + canonical_path.replace('/static-blog', '', 1))}">
  <meta property="og:title" content="{html.escape(title)}">
  <meta property="og:description" content="{html.escape(description)}">
  <meta property="og:type" content="article">
  <link rel="stylesheet" href="{prefix}assets/css/site.css">
  <script type="application/ld+json">
  {{"@context":"https://schema.org","@type":"TechArticle","headline":"{html.escape(title)}","description":"{html.escape(description)}","author":{{"@type":"Person","name":"AI Application Developer"}}}}
  </script>
  {extra_head}
</head>
<body>
  <a class="skip-link" href="#main">Skip to content</a>
  <header class="site-header" id="site-header"></header>
  <main id="main">
    <nav class="breadcrumb" aria-label="Breadcrumb">{breadcrumb}</nav>
    <article class="prose" itemscope itemtype="https://schema.org/TechArticle">
      <header class="article-header">
        <h1 itemprop="headline">{html.escape(title)}</h1>
        <p class="lead" itemprop="description">{html.escape(description)}</p>
        {f'<p class="meta">{reading_time(body)} min read</p>' if show_meta else ''}
      </header>
      {visual_html}
      {body}
      {jargon_html}
    </article>
  </main>
  <footer class="site-footer" id="site-footer"></footer>
  <script src="{prefix}assets/js/site.js" defer></script>
  <script src="{prefix}assets/js/visuals.js" defer></script>
</body>
</html>
"""


def write_agentic_pages() -> list[str]:
    paths: list[str] = []
    section_dir = ROOT / "agentic-development"
    section_dir.mkdir(parents=True, exist_ok=True)

    # index
    steps_html = "".join(
        f'<li><a href="steps/{s["slug"]}.html"><span class="step-num">{i:02d}</span>'
        f'<span>{html.escape(s["title"])}</span></a></li>'
        for i, s in enumerate(AGENTIC_STEPS, 1)
    )
    index_body = f"""
<p>This tab is a twenty-step path from blank repo to production agentic backend. Examples stay generic—a fictional HR, billing, or inventory domain—so you can map the ideas to your stack.</p>
<p>Steps reflect patterns used in modern orchestration services: Mongo for truth, Redis for cache, LangGraph for flow, LiteLLM for models, golden JSON for evals, and strict auth boundaries.</p>
<ul class="step-list">{steps_html}</ul>
"""
    index_path = section_dir / "index.html"
    index_path.write_text(
        page_shell(
            title="Agentic Development — 20 Steps",
            description="A twenty-page path to designing and shipping an agentic orchestration backend.",
            canonical_path="/static-blog/agentic-development/",
            depth=1,
            breadcrumb='<a href="../index.html">Home</a> / Agentic Development',
                body=index_body,
            jargon={
                "Agentic backend": "Service that orchestrates LLM turns, tools, and chat state.",
                "Orchestration": "Coordination of model calls and tools without owning business rules.",
            },
            visual=None,
        ),
        encoding="utf-8",
    )
    paths.append("agentic-development/index.html")

    steps_dir = section_dir / "steps"
    steps_dir.mkdir(exist_ok=True)
    for i, step in enumerate(AGENTIC_STEPS, 1):
        prev_slug = AGENTIC_STEPS[i - 2]["slug"] if i > 1 else None
        next_slug = AGENTIC_STEPS[i]["slug"] if i < len(AGENTIC_STEPS) else None
        nav = ""
        if prev_slug:
            nav += f'<a href="{prev_slug}.html">← Previous</a> · '
        if next_slug:
            nav += f'<a href="{next_slug}.html">Next →</a>'
        art_desc, art_body = load_article("agentic-development", step["slug"])
        dev = AGENTIC_DEV_NOTES.get(step["slug"], "")
        dev_html = (
            f'<div class="callout dev-pov"><strong>Developer POV:</strong> {html.escape(dev)}</div>'
            if dev
            else ""
        )
        body = (art_body or step["body"]) + dev_html + (f'<p class="meta">{nav}</p>' if nav else "")
        fname = f"steps/{step['slug']}.html"
        (section_dir / fname).write_text(
            page_shell(
                title=step["title"],
                description=art_desc or step["desc"],
                canonical_path=f"/static-blog/agentic-development/{fname}",
                depth=2,
                breadcrumb=(
                    '<a href="../../index.html">Home</a> / '
                    '<a href="../index.html">Agentic Development</a> / '
                    f"Step {i}"
                ),
                body=body,
                jargon=step["jargon"],
                visual="graph",
                show_meta=True,
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
        pages = meta["pages"]
        descs = {}
        bodies = {}
        for slug, title, _, body, _ in pages:
            d, b = load_article(section_id, slug)
            descs[slug] = d or title
            bodies[slug] = b or body
        links = "".join(
            f'<li><a href="{slug}.html"><span class="step-num">{i:02d}</span>'
            f'<span><strong>{html.escape(title)}</strong><br><small>{html.escape(descs[slug])}</small></span></a></li>'
            for i, (slug, title, _, _, _) in enumerate(pages, 1)
        )
        index_body = f'<p>{meta["index_intro"]}</p><ul class="step-list">{links}</ul>'
        index_path = section_dir / "index.html"
        index_path.write_text(
            page_shell(
                title=meta["title"],
                description=meta["index_intro"],
                canonical_path=f"/static-blog/{section_id}/",
                depth=1,
                breadcrumb=f'<a href="../index.html">Home</a> / {html.escape(meta["title"])}',
                body=index_body,
                jargon={},
                visual=None,
            ),
            encoding="utf-8",
        )
        paths.append(f"{section_id}/index.html")

        for i, (slug, title, visual, _, jargon) in enumerate(pages):
            fname = f"{slug}.html"
            body_html = expand_body(bodies[slug], 1)
            nav = []
            if i > 0:
                p_slug, p_title = pages[i - 1][0], pages[i - 1][1]
                nav.append(f'<a href="{p_slug}.html">← {html.escape(p_title)}</a>')
            if i < len(pages) - 1:
                n_slug, n_title = pages[i + 1][0], pages[i + 1][1]
                nav.append(f'<a href="{n_slug}.html">{html.escape(n_title)} →</a>')
            if nav:
                body_html += f'<nav class="post-nav" aria-label="More in this section">{"".join(nav)}</nav>'
            (section_dir / fname).write_text(
                page_shell(
                    title=title,
                    description=descs[slug],
                    canonical_path=f"/static-blog/{section_id}/{fname}",
                    depth=1,
                    breadcrumb=(
                        f'<a href="../index.html">Home</a> / '
                        f'<a href="index.html">{html.escape(meta["title"])}</a> / '
                        f"{html.escape(title)}"
                    ),
                    body=body_html,
                    jargon=jargon,
                    visual=visual,
                    show_meta=True,
                ),
                encoding="utf-8",
            )
            paths.append(f"{section_id}/{fname}")
    return paths


def write_home() -> None:
    cards = """
<div class="grid">
  <a class="card" href="agentic-development/index.html">
    <div class="card-visual" data-visual="graph"></div>
    <h2>Agentic Development</h2>
    <p>Twenty steps from boundary drawing to golden evals.</p>
  </a>
  <a class="card" href="graph-orchestration/index.html">
    <div class="card-visual" data-visual="graph"></div>
    <h2>Graph &amp; Orchestration</h2>
    <p>Routing, checkpoints, multi-agent handoffs.</p>
  </a>
  <a class="card" href="data-patterns/index.html">
    <div class="card-visual" data-visual="data"></div>
    <h2>Mongo for AI</h2>
    <p>Schemas for chat, forms, usage, and vectors.</p>
  </a>
  <a class="card" href="rag-knowledge/index.html">
    <div class="card-visual" data-visual="rag"></div>
    <h2>RAG &amp; Knowledge</h2>
    <p>Chunking, tool-based retrieval, ACL.</p>
  </a>
  <a class="card" href="evaluation/index.html">
    <div class="card-visual" data-visual="eval"></div>
    <h2>Eval &amp; Observability</h2>
    <p>Golden cases, traces, judge models.</p>
  </a>
  <a class="card" href="build-guides/index.html">
    <div class="card-visual" data-visual="default"></div>
    <h2>Build Guides</h2>
    <p>Feature slices, writes, local dev, cost.</p>
  </a>
  <a class="card" href="langfuse-lab/index.html">
    <div class="card-visual" data-visual="eval"></div>
    <h2>Langfuse Lab</h2>
    <p>Traces, per-node cost, tokens, failures, alerts.</p>
  </a>
  <a class="card" href="llm-engineering/index.html">
    <div class="card-visual" data-visual="default"></div>
    <h2>LLM Engineering</h2>
    <p>LiteLLM, stubs, windows, model routing.</p>
  </a>
  <a class="card" href="prompts-tools/index.html">
    <div class="card-visual" data-visual="graph"></div>
    <h2>Prompts &amp; Tools</h2>
    <p>Capability cards, planner policy, compose.</p>
  </a>
  <a class="card" href="security-ai/index.html">
    <div class="card-visual" data-visual="eval"></div>
    <h2>Security for AI</h2>
    <p>Auth forwarding, writes, eval signing.</p>
  </a>
  <a class="card" href="testing-ai-dev/index.html">
    <div class="card-visual" data-visual="data"></div>
    <h2>Testing as an AI Dev</h2>
    <p>Graph specs, fakes, golden runner, tracing tests.</p>
  </a>
</div>
"""
    body = f"""
<section class="hero">
  <canvas id="hero-canvas" class="hero-canvas" aria-hidden="true"></canvas>
  <div class="hero-content">
    <p class="hero-tagline">Static field notes</p>
    <h1>Building agentic systems that survive production</h1>
    <p class="lead">Practical essays on orchestration graphs, Mongo data planes, RAG, and evaluation—written by an AI application developer for engineers shipping copilots and tool-using agents.</p>
  </div>
</section>
<p>This site is plain HTML, CSS, and JavaScript: mobile-friendly, crawler-readable, and free of stock image CDNs. Diagrams are generated in the browser with canvas and SVG.</p>
<h2>Explore by topic</h2>
{cards}
<h2>What you will find here</h2>
<ul>
  <li><strong>Agentic Development</strong> (tab 2) — twenty linked lessons mirroring a real orchestration codebase without vendor-specific examples.</li>
  <li>Deep dives on LangGraph-style pipelines, turn admission, catalog merging, and bilingual compose.</li>
  <li>Mongo schema recipes for chat, pending forms, failures, and retrieval metadata.</li>
  <li>Evaluation patterns: golden JSON, stub LLMs, trace diffs, and observability glue.</li>
  <li><strong>Langfuse Lab</strong> — screenshot-guided tours of traces, span trees, token/cost panels, turn budgets, and masking alerts.</li>
  <li>LLM engineering, prompts &amp; tools, security, and testing tabs written from a day-to-day AI developer perspective.</li>
</ul>
<p>Open-source orchestration repos and internal architecture wikis informed the outline; content is generalized so you can adapt it to any domain API.</p>
"""
    (ROOT / "index.html").write_text(
        page_shell(
            title="Agentic Field Notes",
            description="SEO-friendly static blog on agentic AI development, graphs, Mongo, RAG, and evals.",
            canonical_path="/static-blog/",
            depth=0,
            breadcrumb="Home",
            body=body,
            jargon={
                "Agentic system": "Software where an LLM plans actions against tools with persisted state.",
                "Static site": "Pre-built HTML pages served without a server-side renderer.",
                "SEO": "Search engine optimization via semantic markup, meta tags, and sitemaps.",
            },
            extra_head='<meta property="og:type" content="website">',
            visual=None,
        ).replace(
            '<script src="assets/js/visuals.js" defer></script>',
            '<script src="assets/js/hero-canvas.js" defer></script>\n  <script src="assets/js/visuals.js" defer></script>',
        ),
        encoding="utf-8",
    )


def write_sitemap(paths: list[str]) -> None:
    urls = "\n".join(
        f"  <url><loc>{SITE_URL}/{p.removesuffix('index.html')}</loc></url>"
        for p in paths if p != "index.html"
    )
    (ROOT / "sitemap.xml").write_text(
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"  <url><loc>{SITE_URL}/</loc></url>\n"
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
    paths.extend(write_other_sections())
    write_home()
    write_sitemap(["index.html"] + paths)
    write_robots()
    (ROOT / ".nojekyll").write_text("", encoding="utf-8")
    print(f"Generated {len(paths) + 1} pages under {ROOT}")


if __name__ == "__main__":
    main()
