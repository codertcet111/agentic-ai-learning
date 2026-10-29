"""Extra blog sections: Langfuse lab, LLM engineering, security, testing — dev POV."""

from __future__ import annotations

# (slug, title, visual, body_html, jargon dict)
# Body uses placeholders: {{IMG_TRACES_LIST}}, {{IMG_SPAN_TREE}}, {{IMG_TRACE_DETAIL}}

LANGFUSE_SECTION = {
    "title": "Langfuse Lab",
    "index_intro": "Developer walkthrough of LLM traces: failures, span trees, token cost per node, turn checks, and privacy-safe export.",
    "pages": [
        (
            "dev-workflow",
            "Langfuse workflow for AI developers",
            "eval",
            """
<p>When you ship an agentic backend, logs alone are not enough. You need <strong>one trace per user turn</strong> that shows routing, each graph step, every LLM call, and every tool invoke—with latency, token usage, and cost rolled up.</p>
<h2>What I wire before debugging prompts</h2>
<ol>
  <li>Enable tracing in non-production with <code>structure</code> capture first (names, shapes, counts—no raw user text).</li>
  <li>Tag traces with environment, release, conversation id, and request id so support can jump from JSON logs to Langfuse.</li>
  <li>Name observations consistently: root turn, router, agent step, <code>llm.call</code>, <code>capability.invoke</code>.</li>
  <li>Run golden evals with a signing header so CI traces land in the same project for comparison.</li>
</ol>
<div class="callout"><strong>Dev tip:</strong> Correlate <code>X-Request-Id</code> from API logs with the trace id in Langfuse before you touch prompt wording.</div>
""",
            {
                "Observation": "Langfuse unit inside a trace (span-like) with type generation, tool, or agent.",
                "Structure capture": "Tracing mode that records metadata and shapes without free-text payloads.",
                "Turn": "One user message handled end-to-end, usually one root trace.",
            },
        ),
        (
            "traces-list-and-errors",
            "Traces list: spot failures and slow turns",
            "eval",
            """
<p>The <strong>Tracing</strong> table is your shift dashboard. Filter by environment, time range, and status before you open a single trace.</p>
{{IMG_TRACES_LIST}}
<h2>How to read this screen</h2>
<ul>
  <li><strong>Status icons</strong> — Red marks failed turns (upstream 4xx/5xx, graph exceptions, validation failures). Yellow often means partial success or scored warnings. Green is a clean completion.</li>
  <li><strong>Latency column</strong> — Sort descending to find p95 offenders after a deploy. Compare against your <code>turn_check_max_turn_seconds</code> budget.</li>
  <li><strong>Token / cost columns</strong> — When model prices are configured in Langfuse, cost is computed per trace. Use this to catch runaway planner loops (many LLM observations on one turn).</li>
  <li><strong>Search</strong> — Paste <code>conversation_id</code>, <code>request_id</code>, or trace id from structured logs.</li>
</ul>
<h2>What I do as a developer</h2>
<p>After each release I scan errors for 15 minutes: group by observation name. If <code>plan_next_step</code> failures spike, the catalog or schema changed—not necessarily the model. If <code>capability.invoke</code> fails, I check provider circuit breakers and sandbox auth.</p>
<p>Configure Langfuse <strong>notifications</strong> (Slack/email) on error-rate thresholds for the <code>development</code> project so regressions surface before QA files tickets.</p>
""",
            {
                "Trace status": "Langfuse rollup of whether the root observation ended in error.",
                "Error rate": "Percentage of traces with failed observations in a time window.",
            },
        ),
        (
            "span-tree-and-nodes",
            "Span tree: cost and time per graph node",
            "eval",
            """
<p>Open a trace and switch to the <strong>tree view</strong>. Each row is an observation; indentation is parent/child timing. This is how you prove which <em>node</em> burned budget.</p>
{{IMG_SPAN_TREE}}
<h2>Reading the tree (developer checklist)</h2>
<ul>
  <li><strong>Root</strong> — Usually named like <code>chat-turn</code> / <code>answer-chat-turn</code>. Total duration and total cost should match the list view.</li>
  <li><strong>Router</strong> — <code>route-request</code> or direct-recipe paths. If this is huge, routing prompt or catalog size grew.</li>
  <li><strong>Agent steps</strong> — One observation per sub-agent step; children hold LLM and tool calls for that step only.</li>
  <li><strong>LLM rows</strong> — Look at token chips on each generation observation. Multiple planner calls in one turn often mean ambiguous user input or missing lookup results.</li>
  <li><strong>Tool rows</strong> — <code>capability.invoke</code> latency separates network slowness from model slowness.</li>
</ul>
<h2>Why per-node cost matters</h2>
<p>Product asks “why is this chat expensive?” You expand the tree, sort children by cost, and point to the exact planner + compose pair—or an extra retrieval call. That drives engineering fixes (cache catalog, shrink tool list, add direct recipes) instead of blanket model downgrades.</p>
""",
            {
                "Span tree": "Hierarchical view of observations ordered by execution time.",
                "Generation observation": "Langfuse type for an LLM call with input/output token counts.",
            },
        ),
        (
            "trace-detail-io-and-tokens",
            "Trace detail: IO, tokens, and model metadata",
            "eval",
            """
<p>The right-hand detail pane is where you debug <strong>what the model actually saw</strong> (subject to capture mode and masking).</p>
{{IMG_TRACE_DETAIL}}
<h2>Fields I inspect every time</h2>
<ul>
  <li><strong>Input / Output</strong> — Structured JSON for planner/compose calls. Validate against your Pydantic schema expectations.</li>
  <li><strong>Token breakdown</strong> — Input vs output vs cache-read tokens. Rising input tokens often mean bloated capability cards or transcript window.</li>
  <li><strong>Cost</strong> — Per-observation USD when prices are set. Sum mentally: planner + resolver LLM + compose should fit product budget.</li>
  <li><strong>Metadata</strong> — Model id, purpose (<code>plan</code>, <code>compose</code>, <code>route</code>), capability id on tool spans.</li>
  <li><strong>Scores</strong> — Turn-end checks may attach scores (latency budget, call count, cost ceiling). Failed scores highlight yellow in the UI.</li>
</ul>
<h2>Capture modes (dev vs compliance)</h2>
<p><code>structure</code> — safest default: shapes and counts. <code>masked</code> — text with entity pseudonyms for debugging phrasing. Never enable raw content in production without DPO approval; residual PII triggers Rollbar alerts from the masking exporter.</p>
""",
            {
                "Cache-read tokens": "Tokens served from provider prompt cache, usually cheaper.",
                "Turn score": "Numeric flag Langfuse stores on a trace after automated checks.",
            },
        ),
        (
            "turn-checks-and-budgets",
            "Turn checks: automated budgets on every trace",
            "eval",
            """
<p>Server-side <strong>turn checks</strong> run when a trace completes. They turn observability into guardrails.</p>
<h2>Typical limits (configure per environment)</h2>
<ul>
  <li>Max LLM calls per turn — catches planner loops.</li>
  <li>Max wall-clock seconds — catches hung upstream calls.</li>
  <li>Slow LLM call threshold — flags individual generations.</li>
  <li>Max cost USD — only when input/output price per MTok is configured (otherwise the check is skipped to avoid lying).</li>
  <li>Max reply characters — prevents huge compose payloads hitting mobile clients.</li>
</ul>
<p>Failed checks appear as Langfuse scores and in structured logs. In development, treat a failed cost score as a merge blocker for prompt changes that add tools.</p>
<div class="callout">Pair turn checks with golden evals: checks catch runaway behavior; golden cases catch wrong capability choice.</div>
""",
            {
                "Turn check": "Automated policy evaluated on TurnFacts after a chat turn.",
                "MTok": "Millions of tokens; pricing unit for many model APIs.",
            },
        ),
        (
            "masking-alerts-and-failures",
            "Masking residuals, failures, and Rollbar alerts",
            "eval",
            """
<p>Exports pass through a <strong>masking exporter</strong> that scans for emails, phone patterns, and identifiers. If anything survives masking, a throttled Rollbar alert fires with span name and <em>kinds</em> of data—not the values.</p>
<h2>Failure reasons on the root trace</h2>
<ul>
  <li><code>run_timeout</code> — Turn exceeded wall clock.</li>
  <li><code>graph_error</code> — Unhandled exception inside the graph.</li>
  <li><code>run_failed</code> — Business failure handled in-band (denied capability, validation).</li>
  <li><code>cancelled</code> — User or system cancelled an in-progress turn.</li>
</ul>
<p>When debugging, filter traces by <code>failure_reason</code> metadata if your instrumentation sets it. Cross-link to Mongo <code>failure_records</code> for support-facing sanitized detail.</p>
""",
            {
                "Residual alert": "Warning that masking missed a class of sensitive data on export.",
                "In-band failure": "Expected error returned as a structured result, not an exception.",
            },
        ),
        (
            "local-setup-checklist",
            "Local Langfuse setup checklist",
            "eval",
            """
<pre><code># Example env (prefix per your settings class)
AGENTIC_LANGFUSE_ENABLED=true
AGENTIC_LANGFUSE_PUBLIC_KEY=pk-lf-...
AGENTIC_LANGFUSE_SECRET_KEY=sk-lf-...
AGENTIC_LANGFUSE_BASE_URL=https://cloud.langfuse.com
AGENTIC_LANGFUSE_ENVIRONMENT=development
AGENTIC_LANGFUSE_CAPTURE=structure
AGENTIC_LANGFUSE_PSEUDONYM_KEY=&lt;random secret&gt;</code></pre>
<p>Use EU or US base URL consistently. Do not set unprefixed <code>LANGFUSE_*</code> env vars if your stack also runs LiteLLM—duplicate config can send spans to the wrong region.</p>
<p>Send one chat message locally, open Tracing, confirm a new trace within seconds. If not, check lifespan logs for <code>langfuse_disabled_reason</code>.</p>
""",
            {
                "Pseudonym key": "Secret used to HMAC user/tenant placeholders in masked capture.",
                "Disabled reason": "Human-readable cause when tracing did not start.",
            },
        ),
    ],
}

