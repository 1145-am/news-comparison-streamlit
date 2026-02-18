import json
import random
import time
from datetime import date, timedelta
from pathlib import Path

import httpx
import runpy
import streamlit as st

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / ".venv" / "examples" / "config.py"
NUM_DAYS = 90

# Load config: local file for dev, st.secrets for deployment
if CONFIG_PATH.exists():
    config_vars = runpy.run_path(str(CONFIG_PATH))
    LOCATIONS = config_vars.get("LOCATIONS", ["North America", "Europe"])
    CATEGORIES = config_vars.get("CATEGORIES", {})
else:
    LOCATIONS = json.loads(st.secrets.get("LOCATIONS_JSON", '["North America", "Europe"]'))
    CATEGORIES = json.loads(st.secrets.get("CATEGORIES_JSON", "{}"))

SYRACUSE_API_KEY = st.secrets.get("SYRACUSE_API_KEY", "")
PERPLEXITY_API_KEY = st.secrets.get("PERPLEXITY_API_KEY", "")

SYRACUSE_BASE_URL = "https://syracuse.1145.am"
PERPLEXITY_ENDPOINT = "https://api.perplexity.ai/chat/completions"


def check_password():
    """Show a login form and return True if the user has entered valid credentials."""
    if st.session_state.get("authenticated"):
        return True

    credentials = st.secrets.get("credentials", {})
    if not credentials:
        return True  # no credentials configured, skip auth

    with st.form("login"):
        st.title("Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log in")

    if submitted:
        if credentials.get(username) == password:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Invalid username or password")

    return False


if not check_password():
    st.stop()

st.title("News Comparison")

st.markdown(
    "This app compares news results from Syracuse and Perplexity APIs side by side. "
    "Enter a procurement category and location, then click 'Get News' to see the results. "
    "You can also click 'Randomize' to fill in random categories and locations. "
    "Shows news up to 90 days old."
)
# --- API functions ---


def fetch_syracuse(industry: str, location: str) -> dict:
    """Fetch all stories from Syracuse API, following pagination."""
    headers = {"Authorization": f"Token {SYRACUSE_API_KEY}"}
    params = {"industry": industry, "location": location, "days_ago": NUM_DAYS}
    all_results = []

    url = f"{SYRACUSE_BASE_URL}/api/v1/stories/industry-location/"
    while url:
        response = httpx.get(url, headers=headers, params=params, timeout=120.0)
        response.raise_for_status()
        data = response.json()
        all_results.extend(data.get("results", []))
        url = data.get("next")
        params = None  # next URL includes query params already

    return {"count": len(all_results), "results": all_results}


def fetch_perplexity(industry: str, location: str) -> list:
    """Fetch news from Perplexity API."""
    max_date = date.today()
    min_date = max_date - timedelta(days=NUM_DAYS)

    system_command = (
        f"You are a market research analyst with deep knowledge of what a "
        f"procurement category manager in the {industry} industry needs."
    )
    user_command = (
        f"I need you to produce a list of suppliers for industry: {industry} "
        f"in location: {location}. Then find recent news articles for these suppliers. "
        "Focus on topics like corporate finance, partnerships, product innovations, "
        "supplier risk and regulatory changes that I can use in preparing my "
        "procurement strategy, risk management and supplier negotiations. "
        "For each source cited in your response, provide a separate summary of "
        "that source's content. Prioritise more recent news articles. "
        "Please output a list of JSON objects with one JSON object per source "
        "with the following fields: headline, summary_text, published_date, "
        "published_by, document_url"
    )

    payload = {
        "model": "sonar",
        "messages": [
            {"role": "system", "content": system_command},
            {"role": "user", "content": user_command},
        ],
        "response_format": {
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
                        "required": [
                            "headline", "summary_text", "published_date",
                            "published_by", "document_url",
                        ],
                    },
                },
            },
        },
        "web_search_options": {"search_context_size": "medium"},
        "search_after_date_filter": min_date.strftime("%m/%d/%Y"),
        "search_before_date_filter": max_date.strftime("%m/%d/%Y"),
    }

    response = httpx.post(
        PERPLEXITY_ENDPOINT,
        headers={"Authorization": f"Bearer {PERPLEXITY_API_KEY}"},
        json=payload,
        timeout=300.0,
    )
    response.raise_for_status()
    data = response.json()
    content = data["choices"][0]["message"]["content"]
    articles = json.loads(content)
    return sorted(articles, key=lambda x: x.get("published_date", ""), reverse=True)


# --- Display helpers ---


