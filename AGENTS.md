# Repository Guidelines

## Project Overview

This repository is a web-based data-analysis AI agent. Users upload CSV-centered datasets, ask natural-language questions in a React/Vite Workbench, and receive streamed FastAPI/LangGraph answers that can combine preprocessing, analysis, RAG/guideline retrieval, visualization, report drafting, approvals, and trace logging.

Product intent lives in `docs/product/prd.md`; current implementation constraints live in `docs/product/current-state-baseline.md`; priority work lives in `docs/product/roadmap.md`. Runtime docs are useful, but code is the final authority when docs drift.

## Architecture & Data Flow

- Backend entrypoint: `backend/app/main.py` loads `.env`, creates the FastAPI app, adds CORS for local frontend ports, creates SQLAlchemy tables with `Base.metadata.create_all()`, and mounts routers directly.
- Main chat path: `POST /chats/stream` enters `backend/app/modules/chat/`, creates/loads a session, validates the selected `source_id`, emits a `session` SSE event, then relays `AgentClient` events.
- Workflow path: `backend/app/orchestration/builder.py` composes LangGraph nodes roughly as `intake_flow -> dataset_context/chat_fast_path/guideline_flow/planner -> preprocess/analysis/rag/visualization -> merge_context -> data_qa/report/general/clarification terminals`.
- Streaming contract: `backend/app/orchestration/client.py` yields `thought`, `chunk`, `approval_required`, `done`, and `error` events. Approval stages are `preprocess`, `visualization`, and `report`; resume uses the same SSE parsing path.
- Boundary rule: `backend/app/modules/` owns domain behavior, routers, persistence, deterministic processors, and service logic. `backend/app/orchestration/` owns cross-module routing, shared state, approval interrupts, final answer packaging, and SSE-facing output contracts.
- State contract: `backend/app/orchestration/state.py` defines shared keys such as `handoff`, `pending_approval`, `preprocess_result`, `analysis_result`, `rag_result`, `guideline_result`, `visualization_result`, `merged_context`, `evidence_package`, `answer_quality`, `output`, and `fast_path_result`. Prefer additive keys; renames affect frontend, docs, tests, and SSE consumers.
- API route names are contracts. Preserve current prefixes including `/vizualization` unless changing backend, frontend, docs, and tests together.

## Key Directories

- `backend/app/core/` — shared DB/session, LLM, prompt, and tracing infrastructure.
- `backend/app/modules/` — feature modules: datasets, EDA/profiling, chat, analysis, preprocess, RAG, guidelines, visualization, reports/results. Typical public modules use `router.py`, `service.py`, and `schemas.py`; AI-heavy modules also use `planner.py`, `processor.py`, `executor.py`, or `run_service.py`.
- `backend/app/orchestration/` — LangGraph workflow assembly, state contracts, streaming adapter, final answer composition, and workflow wrappers.
- `backend/tests/` — tracked pytest suite. Do not create a new top-level `tests/` directory.
- `frontend/src/app/` — actual frontend app tree. Entry sequence is `frontend/src/main.tsx`, then `frontend/src/app/App.tsx`, then `frontend/src/app/pages/Workbench.tsx`; there is no `WorkbenchApp.tsx`.
- `frontend/src/app/hooks/useAnalysisPipeline.ts` — large Workbench orchestration hook for upload, dataset selection, SSE chat runs, approval resume, result state, and UI milestones.
- `frontend/src/lib/` — API client, request/response types, payload normalizers, and visualization helpers.
- `docs/product/` — product baseline; `docs/architecture/` — code-following runtime docs; `docs/system/` — public API/SSE and backend/frontend structure docs.
- `evaluation/` and `backend/tests/evaluation/` — local benchmark docs, helpers, contracts, deterministic runtime checks, and opt-in live benchmark tests.
- `storage/` — runtime datasets, guideline files, vector indexes, logs, and LangGraph checkpoints; treat generated storage artifacts as local runtime state.

## Development Commands

```bash
# Integrated local dev; backend defaults to 127.0.0.1:8000, frontend to 127.0.0.1:5173
bash dev.sh

# Backend only
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000

# Frontend only; manual docs commonly use port 3000
npm --prefix frontend run dev -- --host 127.0.0.1 --port 3000
npm --prefix frontend run build

# Targeted backend/doc checks
PYTHONPATH=. pytest -q backend/tests/test_docs_harness.py
PYTHONPATH=. pytest -q backend/tests/test_architecture_docs.py
PYTHONPATH=. pytest -q backend/tests/test_main_workflow_analysis_happy_path.py
PYTHONPATH=. pytest -q backend/tests/test_analysis_planning_accuracy_guards.py backend/tests/test_planner_analysis_accuracy_guards.py
```

Frontend `package.json` only declares `dev` and `build`; do not claim `lint`, `check:types`, or `test` scripts passed unless they are added first.

## Code Conventions & Common Patterns