LLM_ENGINEERING = {
    "title": "LLM Engineering",
    "index_intro": "Day-to-day model integration: LiteLLM, structured outputs, stubs, and routing—from an implementer's chair.",
    "pages": [
        (
            "litellm-gateway",
            "LiteLLM as a single gateway",
            "default",
            """
<p>Point every model call through one client. Swap Bedrock, OpenAI-compatible, or Azure endpoints with config—not refactors. Centralize timeouts, retries, and token accounting hooks that feed Langfuse.</p>
<p><strong>Dev workflow:</strong> define model aliases in settings; never hardcode ARNs in graph nodes. Feature-flag new models per environment.</p>
""",
            {"LiteLLM": "Library that unifies many LLM providers behind one API.", "Model alias": "Config key resolving to provider + model id."},
        ),
        (
            "structured-outputs",
            "Structured outputs in production",
            "default",
            """
<p>Bind each prompt to a Pydantic model. Validate JSON strictly; on failure, retry once with a repair prompt or fail safe to a user-facing apology—never pass unvalidated dicts to <code>invoke_capability</code>.</p>
""",
            {"Repair prompt": "Follow-up LLM call asking for schema-compliant JSON only.", "Schema drift": "When prompt examples no longer match the Pydantic model."},
        ),
        (
            "llm-stub-ci",
            "LLM_STUB and deterministic CI",
            "default",
            """
<p><code>LLM_STUB=true</code> returns canned structured responses so graph tests prove routing and persistence without API keys. Keep stub payloads in sync with schema versions using shared fixtures.</p>
""",
            {"Stub": "Test double replacing the network LLM.", "Fixture": "Frozen JSON used by tests and stubs."},
        ),
        (
            "token-window-management",
            "Token window management",
            "default",
            """
<p>Trim transcript windows by sequence, summarize older turns offline, or pass retrieval snippets instead of full policy PDFs. Measure input tokens per observation in Langfuse after each change.</p>
""",
            {"Context window": "Maximum tokens the model accepts per request.", "Summarization": "Compressing older turns into a short memory block."},
        ),
        (
            "model-routing",
            "When to use small vs large models",
            "default",
            """
<p>Route classification and argument filling to smaller models; reserve large models for compose and nuanced planning. Log <code>purpose</code> on each LLM observation so you can prove the split in traces.</p>
""",
            {"Routing": "Choosing model tier per LLM purpose.", "Purpose tag": "Metadata naming plan vs compose vs route."},
        ),
        (
            "streaming-dev",
            "Streaming responses to the client",
            "default",
            """
<p>Stream tokens only after admission succeeds and the turn ledger marks in-progress. Cancel streams when the user aborts; reconcile ledger state so retries do not double-charge tools.</p>
""",
            {"SSE": "Server-sent events transport often used for token streams.", "Abort": "Client signal to stop generation mid-turn."},
        ),
    ],
}

