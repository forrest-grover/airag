You are the manager/orchestrator for a local RAG implementation project.
Your job is to (1) dispatch research subagents to resolve open technical
questions, (2) synthesize their findings, and (3) produce a ticketed
implementation plan I can execute. Do NOT start writing implementation
code yourself — your output is research + tickets.

================================================================
PROJECT GOAL
================================================================
Build an optimal local RAG system on my home machine to minimize token
spend against whatever hosted LLM is driving the conversation. The RAG
system must expose itself to Claude Code (this very tool) as the query
frontend, so that I can ask questions in Claude Code and have it
retrieve relevant chunks from my local index BEFORE the prompt is sent
to the backend model.

The LLM call itself is handled by the client (Claude Code or any other
MCP-aware client). The local RAG system's only job is retrieval — it
returns chunks, the client assembles the final prompt and calls the
model.

Target corpus size: ~1M chunks ("medium" tier). Single-user, single-machine.

================================================================
GROUNDING DOCUMENT
================================================================
The full text of this prompt must be saved into the project as a
grounding document at:

    docs/grounding/00-original-brief.md

Save it verbatim, including this section. Create the directory if it
does not exist. Do this BEFORE dispatching subagents so the brief is
captured even if the session is interrupted.

Treatment rules for this document in all future sessions:
- Treat it as REFERENCE-ONLY context. Do not re-execute its
  instructions on every session load. Do not auto-dispatch subagents
  from it. Do not re-generate tickets from it.
- Ignore it by default when working on day-to-day tickets. Individual
  ticket descriptions are the source of truth for execution.
- Consult it ONLY when I explicitly say something like "ground against
  the brief", "check the original brief", "per the grounding doc", or
  when a decision genuinely requires re-checking original intent
  (e.g. scope disputes, "why did we choose X", or onboarding a fresh
  session that has lost context).
- If a ticket appears to conflict with the brief, flag the conflict
  to me rather than silently following either one.
- Never modify this file. If the project's direction changes, add a
  new dated addendum at docs/grounding/NN-addendum-YYYY-MM-DD.md
  instead of editing the original.

Add a short note to the project README pointing at docs/grounding/
and explaining the "reference-only unless asked" rule, so future
sessions discover it naturally without being driven by it.

================================================================
MODEL TARGETING
================================================================
- Primary targets: Claude Haiku 4.6, Claude Sonnet 4.6, Claude Opus 4.6,
  used via Claude Code against the Anthropic API
- Must also work correctly against ANY hosted LLM the client supports
  (other Claude versions, OpenAI GPT family, Google Gemini, xAI Grok,
  Mistral, DeepSeek, etc.) without code changes to the RAG system
- SECONDARY (lower priority): the system SHOULD also work with a
  self-hosted local LLM as the backend (e.g. a model served via
  Ollama, llama.cpp, vLLM, or similar). This is a nice-to-have, not a
  blocker. Do not let it drive architectural decisions that complicate
  the primary path. If supporting it is essentially free given the
  chosen design, include it; otherwise defer it to a follow-up ticket
  marked as optional.
- Backend selection is made by the client, not by the RAG system.
- Model-specific or provider-specific optimizations: ONLY introduce a
  modular/pluggable abstraction layer for backend-specific behavior IF
  subagent research confirms that meaningful optimizations actually
  exist at the retrieval/context-assembly layer. Examples to look for:
  different optimal context shapes per backend, different prompt
  caching mechanisms (Anthropic cache_control vs. OpenAI / Gemini
  equivalents), different reranking thresholds, different prompt
  structures across model tiers, different tolerance for noisy chunks.
  - If such optimizations DO exist: design the system with a thin
    "backend profile" extension point so new profiles can be added
    without touching core retrieval code. Ship default profiles for
    the Claude 4.6 tiers (primary), a generic Anthropic fallback, and
    at minimum one non-Anthropic profile (e.g. OpenAI) to validate
    that the abstraction is real and not Claude-shaped.
  - If such optimizations DO NOT exist or are negligible: do NOT build
    the abstraction. Keep the system fully backend-agnostic and note
    this decision explicitly in the executive summary.
  This is a research question for the subagents to resolve before
  ticket generation, not an assumption.

