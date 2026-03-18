# News Comparison

A Streamlit app for comparing procurement news across multiple search providers side by side. Designed for procurement category managers to research supplier risk, market trends, and industry news.

## Features

- **4 news providers** — Syracuse, Perplexity, Exa, and Linkup
- **Flexible comparison** — select any combination of providers; results display in dynamic side-by-side columns
- **Two search modes** — by procurement category + location, or by company name
- **Randomize** — pick a random category or company to explore
- **Wide layout** — optimised for comparing up to 4 sources simultaneously
- **Password protection** — optional login via `credentials` in secrets

## Providers

| Provider | What it does |
|---|---|
| **Syracuse** | Internal procurement news database; returns structured stories with full metadata |
| **Perplexity** | AI-powered web search (Sonar model); generates structured JSON article summaries |
| **Exa** | Neural news search; returns highlights from matched articles |
| **Linkup** | Structured web search; returns summarised articles via structured output schema |

## Setup

### Requirements

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### Install

```bash
uv sync
```

### Secrets

Create `.streamlit/secrets.toml`:

```toml
SYRACUSE_API_KEY = "..."
PERPLEXITY_API_KEY = "..."
EXA_API_KEY = "..."
LINKUP_API_KEY = "..."

SYRACUSE_BASE_URL = "https://syracuse.1145.am"  # optional, this is the default

# JSON array of locations shown in the location dropdown
LOCATIONS_JSON = '["Asia Pacific", "Europe", "LATAM", "North America"]'

# Nested JSON object: { "TOP_CATEGORY": { "Sub": ["leaf", ...] } }
CATEGORIES_JSON = '{...}'

# JSON array of company names for the Randomize button in Company mode
COMPANIES_JSON = '["Acme Corp", "Widgets Inc"]'

# Optional: require login
[credentials]
username = "password"
```

All API keys are optional — if a key is missing or empty, that provider will return an error when queried. Leave a key as `""` to effectively disable a provider.

### Run

```bash
uv run streamlit run app.py
```

## Usage

1. Select which **sources** to query using the checkboxes in the sidebar.
2. Choose **Category** or **Company** search mode.
3. Enter a category + location (or company name), then click **Get News**.
4. Results appear in side-by-side columns — one per active source.

In Category mode, the query window is the last 90 days. The category field is free-text, so you can enter anything — not just the predefined taxonomy values.

## Deployment

The app is designed to deploy on [Streamlit Community Cloud](https://streamlit.io/cloud). Set secrets via the Streamlit Cloud secrets UI rather than committing `.streamlit/secrets.toml`.