PROMPT_TOOLS = {
    "title": "Prompts & Tools",
    "index_intro": "Designing planner prompts, capability cards, and tool schemas that models can actually follow.",
    "pages": [
        (
            "capability-cards",
            "Writing capability cards for planners",
            "graph",
            """
<p>Each tool needs a one-line identity, parameter docs, and side-effect class (read vs write). Keep lists under what your model reliably attends to—split domains across sub-agents instead of one megacatalog.</p>
""",
            {"Capability card": "Planner-facing description of one tool.", "Side-effect class": "Label indicating read-only vs mutating behavior."},
        ),
        (
            "planner-policy",
            "Planner policy without prompt soup",
            "graph",
            """
<p>Put non-negotiable rules in <code>AgentDefinition</code> policy modules, not scattered across nodes. State what to do, not only what to avoid. One home per rule prevents drift between English and Arabic compose.</p>
""",
            {"Policy module": "Central text defining graph behavior constraints.", "Prompt soup": "Duplicated conflicting instructions across files."},
        ),
        (
            "lookup-not-guess",
            "Lookups: enrich, don't auto-select",
            "graph",
            """
<p>When an id is required, call lookup, append results to trace, replan. Document this in the planner prompt so engineers do not shortcut in resolver code.</p>
""",
            {"Lookup trace": "Evidence list the planner uses to pick an entity id.", "Replan": "Second planning pass after new data arrives."},
        ),
        (
            "bilingual-compose",
            "Bilingual compose for developers",
            "graph",
            """
<p>Always populate en and ar fallback strings in compose output models. Test with locale headers in API integration tests, not only English unit tests.</p>
""",
            {"Compose": "LLM step that produces user-visible natural language.", "Locale header": "HTTP header selecting response language."},
        ),
    ],
}