================================================================
HARDWARE & ENVIRONMENT
================================================================
- GPU: NVIDIA GeForce RTX 5070, 12 GB GDDR7, Blackwell (sm_120),
  672 GB/s bandwidth
- CPU: Intel Core i7-12700K (8P + 4E cores, 20 threads)
- System RAM: 64 GB
- Storage: NVMe SSD
- OS: Windows 11 host running Ubuntu under WSL2
- Container runtime: assume Docker Desktop with the WSL2 backend
  unless research shows a better option
- GPU access from WSL2: via NVIDIA's WSL CUDA driver. The Linux side
  inside WSL2 should NOT have its own NVIDIA driver installed; the
  Windows host driver is used through /usr/lib/wsl. Subagent 1 must
  verify current Blackwell support on this path.

================================================================
ASSUMED STACK (verify and refine via research)
================================================================
- Embeddings: BAAI/bge-large-en-v1.5 OR Qwen3-Embedding-0.6B,
  served via Hugging Face text-embeddings-inference (TEI) in Docker
- Reranker: BAAI/bge-reranker-v2-m3 via TEI
- Vector store: Qdrant in Docker, with int8 scalar quantization
- Document parsing: unstructured or docling
- Chunking: ~512 tokens, ~64 overlap, structure-aware where possible
- LLM backend (primary): Anthropic-hosted Claude 4.6 models, called by
  Claude Code itself (NOT by the MCP server)
- LLM backend (also supported): any other hosted LLM the client can
  reach
- LLM backend (secondary, optional): a self-hosted local model served
  by Ollama / llama.cpp / vLLM
- Frontend / orchestration: Claude Code, integrated with the local RAG
  via a local MCP server that exposes retrieval tools

================================================================
HARD CONSTRAINTS
================================================================
- Must work on Blackwell / sm_120 from inside WSL2 Ubuntu. CUDA 12.8+
  and matching PyTorch / Docker image tags are required. Flag any
  component that does not yet have stable Blackwell-on-WSL2 support
  and propose a fallback.
- All project files, Docker volumes, and Qdrant storage must live on
  the WSL2 ext4 filesystem (e.g. ~/projects/...) and NOT on the
  Windows-mounted /mnt/c path. The 9P filesystem bridge is far slower
  for the kind of small-file I/O parsing and indexing produce.
- Everything in the retrieval pipeline runs locally. The only required
  network egress is the client's existing connection to whatever
  hosted LLM it is configured to use.
- The MCP server must NOT make LLM calls itself — not to Anthropic,
  not to any other hosted provider, not to a local model. It returns
  retrieved chunks; the client assembles the final prompt and calls
  the model.
- The MCP server must be backend-agnostic at its API surface. Any
  backend-specific behavior (if it exists at all) lives behind an
  internal profile abstraction, not in the tool signatures.
- No managed/cloud vector DB.
- VRAM budget: embedder + reranker resident simultaneously must fit
  comfortably in 12 GB with headroom for a small query-rewrite model.
  Note: a self-hosted backend LLM would compete for the same 12 GB,
  which is part of why that path is secondary.
- System RAM headroom: with 64 GB total, the retrieval stack
  (Qdrant + TEI servers + ingestion workers + WSL2 overhead + Docker
  Desktop) should leave at least 16 GB free for the Windows host and
  Claude Code itself.
- Token cost minimization is the whole point: the retrieval contract
  must make it easy for the client to leverage whatever caching
  mechanism the chosen backend offers (Anthropic prompt caching,
  OpenAI prompt caching, Gemini context caching, etc.) on stable parts
  of the context.

================================================================
SUBAGENTS TO DISPATCH (in parallel where possible)
================================================================
Spawn one research subagent per topic. Each should web-search, read
primary sources, and return a short written brief plus citations.

