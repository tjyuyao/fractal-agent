# fractal-agent

An implementation of [fractal.md](fractal.md): a fractal self-similar Agent Harness.

A contract (immutable intent + decidable checks) enters an instance; the instance either
builds it directly or decomposes it into a sub-contract DAG and delegates; the parent layer
verifies the returned evidence. The same pattern at any depth — that is the fractal.

- `fractal.md` — the constitution: primitives, definitions, axioms, theorems
- `spec/` — amendments, invariant catalog, glossary
- `docs/` — architecture, roadmap, ADRs, dev notes
- `src/fractal_kernel` — deterministic kernel (no LLM, no I/O)
- `src/fractal_runtime` — boundary, check executors, build executor (ported agent loop), LLM adapters
- `src/fractal_cli` — discussion / steering / session entry points

## Development

```bash
uv sync --dev
uv run pytest
```

## Credits

The build executor's agent loop is ported from [tau](https://github.com/huggingface/tau)
(`tau_agent` v0.4.1, MIT) — see `docs/adr/0006`. tau remains the reference
implementation and the recommended dev agent for this repo.