SECURITY_AI = {
    "title": "Security for AI",
    "index_intro": "Threat models and patterns for auth-forwarding orchestrators.",
    "pages": [
        (
            "token-forwarding",
            "Token forwarding, never token storage",
            "default",
            """
<p>Middleware copies Access-Token into request context; providers attach per call. No cookies on shared httpx pools. Redact before logs, Mongo, Rollbar, and Langfuse.</p>
""",
            {"Token forwarding": "Passing the client auth header upstream unchanged.", "Cookie jar": "HTTP client store that must stay disabled on pools."},
        ),
        (
            "three-layer-authz",
            "Three-layer authorization",
            "default",
            """
<p>Planner sees advertised tools; orchestrator checks session capabilities; upstream enforces permissions. Document which layer blocked a invoke in trace metadata for support.</p>
""",
            {"Advertised": "Tools visible in planner context.", "Authorized": "Tools the principal may actually call."},
        ),
        (
            "write-confirmation",
            "Writes and explicit confirmation",
            "default",
            """
<p>Mutations require <code>explicit_action</code> and UI confirmation. Operation ids dedupe retries. Test double-submit in API tests.</p>
""",
            {"Explicit action": "Proof the user confirmed a dangerous tool.", "Dedupe": "Preventing duplicate side effects on retry."},
        ),
        (
            "eval-trace-signing",
            "Signed eval traces",
            "default",
            """
<p>CI runners use a signing key header to attach eval runs to experiment traces. Rotate keys; never ship signing keys to production clusters.</p>
""",
            {"Eval signing": "HMAC proving a trace belongs to automated eval traffic.", "Experiment": "Langfuse grouping of related eval traces."},
        ),
    ],
}