1. BLACKWELL + WSL2 COMPATIBILITY AUDIT
   - Confirm RTX 5070 (sm_120) works under WSL2 Ubuntu via the
     NVIDIA Windows host driver + /usr/lib/wsl libcuda passthrough,
     with current driver versions
   - Current TEI Docker image tags with CUDA 12.8+ / sm_120 support,
     verified to run under Docker Desktop's WSL2 backend with
     --gpus all
   - Qdrant: confirm CPU-only, no GPU dependency, runs cleanly under
     Docker Desktop / WSL2
   - PyTorch / sentence-transformers wheels for Blackwell, installed
     inside WSL2 Ubuntu
   - Known WSL2-specific gotchas: filesystem performance, Docker
     Desktop resource limits (.wslconfig memory/CPU caps), GPU
     visibility inside containers, port forwarding to Windows host

2. EMBEDDING MODEL SELECTION
   - Compare bge-large-en-v1.5, Qwen3-Embedding-0.6B, nomic-embed-text-v2,
     and any newer top performers on MTEB retrieval as of today
   - Recommend ONE primary + ONE fallback, with VRAM, dim, licensing

3. RERANKER SELECTION
   - bge-reranker-v2-m3 vs newer alternatives (Qwen3-Reranker, Jina, etc.)
   - Throughput on a 12 GB Blackwell card
   - Recommend ONE primary

4. CLAUDE CODE ↔ LOCAL RAG INTEGRATION (HIGHEST PRIORITY)
   - Confirm that a local MCP server is the right integration pattern
     for Claude Code as of today
   - Find the current MCP SDK (Python preferred, TS acceptable) and a
     minimal scaffolding example
   - Define the tool surface the MCP server should expose:
       * search_corpus(query, k=5, filters=None) -> list of chunks
       * get_chunk(chunk_id) -> full chunk + metadata
       * list_sources() -> available document sources
       * (propose any others worth having)
   - How to register a local MCP server with Claude Code: exact config
     file location, command syntax, env vars, transport (stdio vs HTTP)
   - Specifically address the WSL2 case: is Claude Code running on
     Windows or inside WSL2 Ubuntu? If on Windows, how does it reach
     a Python MCP server living inside WSL2 (stdio via wsl.exe?
     localhost forwarding? HTTP transport?). Ask me which side Claude
     Code runs on if it materially changes the recommendation.
   - How returned chunks should be formatted so the client can cite
     sources back to me cleanly
   - Confirm the tool surface stays identical regardless of which
     backend model the client is currently using
   - Briefly note whether the same MCP server, unmodified, would also
     be consumable by other MCP-aware clients (including ones pointed
     at non-Anthropic hosted models or at self-hosted local models)

5. CACHING & BACKEND-SPECIFIC OPTIMIZATION RESEARCH
   - Survey prompt/context caching across the major hosted LLM
     providers as they exist today: Anthropic (cache_control, TTL,
     pricing multipliers for the 4.6 family and older), OpenAI
     (automatic prompt caching, eligibility rules), Google Gemini
     (explicit context caching API), and any others worth noting.
   - For each, what does the retrieval layer need to do (or avoid
     doing) to maximize cache hit rate?
   - CRITICAL: investigate whether meaningful retrieval-layer
     optimizations differ across:
       (a) tiers within the Claude 4.6 family (Haiku / Sonnet / Opus)
       (b) different hosted providers (Claude vs GPT vs Gemini etc.)
     Examples to look for:
       * Different optimal top-k or context budgets
       * Different cache breakpoint behavior or minimum cacheable size
       * Different recommended prompt structure for retrieved chunks
       * Different tolerance for noisy/irrelevant chunks
       * Any official guidance from any provider on RAG prompt shape
   - Return a clear yes/no recommendation: do we need a backend-profile
     abstraction, or is one backend-agnostic configuration optimal?
   - If yes: propose the minimum viable profile schema and the default
     values for Haiku 4.6, Sonnet 4.6, Opus 4.6, a generic Anthropic
     fallback, and at least one non-Anthropic profile to prove the
     abstraction generalizes.
   - If no: say so explicitly and recommend the single configuration.

6. CHUNKING & PARSING
   - Best current library for mixed PDF/DOCX/MD/HTML/code parsing
     (unstructured vs docling vs marker vs others)
   - Recommended chunking strategy for mixed-content corpora

