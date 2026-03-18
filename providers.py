import json
from urllib.parse import urlparse

import httpx

from config import (
    CATEGORIES, LOCATIONS,
    MIN_DATE, MAX_DATE, NUM_DAYS,
    SYRACUSE_API_KEY, SYRACUSE_BASE_URL,
    PERPLEXITY_API_KEY, PERPLEXITY_ENDPOINT,
    EXA_API_KEY, LINKUP_API_KEY,
)

# --- Syracuse ---


def fetch_syracuse_story(uri: str) -> dict:
    headers = {"Authorization": f"Token {SYRACUSE_API_KEY}"}
    url = f"{SYRACUSE_BASE_URL}/api/v1/stories/{uri}"
    response = httpx.get(url, headers=headers, timeout=30.0, follow_redirects=True)
    response.raise_for_status()
    return response.json()


def fetch_syracuse(industry: str, location: str) -> dict:
    headers = {"Authorization": f"Token {SYRACUSE_API_KEY}"}
    params = {"days_ago": NUM_DAYS}
    if industry and industry != "All":
        params["industry"] = industry
    if location and location != "All":
        params["location"] = location
    all_results = []

    url = f"{SYRACUSE_BASE_URL}/api/v1/stories/industry-location/"
    while url:
        response = httpx.get(url, headers=headers, params=params, timeout=120.0)
        response.raise_for_status()
        data = response.json()
        all_results.extend(data.get("results", []))
        if len(all_results) >= 20:
            break
        url = data.get("next")
        params = None  # next URL includes query params already

    return {"count": len(all_results), "results": all_results}


def fetch_syracuse_company(company: str) -> dict:
    headers = {"Authorization": f"Token {SYRACUSE_API_KEY}"}
    params = {"days_ago": NUM_DAYS, "org_name": company}
    all_results = []

    url = f"{SYRACUSE_BASE_URL}/api/v1/stories/organization/"
    while url:
        response = httpx.get(url, headers=headers, params=params, timeout=120.0)
        response.raise_for_status()
        data = response.json()
        all_results.extend(data.get("results", []))
        if len(all_results) >= 20:
            break
        url = data.get("next")
        params = None

    return {"count": len(all_results), "results": all_results}


# --- Perplexity ---

_PERPLEXITY_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "schema": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "headline": {"type": "string"},
                    "summary_text": {"type": "string"},
                    "published_date": {"type": "string", "format": "date-time"},
                    "published_by": {"type": "string"},
                    "document_url": {"type": "string"},
                },
                "required": ["headline", "summary_text", "published_date", "published_by", "document_url"],
            },
        },
    },
}


def _run_perplexity_query(system_prompt: str, user_prompt: str) -> list:
    payload = {
        "model": "sonar",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "response_format": _PERPLEXITY_SCHEMA,
        "web_search_options": {"search_context_size": "medium"},
        "search_after_date_filter": MIN_DATE.strftime("%m/%d/%Y"),
        "search_before_date_filter": MAX_DATE.strftime("%m/%d/%Y"),
    }
    response = httpx.post(
        PERPLEXITY_ENDPOINT,
        headers={"Authorization": f"Bearer {PERPLEXITY_API_KEY}"},
        json=payload,
        timeout=300.0,
    )
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    articles = json.loads(content)
    return sorted(articles, key=lambda x: x.get("published_date", ""), reverse=True)


def fetch_perplexity(industry: str, location: str) -> list:
    effective_industry = ", ".join(CATEGORIES.keys()) if industry == "All" else industry
    effective_location = ", ".join(LOCATIONS) if location == "All" else location

    if ',' in effective_industry:
        industries_text = f"the following industries: {effective_industry}"
        industry_context = "these industries"
    else:
        industries_text = effective_industry
        industry_context = "this industry"

    locations_text = f"the following locations: {effective_location}" if ',' in effective_location else effective_location

    system_prompt = (
        f"You are a market research analyst with deep knowledge of what a "
        f"procurement category manager in the {effective_industry} industry needs."
    )
    user_prompt = (
        f"I am a procurement category manager for {industries_text} in {locations_text}. "
        f"First identify top 5-7 suppliers in {industry_context}, then find recent news about them "
        f"and relevant industry news. "
        f"Focus on finance, partnerships, innovations, risks, and regulatory changes "
        f"for procurement strategy and supplier negotiations. "
        f"Output JSON objects with: headline, summary_text, published_date, published_by, document_url"
    )
    return _run_perplexity_query(system_prompt, user_prompt)


def fetch_perplexity_company(company: str) -> list:
    system_prompt = (
        "You are a market research analyst helping a procurement team assess supplier risk and opportunity."
    )
    user_prompt = (
        f"I need you to find recent news articles for {company}. "
        "Focus on topics like corporate finance, partnerships, product innovations, supplier risk and regulatory changes "
        "that I can use in preparing my procurement strategy, risk management and supplier negotiations. "
        "For each source cited in your response, provide a separate summary of that source's content. "
        "Prioritise more recent news articles. "
        "Please output a list of JSON objects with one JSON object per source with the following fields: "
        "headline, summary_text, published_date, published_by, document_url"
    )
    return _run_perplexity_query(system_prompt, user_prompt)