TESTING_AI_DEV = {
    "title": "Testing as an AI Dev",
    "index_intro": "pytest, fakes, and graph specs without flaking on real models.",
    "pages": [
        (
            "graph-executable-spec",
            "Graph tests as executable spec",
            "default",
            """
<p>Maintain one module that asserts routing, pending form resume, and supersede behavior. When product asks "what happens if…", point to a test name.</p>
""",
            {"Executable spec": "Tests that document required behavior.", "Supersede": "Replacing a pending form with a new user intent."},
        ),
        (
            "fakes-mongo-redis",
            "Fakes for Mongo and Redis",
            "default",
            """
<p>In-memory fakes implement repository interfaces. Never hit Docker Mongo in unit tests. Integration tests own the <code>integration</code> marker.</p>
""",
            {"Fake repository": "In-memory stand-in for persistence.", "Marker": "pytest tag excluding slow tests from default runs."},
        ),
        (
            "golden-runner-dev",
            "Running golden evals locally",
            "default",
            """
<p>Run the eval CLI against stub LLM for fast feedback; nightly job with real models and Langfuse compare. Tag cases <code>safety</code> vs <code>routing</code> for selective CI.</p>
""",
            {"Golden runner": "CLI executing JSON cases and reporting diffs.", "Nightly job": "Scheduled pipeline with live model credentials."},
        ),
        (
            "testing-observability",
            "Testing observability hooks",
            "default",
            """
<p>Assert spans are created with expected names using in-memory exporters. Test masking by feeding PII into payload helpers and expecting redaction.</p>
""",
            {"In-memory exporter": "Test double capturing spans without cloud upload.", "Hook": "Function emitting telemetry around LLM or tools."},
        ),
    ],
}

# Extra pages appended to existing sections (slug, title, visual, body, jargon)
GRAPH_EXTRA = [
    (
        "debugging-with-traces",
        "Debugging graph bugs with traces",
        "graph",
        """
<p>Reproduce locally, copy <code>request_id</code>, open Langfuse, walk the span tree. Compare node order to the previous release trace for the same golden case.</p>
""",
        {"Golden replay": "Re-running a fixed scenario to compare traces."},
    ),
    (
        "state-size",
        "Keeping GraphState small",
        "graph",
        """
<p>Store large tool results by reference in Mongo; keep state to ids and summaries. Large checkpoints slow resume and inflate export costs.</p>
""",
        {"Channel value": "Piece of graph state LangGraph merges between nodes."},
    ),
]

DATA_EXTRA = [
    (
        "turn-ledger-dev",
        "Turn ledger for developers",
        "data",
        """
<p>Every turn transitions <code>pending → running → completed|failed|cancelled</code>. Query by conversation id when Langfuse shows a hang—ledger beats guessing from checkpoints.</p>
""",
        {"Turn ledger": "Authoritative document for in-flight and finished turns."},
    ),
    (
        "idempotency-patterns",
        "Idempotency keys in chat APIs",
        "data",
        """
<p>Clients send idempotency keys on message append; partial unique indexes enforce uniqueness. Design APIs so mobile offline queues cannot fork transcripts.</p>
""",
        {"Idempotency": "Property where retries do not duplicate effects."},
    ),
]