- Make the smallest target-scoped diff that satisfies the request. Avoid adjacent cleanup, broad refactors, and formatting-only churn.
- Before changing a workflow, router, payload, or public type, confirm real paths, route prefixes, payload keys, and package scripts in the current tree.
- Read child guidance before scoped work: `backend/app/orchestration/AGENTS.md`, `backend/app/modules/AGENTS.md`, `frontend/src/app/AGENTS.md`, and `docs/architecture/AGENTS.md`.
- For architecture/codebase questions, inspect `graphify-out/GRAPH_REPORT.md` first; if `graphify-out/wiki/index.md` exists, prefer the wiki. Do not commit graphify output wholesale.
- Do not add broad `try/except` or `try/catch`, retry/backoff layers, fake fallbacks, or defensive validation unless explicitly requested.
- Keep deterministic validation/rule logic in processors or services, not routers. Keep cross-feature sequencing in orchestration, not feature modules.
- Dependency injection uses `dependencies.py` factory functions and FastAPI `Depends`; repositories receive DB sessions and services receive repositories/processors/readers.
- Frontend stateful orchestration belongs in hooks and normalization helpers; avoid scattering pipeline/session logic through presentation components.
- `components/ui/` are broad-impact shared primitives; `components/genui/` is Workbench-specific product UI. Tailwind utility classes and `--genui-*` CSS variables are common.
- Preserve exact backend/frontend contracts, including `/vizualization`, approval payload keys, and final result keys. Update `frontend/src/lib/api.ts`, `useAnalysisPipeline.ts`, renderers, docs, and tests together when contracts move.
- DB schema changes rely on `Base.metadata.create_all()`; there is no migration tool in this repo.

## Important Files

- `backend/app/main.py` — FastAPI initialization and router mounting.
- `backend/app/orchestration/builder.py` — main LangGraph workflow branching and terminal behavior.
- `backend/app/orchestration/client.py` — LangGraph streaming adapter and final SSE payload construction.
- `backend/app/orchestration/state.py` — shared TypedDict state contract.
- `backend/app/orchestration/ai.py` — final general/data answer generation from merged context.
- `backend/app/modules/chat/router.py` and `service.py` — user-facing chat/SSE entry and session integration.
- `backend/app/modules/analysis/service.py` and `processor.py` — analysis orchestration seam and deterministic validation/normalization.
- `backend/app/modules/rag/service.py` — RAG index/query lifecycle.
- `frontend/src/app/App.tsx` and `pages/Workbench.tsx` — frontend routing and Workbench shell.
- `frontend/src/app/hooks/useAnalysisPipeline.ts` — primary frontend runtime state engine.
- `frontend/src/lib/api.ts` — API base URL, `ApiError`, endpoint wrappers, request/response types, upload progress, and SSE URL helpers.
- `frontend/src/lib/visualization.ts` and `frontend/src/app/components/visualization/visualizationModel.ts` — visualization payload normalization/rendering.
- `frontend/package.json`, `frontend/tsconfig.json`, `frontend/vite.config.ts`, `backend/requirements.txt`, `dev.sh` — build/runtime tooling.
- `docs/architecture/request-lifecycle.md`, `docs/architecture/shared-state.md`, `docs/architecture/backend-workflow.md`, `docs/architecture/orchestration/workflows.md`, `docs/system/api-spec.md`, `docs/system/api-sse-error-contract.md` — contract docs that must follow runtime changes.

## Runtime/Tooling Preferences

- Backend uses Python dependencies from `backend/requirements.txt`, not `pyproject.toml`. Install with `pip install -r backend/requirements.txt` in your chosen virtual environment.
- Backend stack includes FastAPI, Uvicorn, SQLAlchemy, Pydantic, pandas/numpy, LangChain/LangGraph, sentence-transformers, and FAISS.
- Frontend uses npm scripts and `package-lock.json`; `frontend/package.json` also contains a `pnpm.overrides` pin for Vite, but no `packageManager` field.
- Frontend is private ESM with Vite 6, React 18, React Router 7, Tailwind/Vite plugin, MUI, Radix UI, Recharts, and strict TypeScript.
- `frontend/tsconfig.json` includes `src` but excludes `src/components/**/*` and `src/store/**/*`; do not assume those excluded trees are type-checked.
- `frontend/vite.config.ts` requires both React and Tailwind plugins for Make. Preserve the `@` alias to `frontend/src`; raw imports are configured only for SVG and CSV.
- API base URL defaults to `http://localhost:8000` via `VITE_API_BASE_URL` fallback in `frontend/src/lib/api.ts`.

## Testing & QA

- Use focused pytest runs for backend changes. Architecture/doc changes should run:
  ```bash
  PYTHONPATH=. pytest -q backend/tests/test_architecture_docs.py backend/tests/test_docs_harness.py
  ```
- Workflow/planning changes should run the workflow and planner guard tests listed in Development Commands, plus any directly affected module tests.
- Frontend changes should run `npm --prefix frontend run build`; no lint/typecheck script exists in `frontend/package.json`.
- `backend/tests/test_docs_harness.py` verifies markdown links, stale architecture references, placeholder phrases, code-path references, and documented FastAPI routes in `docs/system/api-spec.md`.
- Evaluation tests are split into `backend/tests/evaluation/contracts`, `runtime`, `workflow`, `metrics`, and opt-in `live`. Local raw CSV artifacts under `evaluation/raw/` may be gitignored and absent in a fresh checkout.
- Live benchmark tests require explicit opt-in, for example:
  ```bash
  RUN_LIVE_BENCHMARK=1 OPENAI_API_KEY=... PYTHONPATH=. pytest -q backend/tests/evaluation/live -m live_benchmark
  ```
- For code-file changes, run `graphify update .` when available to refresh the local graph; do not treat generated graphify artifacts as required source changes.
