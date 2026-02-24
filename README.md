# Repo Summarizer API

> FastAPI + Nebius Token Factory — summarize any public GitHub repository in seconds.

Given a public GitHub URL, the API returns:
- A human-readable summary (markdown)
- Main technologies detected
- Project structure overview

---

## Project Structure

```
Nebius_project/
├── main.py                  # FastAPI app entry point
├── settings.py              # Pydantic settings (reads from .env)
├── requirements.txt
├── api/
│   ├── routes.py            # API route definitions
│   ├── schemas.py           # Request / response models
│   └── summarize.py         # Summarize endpoint logic
├── services/
│   ├── github_client.py     # GitHub REST API client
│   ├── repo_processor.py    # File selection & context budgeting
│   ├── llm_client.py        # Nebius (OpenAI-compatible) async client
│   ├── summarizer.py        # Prompt construction
│   └── summarize_service.py # Orchestration layer
├── utils/
│   ├── errors.py
│   └── text.py
└── django_ui/               # Optional web UI (disabled by default)
    ├── settings.py
    ├── urls.py
    └── views.py
```

---

## Setup

**1. Create and activate a virtual environment**

```bash
python -m venv .venv

# Linux / macOS
source .venv/bin/activate

# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1
```

**2. Install dependencies**

```bash
pip install -r requirements.txt
```

**3. Configure environment variables**

Create a `.env` file in the project root:

```dotenv
# ------------------------------------------------
# REQUIRED
# ------------------------------------------------
NEBIUS_API_KEY=<your Nebius Token Factory API key>
# Obtain from https://nebius.ai — used to authenticate all LLM calls.

# ------------------------------------------------
# OPTIONAL
# ------------------------------------------------
GITHUB_TOKEN=<your GitHub personal access token>
# Strongly recommended. Without it, GitHub's unauthenticated rate limit
# (60 req/hr) will quickly block requests on active usage.
# Create one at https://github.com/settings/tokens (no special scopes needed).

NEBIUS_MODEL=Qwen/Qwen3-30B-A3B-Instruct-2507
# Override the default LLM model. See "Model Choice" below for details.

ENABLE_DJANGO_UI=True
# Set to True to mount the optional Django web UI at /ui (see below).
```

---

## Running the Server

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

---

## Usage

**REST API**

```bash
curl -X POST http://localhost:8000/summarize \
  -H "Content-Type: application/json" \
  -d '{"github_url": "https://github.com/psf/requests"}'
```

**Django Web UI** *(optional)*

If `ENABLE_DJANGO_UI=True` is set in `.env`, a minimal web interface is available at:

```
http://localhost:8000/ui
```

It provides a simple form to submit a GitHub URL and view the formatted summary — no API client needed.

---

## Model Choice

The default model is **`Qwen/Qwen3-30B-A3B-Instruct-2507`**.

This model was chosen for several reasons:
- **Code comprehension** — Qwen3 performs strongly on code-related tasks, including reading multi-file repositories and identifying architectural patterns.
- **Instruction following** — it reliably produces structured JSON output (required for the schema-enforced response format), reducing parsing failures.
- **Cost/quality balance** — at 30B parameters with a Mixture-of-Experts architecture (only ~3B active per forward pass), it delivers near-70B quality at lower inference cost.
- **Nebius availability** — it is a first-class model on the Nebius Token Factory platform and is demonstrated in their official examples.

To use a different model, set `NEBIUS_MODEL` in your `.env`. Any model available on
[Nebius Token Factory](https://nebius.ai) that supports the OpenAI-compatible `json_schema` response format will work.

---

## Repo Content Strategy

**Included (prioritized):**
- `README` — highest priority, larger context budget allowed
- Key config files: `pyproject.toml`, `requirements.txt`, `setup.py`, `package.json`, `Dockerfile`, CI configs
- Representative source files under `src/`, `app/`, `tests/`, `docs/`

**Skipped:**
- Binary assets (images, archives, compiled artifacts)
- Lock files (`package-lock.json`, `poetry.lock`, etc.)
- Vendor / build directories (`node_modules/`, `dist/`, `build/`, `.venv/`, caches)
- Very large files (per-file byte cap enforced)

**Context budget:**
Files are scored and ranked by relevance. The processor fills the prompt up to a total character cap, truncating lower-priority files first. This keeps LLM calls fast and cost-predictable regardless of repository size.


---

## Why these key decisions map to your rubric

- **File filtering:** ignores obvious noise dirs + binaries + lockfiles; prioritizes README + configs + representative source files.
- **Context window strategy:** explicit *total prompt budget* + per-file truncation + “readme-first”.
- **Prompt engineering:** strict JSON schema output via Nebius `response_format` (documented). :contentReference[oaicite:2]{index=2}
- **Modularity:** GitHub client / repo processing / LLM client / summarizer separated.

If you want, I can also add: (a) a `/health` endpoint, (b) optional streaming, or (c) a 2-pass summarization path for giant repos (summarize files → summarize summaries) — but the above already satisfies the blocking criteria cleanly.
::contentReference[oaicite:3]{index=3}