def render_syracuse_results(data: dict):
    """Render Syracuse stories."""
    stories = data.get("results", [])
    st.markdown(f"**{data.get('count', len(stories))} stories found** (showing up to 20)")
    for story in stories[:20]:
        st.markdown(f"**{story['headline']}**")
        st.caption(
            f"{story.get('activity_class', '')} | "
            f"{story.get('published_date', 'N/A')} | "
            f"{story.get('published_by', 'N/A')}"
        )
        extract = story.get("document_extract", "")
        if extract:
            st.write(extract[:300] + ("..." if len(extract) > 300 else ""))
        url = story.get("document_url", "")
        url_markdown = f"[Source]({url})" if url else "No source URL"
        syracuse_uri = story.get("uri", "")
        syracuse_markdown = f"[View on Syracuse]({SYRACUSE_BASE_URL}/api/v1/stories/{syracuse_uri})" if syracuse_uri else "No Syracuse URI"
        st.markdown(f"{url_markdown} | {syracuse_markdown}")
        st.divider()


def render_perplexity_results(articles: list):
    """Render Perplexity articles."""
    st.markdown(f"**{len(articles)} articles found** (showing up to 20)")
    for article in articles[:20]:
        st.markdown(f"**{article['headline']}**")
        st.caption(
            f"{article.get('published_date', 'N/A')} | "
            f"{article.get('published_by', 'N/A')}"
        )
        st.write(article.get("summary_text", ""))
        url = article.get("document_url", "")
        if url:
            st.markdown(f"[Source]({url})")
        st.divider()


# --- Category picker ---


def pick_random_category(categories):
    """Pick a random category entry."""
    tops = list(categories.keys())
    if not tops:
        return ""

    if random.random() < 0.5:
        top = random.choice(tops)
        second_map = categories[top]
        children = list(second_map.keys()) if isinstance(second_map, dict) else []
        sample = random.sample(children, min(3, len(children))) if children else []
        return f"{top} ({', '.join(sample)})" if sample else top
    else:
        top = random.choice(tops)
        second_map = categories[top]
        if not isinstance(second_map, dict) or not second_map:
            return top
        second = random.choice(list(second_map.keys()))
        leaves = second_map.get(second, [])
        if not leaves:
            return f"{second} ({top})"
        leaf = random.choice(leaves)
        return f"{leaf} ({top} - {second})"


# --- Session state ---

if "category_text" not in st.session_state:
    st.session_state["category_text"] = ""
if "location" not in st.session_state:
    st.session_state["location"] = LOCATIONS[0] if LOCATIONS else ""


def do_randomize():
    st.session_state["category_text"] = pick_random_category(CATEGORIES)
    st.session_state["location"] = random.choice(LOCATIONS) if LOCATIONS else ""


# --- UI ---

st.button("Randomize", on_click=do_randomize)

col_category, col_in, col_location = st.columns([6, 0.3, 2])

st.markdown("Feel free to change the category and location how you want.")

with col_category:
    st.text_input("Category", key="category_text")

with col_in:
    st.markdown(
        "<div style='padding-top:2.35rem; text-align:center;'>in</div>",
        unsafe_allow_html=True,
    )

with col_location:
    st.selectbox("Location", options=LOCATIONS, key="location")

if st.button("Get News", disabled=not (st.session_state["category_text"].strip() and st.session_state["location"])):
    industry = st.session_state['category_text'].strip()
    location = st.session_state["location"]
    st.markdown(f"Fetching news for **{industry}** in **{location}** ....")

    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Syracuse")
        with st.spinner("Querying Syracuse ..."):
            try:
                t0 = time.time()
                syracuse_data = fetch_syracuse(industry, location)
                elapsed = time.time() - t0
                st.caption(f"Query took {elapsed:.1f}s")
                render_syracuse_results(syracuse_data)
            except httpx.HTTPStatusError as e:
                st.error(f"Syracuse error ({e.response.status_code}): {e.response.text}")
            except Exception as e:
                st.error(f"Syracuse error: {e}")

    with col_right:
        st.subheader("Perplexity")
        with st.spinner("Querying Perplexity ..."):
            try:
                t0 = time.time()
                perplexity_articles = fetch_perplexity(industry, location)
                elapsed = time.time() - t0
                st.caption(f"Query took {elapsed:.1f}s")
                render_perplexity_results(perplexity_articles)
            except httpx.HTTPStatusError as e:
                st.error(f"Perplexity error ({e.response.status_code}): {e.response.text}")
            except Exception as e:
                st.error(f"Perplexity error: {e}")
