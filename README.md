# Paper Manager + Jev

arXiv URL -> SQLite -> title-only category generation via OpenRouter -> title+abstract classification via Jev.

## Flow

1. `POST /papers/import` with an arXiv URL.
2. `POST /classify/categories` generates category candidates from titles only.
3. `POST /classify/jev` classifies papers with Jev using title + abstract and the generated categories.
4. Results are stored in SQLite.

The existing direct-LLM classification method can coexist with this Jev method.

## Setup

```bash
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
cp .env.example .env
```

Set `OPENROUTER_API_KEY` and `TYPESAFE_API_KEY` in `.env`.

Run:

```bash
uv run uvicorn app:app --reload
```

## API

Import:

```bash
curl -X POST http://127.0.0.1:8000/papers/import \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://arxiv.org/abs/2401.12345"}'
```

Generate categories:

```bash
curl -X POST http://127.0.0.1:8000/classify/categories
```

Classify all papers with Jev:

```bash
curl -X POST http://127.0.0.1:8000/classify/jev
```

Get papers:

```bash
curl http://127.0.0.1:8000/papers
```
