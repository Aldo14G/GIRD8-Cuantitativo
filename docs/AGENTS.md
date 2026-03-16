# AGENTS.md

Guide for coding agents working in this repository.

## Project Snapshot

- **Project**: Evolución de la Calidad de Datos Abiertos NL 2024-2026
- **Language**: Python 3.11+
- **Main scripts**: `src/extract/01_extract.py`, `src/evaluate/02_evaluate.py`, `src/longitudinal/03_longitudinal.py`
- **Data flow**: `data/raw` → `data/processed` → `data/output` (Medallion Architecture)
- **Repo has**: No package build config, no formal test suite yet

## Environment

- **Recommended Python**: 3.11 (3.10+ acceptable)
- **Baseline dependencies**:
  ```bash
  pip install -r requirements.txt
  ```
- **Optional dev tools**:
  ```bash
  pip install pytest ruff black mypy
  ```

## Installation

```bash
# Clone the repository
git clone https://github.com/[tu-usuario]/GIRD8-Cuantitativo.git
cd GIRD8-Cuantitativo

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Copy environment template and configure
cp .env.example .env
# Edit .env with your API keys
```

## Build Commands

- There is no package build step
- Use compile checks as build-equivalent validation:
  ```bash
  python -m compileall src/
  ```
- Quick per-file syntax check:
  ```bash
  python -m py_compile src/extract/01_extract.py src/evaluate/02_evaluate.py src/longitudinal/03_longitudinal.py
  ```

## Lint and Format Commands

- Recommended lint command:
  ```bash
  ruff check src/
  ```
- Recommended format check:
  ```bash
  black --check src/
  ```
- Auto-fix path:
  ```bash
  ruff check src/ --fix
  black src/
  ```

## Test Commands

- Current state: no automated tests are present
- Practical validation currently is script-level smoke testing:
  ```bash
  python -m src.extract 01_extract.py
  python -m src.evaluate 02_evaluate.py
  python -m src.longitudinal 03_longitudinal.py
  ```
- Or use the pipeline orchestrator:
  ```bash
  python scripts/run_pipeline.py
  ```
- If/when tests are added with `pytest`, use:
  ```bash
  pytest -q
  ```
- Run a single test file:
  ```bash
  pytest tests/test_evaluate.py -q
  ```

## Pipeline Run Order

Run modules in order unless intentionally debugging one layer:

```bash
# Full pipeline
python scripts/run_pipeline.py

# Or individual modules
python -m src.extract.main
python -m src.evaluate.main
python -m src.longitudinal.main
```

Do not skip upstream layers when downstream scripts expect fresh outputs.

## Code Style Guidelines

### Imports

- Group imports as: stdlib, third-party, local
- Keep imports explicit and remove unused imports in touched files
- Avoid wildcard imports

### Formatting

- Follow PEP 8
- Keep line length around 88-100 chars
- Preserve existing visual separators and section comments
- Prefer readability over compact one-liners

### Typing

- Add type hints for new or modified functions
- Use built-in generics (`list[str]`, `dict[str, Any]`) consistently
- Keep return types explicit for pipeline helpers
- Use `Optional[T]` only when `None` is a valid runtime state

### Naming

- Use `snake_case` for functions, variables, and files
- Use `UPPER_SNAKE_CASE` for module constants
- Prefer descriptive identifiers over abbreviations

### DataFrame and Schema Rules

- Parse timestamps with `pd.to_datetime(..., errors="coerce", utc=True)`
- Validate required columns before transformations
- Keep cross-layer column names stable unless migration is planned
- Add columns instead of repurposing existing ones

### Error Handling

- Wrap network and file I/O in `try/except` with actionable context
- Return structured fallback data for recoverable failures
- Include dataset/resource identifiers in error messages when possible
- Do not swallow exceptions silently

### Logging and Progress

- Existing style uses `print`; keep that style for consistency
- Emit periodic progress for long loops
- Print output artifact paths at script completion

## Architecture Safety Rules

- Respect medallion boundaries:
  - `data/raw`: extraction and snapshots
  - `data/processed`: scoring and organization-level aggregates
  - `data/output`: longitudinal deltas and predictive modeling
- Do not rename output files or prefixes without updating consumers
- Keep score scales in expected `0.0-1.0` range unless redesign is requested
- Preserve backward compatibility with historical snapshots when practical

## API and Secrets

- `src/evaluate/02_evaluate.py` includes optional LLM-based standards scoring
- Never hardcode API keys or credentials
- Prefer environment variables for secrets (use `.env` file)
- Keep explicit request timeouts in network calls

## Dashboard Integration

The project includes two dashboards that consume the processed data:

### R Dashboard
- Location: `dashboards/r/`
- Run: Open `app.R` in RStudio or run `Rscript app.R`
- Data source: `data/processed/`

### Web Dashboard
- Location: `dashboards/web/`
- Run: `python dashboards/web/server.py --data-root data/`
- Data source: `data/processed/` and `data/output/`

## Recommended Agent Workflow

1. Read `docs/PROJECT_CONTEXT.md` and target module before editing
2. Keep changes minimal and scoped to requested behavior
3. Run `python -m compileall .` after edits
4. Run the smallest relevant pipeline path for validation
5. Report changed files, assumptions, and output impact clearly

## Git Workflow (Open Science)

This is an open science project. When contributing:

1. Create a feature branch: `git checkout -b feature/your-feature`
2. Make changes and commit with descriptive messages
3. Push to GitHub and create a Pull Request
4. Ensure documentation is updated

---

For questions about the research methodology, see `docs/README.md`.