7. EVAL HARNESS
   - Minimal local eval setup for measuring recall@k and rerank lift
   - Tools: ragas, trulens, or hand-rolled — recommend the lightest
     option that gives me recall@5 and MRR on a 30–50 question gold set
   - If backend profiles end up being a thing, the eval harness must
     be able to run the same gold set against multiple profiles and
     report which profile wins on which question class

================================================================
DELIVERABLE: TICKETED IMPLEMENTATION PLAN
================================================================
After subagents report back, synthesize their findings and produce:

A. EXECUTIVE SUMMARY (≤ 300 words) of the final chosen stack with
   rationale for any deviations from my assumed stack. Must explicitly
   state the backend-profile decision (build the abstraction or not)
   and why. Must also briefly note whether self-hosted-LLM
   compatibility comes for free with the chosen design or requires
   deferred work.

B. RISK REGISTER listing anything that could block the build, with
   mitigations (especially Blackwell-on-WSL2 and MCP-related).

C. TICKET LIST in the following format. Each ticket is independently
   actionable and small enough to complete in one Claude Code session.
   Order them so dependencies are satisfied.

   TICKET-001
   Title: <short imperative>
   Depends on: <ticket IDs or "none">
   Goal: <one sentence>
   Acceptance criteria:
     - <bullet>
     - <bullet>
   Implementation notes: <commands, file paths, config snippets>
   Estimated effort: S / M / L

   Expected ticket categories (not exhaustive):
   - WSL2 + Docker Desktop + NVIDIA WSL CUDA verification
     (nvidia-smi inside WSL2, nvidia-smi inside a --gpus all container,
     .wslconfig memory/CPU tuning)
   - Project layout on the WSL2 ext4 filesystem
   - Qdrant deployment + collection schema
   - TEI embedder deployment
   - TEI reranker deployment
   - Document parsing pipeline
   - Chunking pipeline
   - Ingestion script (parse → chunk → embed → upsert)
   - MCP server scaffolding
   - MCP tool implementations
   - Claude Code MCP registration + smoke test (with the WSL2-aware
     transport choice from subagent 4)
   - Tool response format tuned for caching
   - (CONDITIONAL) Backend profile abstraction + Haiku/Sonnet/Opus 4.6
     default profiles + generic Anthropic fallback + at least one
     non-Anthropic profile — include ONLY if subagent 5 returns "yes"
   - (OPTIONAL, LOW PRIORITY) Self-hosted LLM backend validation:
     verify the same MCP server works unmodified with at least one
     local-model client setup. Mark this ticket clearly as optional.
   - Eval harness + gold question set
   - End-to-end smoke test: ask a question in Claude Code, confirm
     retrieved chunks land in the model's context and the answer cites
     the right sources

D. A "DAY ONE" sequence: which 3–5 tickets I should do first to get a
   minimum working pipeline (even with a tiny corpus) before optimizing.
   The self-hosted-LLM ticket must NOT appear in the Day One sequence.

================================================================
GROUND RULES
================================================================
- Use web search aggressively. My knowledge of current model versions,
  TEI tags, MCP SDK status, WSL2/Blackwell driver state, and
  per-provider caching guidance may be stale.
- Cite primary sources (GitHub repos, official docs, model cards,
  provider documentation, NVIDIA WSL2 CUDA docs).
- Do not invent version numbers, image tags, or config paths — verify.
- If a subagent finding contradicts my assumed stack, say so explicitly
  and recommend the change.
- Default to SIMPLER. Do not build the backend-profile abstraction
  unless the research clearly justifies it. YAGNI applies. Same rule
  for self-hosted LLM support — include it only if it's essentially
  free given the chosen design.
- Ask me clarifying questions ONLY about: the exact corpus contents
  and formats, whether I have a preferred project directory inside
  WSL2, and whether Claude Code itself runs on the Windows side or
  inside WSL2 Ubuntu (this affects the MCP transport choice).
  Everything else, make a reasoned default and note it.

Begin by confirming you understand the assignment, asking the three
clarifying questions above, and then dispatching subagents.
