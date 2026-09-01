# Fractal Agent — Agent Instructions

Implementing fractal.md: a fractal self-similar Agent Harness built from 4 primitives
(Intent / Check / Work / World State), 13 definitions, 2 axioms, 6 theorems.

Implementation strategy: a small deterministic kernel (contracts, evidence, invariants,
scheduling) with LLMs as untrusted components, invoked only at the four capability points
(plan / build / delegate / supervise) and at discussion. Every LLM output passes schema
and Guard validation before entering the kernel.

## Spec hierarchy (binding order)

1. `fractal.md` — constitution, v0.1 (2026-08-31). Treat as immutable reference text; never edit.
2. `spec/amendments.md` — effective amendments (AM-xxx) resolving spec gaps. Binding.
3. `spec/invariants.md` — invariant catalog with Guard error codes and recovery paths.
4. `docs/adr/` — decision records that bind the implementation.
5. `docs/roadmap.md` — phases with acceptance criteria mapped to theorems.
6. `spec/glossary.md` — spec notation to code symbol mapping.

If implementation and spec conflict: stop, do not silently deviate. Use the `spec-amend`
skill to record an amendment or ADR first, then implement.

## Architecture

```text
fractal_cli      discussion, steering, session entry points         (top)
fractal_runtime  boundary, check executors, build executor, LLM     (side effects)
fractal_kernel   models, event store, guard, DAG, scheduler         (pure)
```

Dependency rule (enforced by `tests/test_imports.py`):

- `fractal_kernel` imports nothing from the other two packages; no LLM SDK, no subprocess,
  no git.
- `fractal_runtime` may import `fractal_kernel`.
- `fractal_cli` may import everything.
- No package imports tau anywhere in `src/`: the build executor is a minimal agent loop
  ported from tau_agent v0.4.1 (ADR-0006). tau (`../tau`) remains the reference
  implementation and the daily dev agent — as a tool, never as a dependency.

Key decisions (see `docs/adr/`):

- ADR-0001: boundary = declarative write manifest (static disjointness check across parallel
  siblings) carried by a git worktree, enforced by tool interception + submission-time diff
  audit. Conflict determination is set intersection, not behavior guessing.
- ADR-0002 (superseded by 0006): tau chosen as build body and reference. Kept for history.
- ADR-0003: append-only JSONL event log is the sole source of truth; state is a fold over
  events. LLM conversations are caches, not facts.
- ADR-0004: checks are registered executors with a declared determinism class
  (hard/soft/human); v0 implements hard checks only.
- ADR-0005: spec change procedure — fractal.md is never edited; amendments accumulate in
  `spec/amendments.md`.
- ADR-0006 (supersedes 0002's dependency clause): build capability body = a minimal
  agent loop ported from tau_agent v0.4.1 into `fractal_runtime` — messages, tools
  (the manifest interception surface), loop, events, provider adapters, fake provider.
  Porting discipline: record source version and deviations; semantic deviations get an ADR;
  re-syncing upstream is an explicit decision.

## Commands

```bash
uv sync --dev
uv run pytest
uv run ruff check .
uv run ruff format .
uv run mypy
```

Run Python and tests through `uv` so they use the project environment.

## Workflow

- Work in phases per `docs/roadmap.md`; record journals in `docs/dev-notes/`.
- Spec-first: implement concepts through the `implement-concept` skill —
  spec clause → kernel schema → red invariant tests → minimal implementation → green.
- Invariant tests never call an LLM, never touch the network, and never depend on tau;
  LLM paths are tested with recorded golden replays (`tests/golden/`, introduced in Phase 2).
- Every new Guard rule gets an entry in `spec/invariants.md` (error code, REJECT behavior,
  recovery path — all three mandatory).
- Decisions with spec-level or cross-module consequence get an ADR before the code.
- Keep commits atomic: one coherent feature, fix, docs update, refactor per commit.

## Python guidelines

- Python >= 3.12; pydantic models for spec objects; frozen models + tuple collections for
  immutable spec objects (Contract, Evidence, CheckSpec) to honor T4 at the type level.
- Docstrings cite spec clause numbers (D / A / T / AM); no inline comments.
- Prefer explicit, small abstractions over framework-heavy designs (same philosophy as tau).

## Current phase

Phase 0 (schema freeze + invariant tests). See `docs/roadmap.md` for status and acceptance.

## Skills

Project skills in `.agents/skills/` (loaded by tau and AGENTS.md-compatible agents):

- `implement-concept` — spec → schema → red tests → implementation loop
- `spec-amend` — record spec gaps as amendments/ADRs instead of improvising
- `add-check-type` — register a new check executor
- `phase-verify` — run the current phase acceptance checklist