RAG_EXTRA = [
    (
        "eval-retrieval",
        "Evaluating retrieval quality",
        "rag",
        """
<p>Label 50 questions with expected doc ids. Measure recall@k on the retrieval step alone before end-to-end answer eval—separates embedding issues from compose issues.</p>
""",
        {"Recall@k": "Whether the right doc appears in the top k chunks."},
    ),
]

EVAL_EXTRA = [
    (
        "langfuse-scores",
        "Langfuse scores from CI",
        "eval",
        """
<p>Attach scores for routing accuracy, tool correctness, and latency. Dashboard trend lines per release tag (<code>langfuse_release</code>).</p>
""",
        {"Score": "Numeric or boolean quality signal stored on a trace."},
    ),
]

BUILD_EXTRA = [
    (
        "incident-runbook",
        "On-call runbook for agentic APIs",
        "default",
        """
<p>1) Request id → logs 2) conversation id → Mongo transcript 3) trace id → Langfuse 4) failure_record → error class. Escalate provider outages separately from model quality regressions.</p>
""",
        {"Runbook": "Step list for incident response."},
    ),
]

IMAGE_PLACEHOLDERS = {
    "{{IMG_TRACES_LIST}}": "traces-list-errors.png",
    "{{IMG_SPAN_TREE}}": "trace-span-tree.png",
    "{{IMG_TRACE_DETAIL}}": "trace-detail-tokens-cost.png",
    "{{IMG_ALERTS}}": "langfuse-alerts.png",
    "{{IMG_SCORES}}": "langfuse-scores.png",
}

IMAGE_META = {
    "traces-list-errors.png": (
        "Langfuse Tracing view with the traces list, a selected turn's span tree and its attributes",
        "The Tracing view: filters and the traces list on the left, the selected chat turn's span tree and attributes on the right.",
    ),
    "trace-span-tree.png": (
        "Langfuse span tree for one chat turn with nested router, agent, LLM and tool observations",
        "One chat turn as a span tree: routing, the agent step, the planner call and two tool calls, each with its own time and cost.",
    ),
    "trace-detail-tokens-cost.png": (
        "Langfuse observation detail showing attributes and metadata including LLM calls and token counts",
        "The detail pane for the turn: environment, release, routing mode, number of LLM and tool calls, and input and output tokens.",
    ),
    "langfuse-alerts.png": (
        "Langfuse Alerts page with an alert rule for failed turns",
        "The Alerts page in Langfuse with a rule that fires on failed turns.",
    ),
    "langfuse-scores.png": (
        "Langfuse Scores table listing automated turn check results over time",
        "Scores written by automated turn checks, listed per trace with a histogram of values over time.",
    ),
}

AI_ESSENTIALS = {
    "title": "AI Engineer Essentials",
    "index_intro": "The fundamentals every AI engineer leans on: how LLMs behave, embeddings, when to fine-tune, MCP, serving, guardrails, memory, releases and privacy.",
    "pages": [
        ("llm-fundamentals", "How LLMs actually behave", "default", "",
         {"Token": "The unit a model reads and writes; roughly three quarters of an English word.",
          "Temperature": "Sampling setting that controls how random the next-token choice is.",
          "Hallucination": "Fluent output that is not supported by the input or by facts."}),
        ("embeddings-vector-search", "Embeddings and vector search", "rag", "",
         {"Embedding": "A list of numbers representing the meaning of a piece of text.",
          "ANN index": "Approximate nearest-neighbour index, such as HNSW, for fast similarity search.",
          "Reranker": "A model that reorders a short list of search results by relevance."}),
        ("prompt-rag-or-finetune", "Prompting, RAG or fine-tuning?", "default", "",
         {"Fine-tuning": "Further training a model on your own examples to change its behaviour.",
          "RAG": "Retrieval-augmented generation: fetching relevant text and giving it to the model."}),
        ("mcp-tool-interoperability", "MCP: connecting agents to tools", "graph", "",
         {"MCP": "Model Context Protocol, an open standard for connecting AI applications to tools and data.",
          "MCP server": "A program that exposes tools, resources or prompts to MCP clients."}),
        ("inference-latency-cost", "Inference: latency, throughput and cost", "default", "",
         {"TTFT": "Time to first token: how long before the reply starts appearing.",
          "KV cache": "Stored attention state that lets a model reuse work for earlier tokens.",
          "Quantization": "Storing model weights with fewer bits to save memory and speed up inference."}),
        ("guardrails-prompt-injection", "Guardrails and prompt injection", "eval", "",
         {"Prompt injection": "Text that tries to override an AI system's instructions.",
          "Least privilege": "Giving a component only the access it strictly needs."}),
        ("agent-memory", "Agent memory: short and long term", "graph", "",
         {"Working memory": "What the model sees in the current context window.",
          "Long-term memory": "Facts saved across conversations and retrieved when relevant."}),
        ("llmops-releases", "LLMOps: shipping prompt and model changes", "eval", "",
         {"Canary release": "Sending a small share of traffic to a new version before everyone.",
          "Prompt versioning": "Tracking prompt text like code, with history and rollbacks."}),
        ("privacy-responsible-ai", "Privacy and responsible AI in practice", "default", "",
         {"PII": "Personally identifiable information, such as names, emails and phone numbers.",
          "Data minimisation": "Collecting and keeping only the data a feature needs."}),
    ],
}