# --- Exa ---


def _run_exa_query(query: str) -> list:
    from exa_py import Exa
    client = Exa(EXA_API_KEY)
    response = client.search(
        query,
        end_published_date=MAX_DATE.isoformat(),
        start_published_date=MIN_DATE.isoformat(),
        category="news",
        num_results=20,
        type="auto",
        contents={"highlights": True},
    )
    articles = []
    for item in response.results:
        try:
            parsed_url = urlparse(item.url)
            top_highlight = item.highlights[0] if item.highlights else ""
            author_string = f" ({item.author})" if item.author else ""
            articles.append({
                "headline": item.title,
                "published_date": item.published_date or "",
                "summary_text": top_highlight.replace("\n", " "),
                "published_by": f"{parsed_url.netloc}{author_string}",
                "document_url": item.url,
            })
        except Exception:
            continue
    return sorted(articles, key=lambda x: x.get("published_date", ""), reverse=True)


def fetch_exa(industry: str, location: str) -> list:
    effective_industry = ", ".join(CATEGORIES.keys()) if industry == "All" else industry
    effective_location = ", ".join(LOCATIONS) if location == "All" else location
    query = (
        f"Fetch recent news related to the {effective_industry} industry in {effective_location}. "
        "Focus on market trends, regulatory updates, major deals, innovations, and key players. "
        "Only include content from credible business, trade, or regional news sources."
    )
    return _run_exa_query(query)


def fetch_exa_company(company: str) -> list:
    query = (
        f"Find recent news mentioning {company}. "
        "Prioritize product launches, strategic moves, M&A, financial performance, regulatory issues. "
        "Only include information from trustworthy business or industry-specific media outlets."
    )
    return _run_exa_query(query)


# --- Linkup ---

_LINKUP_SCHEMA = json.dumps({
    "type": "object",
    "properties": {
        "articles": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "headline": {"type": "string"},
                    "publication_date": {"type": "string", "format": "date-time"},
                    "summary": {"type": "string"},
                    "source": {"type": "string"},
                    "url": {"type": "string"},
                },
                "required": ["headline", "publication_date", "source", "url"],
            },
        }
    },
    "required": ["articles"],
})


def _run_linkup_query(query: str) -> list:
    from linkup import LinkupClient
    client = LinkupClient(api_key=LINKUP_API_KEY)
    response = client.search(
        query=query,
        depth="standard",
        output_type="structured",
        structured_output_schema=_LINKUP_SCHEMA,
        include_images=False,
        from_date=MIN_DATE,
        to_date=MAX_DATE,
    )
    items = response["articles"] if isinstance(response, dict) else response.articles
    articles = []
    for item in items:
        try:
            item_dict = item if isinstance(item, dict) else vars(item)
            articles.append({
                "headline": item_dict["headline"],
                "published_date": item_dict.get("publication_date", ""),
                "summary_text": item_dict.get("summary", ""),
                "published_by": item_dict["source"],
                "document_url": item_dict["url"],
            })
        except Exception:
            continue
    return sorted(articles, key=lambda x: x.get("published_date", ""), reverse=True)


def fetch_linkup(industry: str, location: str) -> list:
    effective_industry = ", ".join(CATEGORIES.keys()) if industry == "All" else industry
    effective_location = ", ".join(LOCATIONS) if location == "All" else location
    query = (
        f"Fetch recent news related to the {effective_industry} industry in {effective_location}. "
        "Focus on market trends, regulatory updates, major deals, innovations, and key players. "
        "Return source titles, publication dates, and a short summary for each news item. "
        "Only include content from credible business, trade, or regional news sources."
    )
    return _run_linkup_query(query)


def fetch_linkup_company(company: str) -> list:
    query = (
        f"Find recent news mentioning {company}. "
        "Prioritize product launches, strategic moves, M&A, financial performance, regulatory issues. "
        "Summarize each relevant article in 2-3 sentences, including source, date, and URL. "
        "Only include information from trustworthy business or industry-specific media outlets."
    )
    return _run_linkup_query(query)


# --- Provider registry ---

PROVIDER_CONFIG = [
    {
        "key": "syracuse",
        "label": "Syracuse",
        "data_key": "syracuse_data",
        "fetch_category": fetch_syracuse,
        "fetch_company": fetch_syracuse_company,
    },
    {
        "key": "perplexity",
        "label": "Perplexity",
        "data_key": "perplexity_articles",
        "fetch_category": fetch_perplexity,
        "fetch_company": fetch_perplexity_company,
    },
    {
        "key": "exa",
        "label": "Exa",
        "data_key": "exa_articles",
        "fetch_category": fetch_exa,
        "fetch_company": fetch_exa_company,
    },
    {
        "key": "linkup",
        "label": "Linkup",
        "data_key": "linkup_articles",
        "fetch_category": fetch_linkup,
        "fetch_company": fetch_linkup_company,
    },
]
