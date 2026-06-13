# 1. Core Product & Domain Rules

This repository is a portfolio-grade, RAG-based university application assistant for international Master's applicants. It is currently an early **greenfield scaffold** (FastAPI + `/health`); RAG, retrieval, LLM, and agent orchestration are planned but not yet implemented.

- Core purpose: ingest university admission documents, then (1) answer applicant questions with **source citations**, (2) generate per-program application checklists, and (3) draft formal emails to admissions offices.
- Answers MUST be grounded in ingested documents and cite their sources. Never fabricate admission facts (deadlines, fees, required documents, language-test thresholds). If the documents do not support an answer, say so explicitly rather than guessing.
- CRITICAL DOMAIN RULE: Different universities and programs have fundamentally different requirements. When retrieving, aggregating, or deriving facts, strictly scope everything to the specific program/university in question. NEVER blend facts across institutions (e.g., applying one school's deadline or fee to another), as this produces confidently wrong answers and undermines trust.

Scope control is strict:
- Do not add new endpoints unless explicitly requested.
- Do not add RAG, vector store, embedding, LLM, or LangGraph components until explicitly requested. The scaffold is intentionally minimal.
- Do not add new business workflows unless explicitly requested.
- Do not expand schemas, payloads, response shapes, or contracts unless explicitly requested.
- Do not invent features because they seem useful. Preserve existing intent and interfaces.

# 2. Technical Details

Package and runtime truth:
- Language/runtime: **Python 3.12**.
- Package manager: `pip`.
- Primary runtime manifest: `requirements.txt`. ALWAYS read `requirements.txt` to understand the current libraries and their specific versions. Do not hallucinate package versions.

Architecture and ownership:
- `app/` is the thin FastAPI delivery layer. ALWAYS check `app/main.py` (the `create_app()` factory + router wiring) and `app/api/routes.py` for current API contracts.
- `app/api/schemas.py` holds Pydantic request/response models; all request/response bodies go through Pydantic, not raw dicts.
- `app/core/config.py` holds configuration (`Settings` / `get_settings()` via `pydantic-settings`).
- Domain/RAG logic does not exist yet. When added, it must live in its own package (e.g. `app/rag/` or `src/`), keeping `app/` a thin delivery layer.
- Tests live in `tests/`, driven by `pytest` and FastAPI's `TestClient` (which depends on `httpx`).

# 3. Configuration, Secrets & Storage

- All configuration comes from environment variables, surfaced through `app/core/config.py` (`Settings` / `get_settings`). Add new config as typed fields there; never read `os.environ` directly inside handlers.
- Never hardcode credentials, API keys, or connection strings anywhere in code or config; read them from the environment.
- Local development uses a gitignored `.env`; `.env.example` documents every available variable. Never commit a real `.env` or any real key.
- Future LLM/RAG credentials (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`) exist only as commented placeholders in `.env.example` and are NOT wired up yet.
- Environment isolation: select behavior via the `ENVIRONMENT` variable rather than hardcoding paths. If it is not explicitly set, default to `development` (a safe default; never default to a production path).
- Document & index storage (when RAG lands): persist ingested documents and vector indexes under a clearly partitioned, configurable location. Do NOT commit ingested corpora or built indexes into the repo, and do NOT scatter them in ad-hoc local folders.

# 4. Working Loop

Every task follows this loop exactly, with no exceptions:

`Inspect -> Plan -> Wait for approval -> Code -> Test -> Fix`

- Inspect the current code before proposing anything. No work is done ad-hoc, not even bug fixes.
- Write a step-by-step plan BEFORE touching any code. The plan is a file under `docs/experiments/`; this builds project memory, lets new joiners read the repo's history from `docs/experiments/` alone, and keeps work commit-traceable.
- CRITICAL: After presenting the plan, you MUST wait for my explicit approval before writing or modifying any files.
- Then Code -> Test -> Fix. Prefer small, architecture-preserving edits over broad rewrites.
- Every plan and its outcome is committed AND pushed; the working tree returns clean (`git status` empty) before moving to the next item.
- Plan file format and marking contract: see `docs/experiments/AGENTS.md` (authoritative).

# 5. Data Science & ML Rules (CRITICAL)

- Grounding over recall: a generated answer must be supported by retrieved source documents and must cite them. Never fabricate admission facts; an unsupported answer is a defect, not a near-miss.
- Prevent data leakage: keep evaluation question/answer sets isolated from any tuning or few-shot data; never tune on the eval set. Fit any learned transformation ONLY on the training split.
- Reproducibility: set `random_state=42` for all stochastic operations, and pin the exact model ids/versions used for embeddings and generation so a run can be reproduced.
- Preserve evaluation, citation/grounding, and artifact-generation behavior during updates; do not silently change how citations or checklists are produced.

# 6. Debugging Rules

When facing a bug, DO NOT GUESS. Follow this loop:
1. Reproduce the problem.
2. Prove you reproduced it (with concrete evidence: a failing test, log, stack trace, or response payload) before changing any code.
3. Find the root cause. Verify which layer it belongs to: API delivery, configuration wiring, retrieval, prompt/generation, or document ingestion.
4. Fix it. Keep the fix minimal and local to the proven fault line.
5. Prove you fixed it, via the same reproduction path or a tighter automated test.

Additional rules:
- Do not patch around missing config, config drift, or dependency drift unless you have proven that is the root cause.
- Prefer focused tests or targeted reproductions over speculative edits.

# 7. Coding Standards

Non-negotiable:
- No emojis ever in code, logs, commits, or generated documentation.
- Never use Turkish characters in variables, functions, or comments.
- Always add type hints to function signatures and return types.
- Keep functions small and readable: one clear responsibility each.
- Always use exact variable names as they appear in the codebase. NEVER invent custom acronyms for codebase variables or business logic; if there is no existing name, write the concept out clearly.
- Avoid over-defensive programming. Do not add `try/except` blocks, wrappers, or fallback branches without evidence they are needed.
- No filler: no comments that just restate the code, no redundant docstrings, no summary sections repeating what is already above. Keep generated documentation short and direct.

Repo-safe edits:
- Keep `app/` thin (FastAPI delivery only); domain/RAG logic goes in its own package; configs stay declarative and typed in `app/core/config.py`.
- Do not silently rename endpoint paths, schema fields, config keys, or modules.
- Do not introduce broad refactors during feature or bug work unless explicitly requested.
- Prefer explicit, testable logic over abstraction-heavy wrappers and fallback-heavy control flow.
- If you discover drift or contradictions, document them in the task output instead of masking them.

Modularity:
- Domain/RAG code must be modular, reusable, and cleanly separated. Isolate heavy transformations (e.g. document parsing, chunking) into pure, independently testable functions.

Performance & memory safety:
- Design ingestion and indexing pipelines for scale. Do not load an entire document corpus into memory when chunked or streamed processing is possible.
- Immediate cleanup: any temporary local files created during ingestion or extraction MUST be deleted in a `finally` block to prevent local disk bloat in containerized environments.

# Development commands

```bash
# Set up environment (first time)
python3.12 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env

# Run the API (auto-reload)
uvicorn app.main:app --reload

# Run the tests
pytest
```