NEW_SECTIONS = [
    AI_ESSENTIALS,
    LANGFUSE_SECTION,
    LLM_ENGINEERING,
    PROMPT_TOOLS,
    SECURITY_AI,
    TESTING_AI_DEV,
]

AGENTIC_DEV_NOTES: dict[str, str] = {
    "01-orchestration-plane": "Before coding, list three APIs your agent will call—if any logic is not already in those APIs, move it there first.",
    "02-layered-architecture": "Draw imports on a whiteboard; any arrow from providers to agents is a bug.",
    "03-request-context": "Grep your codebase for token strings in GraphState or checkpoint tests—should return zero hits.",
    "04-sessions-conversations": "Integration-test conversation revision rejection before you ship mobile offline queue.",
    "05-turn-admission": "Simulate two parallel POSTs with the same idempotency key; only one graph run should win.",
    "06-mongo-collections-map": "Keep INDEX_SPECS as the single source of truth; drift between model and index causes silent prod failures.",
    "07-messages-transcripts": "Never UPDATE message documents; append-only makes replay and audit trivial.",
    "08-pending-interactions": "Add an API test where free text supersedes a pending form—users always do this in prod.",
    "09-capability-catalog": "Log catalog hash on each turn in traces; support can see if a user pinned an old tool list.",
    "10-providers-invoke": "Unit-test circuit breaker open path returns typed AppError, not raw httpx exceptions.",
    "11-langgraph-skeleton": "Compile graph once; if compile runs per request, you have a performance incident waiting.",
    "12-graph-nodes-flow": "Print the node sequence from Langfuse for a golden case and commit it as baseline documentation.",
    "13-typed-llm-schemas": "When schema changes, update stub LLM fixtures in the same PR or CI will lie.",
    "14-argument-resolution": "Code review rule: no resolver may set an entity id without lookup_trace entry.",
    "15-routing-recipes": "Add recipes for support macros before tuning planner temperature.",
    "16-presentation-modes": "Snapshot compose en/ar strings in tests when UI uses structured renderers.",
    "17-redis-cache-patterns": "Chaos-test with Redis stopped; chat must still admit turns correctly.",
    "18-observability-tracing": "Link Datadog APM (if used) with Langfuse via shared request_id in logs.",
    "19-rag-knowledge-hooks": "Measure retrieval recall before tuning compose prompts—bad chunks cannot be composed away.",
    "20-evaluation-golden-suite": "Tag at least five cases per mutating capability; writes are where incidents happen.",
}

SECTION_EXTRAS: dict[str, list] = {
    "graph-orchestration": GRAPH_EXTRA,
    "data-patterns": DATA_EXTRA,
    "rag-knowledge": RAG_EXTRA,
    "evaluation": EVAL_EXTRA,
    "build-guides": BUILD_EXTRA,
}
