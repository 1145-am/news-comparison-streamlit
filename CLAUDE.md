# CLAUDE.md

## Project overview

Single-file Streamlit app (`app.py`) that lets users compare procurement news across up to 4 providers side by side: Syracuse (internal DB), Perplexity, Exa, and Linkup.

## Architecture

Everything lives in `app.py`. There are no modules, no separate files beyond config.

**Key sections in order:**
1. Page config + secrets + constants
2. `check_password()` — optional login gate
3. Fetch functions — one pair (`fetch_<provider>` / `fetch_<provider>_company`) per provider
4. Display helpers — `render_syracuse_results` (dict input) and `render_articles` (list input)
5. `PROVIDER_CONFIG` — list of dicts wiring each provider's label, session state key, fetch funcs, and render func
6. Session state initialisation
7. UI — sidebar source checkboxes, search mode radio, inputs, Get News button, results columns

## Adding a new provider

1. Write `fetch_<name>(industry, location)` and `fetch_<name>_company(company)` — both return a list of article dicts with keys: `headline`, `published_date`, `summary_text`, `published_by`, `document_url`.
2. Add an entry to `PROVIDER_CONFIG` (label, data_key, fetch_category, fetch_company, render).
3. Add `use_<name>` to session state defaults.
4. Add the API key to `.streamlit/secrets.toml` and read it at the top of `app.py`.
5. Add the package to `pyproject.toml` and run `uv add <package>`.

Syracuse is the exception — its fetch functions return a dict `{"count": int, "results": [...]}` and it has its own `render_syracuse_results` renderer.

## Article dict format

All non-Syracuse providers return lists of dicts:

```python
{
    "headline": str,
    "published_date": str,      # ISO 8601, used for sorting
    "summary_text": str,
    "published_by": str,
    "document_url": str,
}
```

## Environment

- **Package manager:** `uv` (not pip)
- **Python:** 3.13+
- **Run:** `uv run streamlit run app.py`
- **Install deps:** `uv add <package>` / `uv sync`
- **Config:** `.streamlit/secrets.toml` (never commit real keys)

## Secrets

```
SYRACUSE_API_KEY, PERPLEXITY_API_KEY, EXA_API_KEY, LINKUP_API_KEY
SYRACUSE_BASE_URL (default: https://syracuse.1145.am)
LOCATIONS_JSON    (JSON array of location strings)
CATEGORIES_JSON   (nested JSON object for category taxonomy)
COMPANIES_JSON    (JSON array of company name strings)
[credentials]     (optional: username = "password" pairs)
```

## UI conventions

- `st.set_page_config(layout="wide")` is the very first `st` call — keep it that way.
- Provider selection is in the sidebar as checkboxes (`use_<provider>` session state keys).
- The number of result columns is always equal to the number of providers that returned data.
- `get_news_disabled` prevents the button when inputs are incomplete.
- All fetched results are cached in session state so they survive reruns.
