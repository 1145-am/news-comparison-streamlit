import random
import time

import httpx
import streamlit as st

st.set_page_config(layout="wide", page_title="News Comparison")

from config import LOCATIONS, CATEGORIES, COMPANIES  # noqa: E402
from providers import PROVIDER_CONFIG, fetch_syracuse_story  # noqa: E402


# --- Auth ---


def check_password():
    if st.session_state.get("authenticated"):
        return True

    credentials = st.secrets.get("credentials", {})
    if not credentials:
        return True

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


# --- Display ---


@st.dialog("Story Detail", width="large")
def show_syracuse_story_dialog(uri: str):
    try:
        st.json(fetch_syracuse_story(uri))
    except Exception as e:
        st.error(f"Failed to load story: {e}")


def render_syracuse_results(data: dict):
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
        st.markdown(f"[Source]({url})" if url else "No source URL")
        if uri := story.get("uri", ""):
            if st.button("View in Syracuse", key=f"syracuse_{uri}"):
                show_syracuse_story_dialog(uri)
        st.divider()


def render_articles(articles: list):
    st.markdown(f"**{len(articles)} articles found** (showing up to 20)")
    for article in articles[:20]:
        st.markdown(f"**{article['headline']}**")
        st.caption(
            f"{article.get('published_date', 'N/A')} | "
            f"{article.get('published_by', 'N/A')}"
        )
        st.write(article.get("summary_text", ""))
        if url := article.get("document_url", ""):
            st.markdown(f"[Source]({url})")
        st.divider()


RENDER_FUNCS = {
    "syracuse": render_syracuse_results,
    "perplexity": render_articles,
    "exa": render_articles,
    "linkup": render_articles,
}


# --- Helpers ---


def pick_random_category(categories):
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
        return f"{random.choice(leaves)} ({top} - {second})"


# --- Session state ---

_STATE_DEFAULTS = {
    "search_mode": "Category",
    "company_text": "",
    "category_text": "",
    "all_industries": False,
    "all_locations": False,
    "location": LOCATIONS[0] if LOCATIONS else "",
    "use_syracuse": True,
    "use_perplexity": False,
    "use_exa": False,
    "use_linkup": False,
}

for key, default in _STATE_DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = default

for p in PROVIDER_CONFIG:
    if p["data_key"] not in st.session_state:
        st.session_state[p["data_key"]] = None


# --- UI ---

st.title("News Comparison")
st.markdown(
    "Compare news from Syracuse, Perplexity, Exa, and Linkup side by side. "
    "Search by procurement category and location, or by company name. "
    "Click 'Randomize' to pick a random category or company. "
    "Shows news up to 90 days old."
)

with st.sidebar:
    st.subheader("Sources")
    for p in PROVIDER_CONFIG:
        st.checkbox(p["label"], key=f"use_{p['key']}")

search_mode = st.radio("Search by", ["Category", "Company"], horizontal=True, key="search_mode")

if search_mode == "Category":
    st.button("Randomize", on_click=lambda: st.session_state.update({
        "category_text": pick_random_category(CATEGORIES),
        "location": random.choice(LOCATIONS) if LOCATIONS else "",
        "all_industries": False,
        "all_locations": False,
    }))

    col_category, col_in, col_location = st.columns([6, 0.3, 2])
    st.markdown("Feel free to change the category and location how you want.")

    with col_category:
        st.text_input("Category", key="category_text", disabled=st.session_state["all_industries"])
        st.checkbox("All industries", key="all_industries")
    with col_in:
        st.markdown("<div style='padding-top:2.35rem; text-align:center;'>in</div>", unsafe_allow_html=True)
    with col_location:
        st.selectbox("Location", options=LOCATIONS, key="location", disabled=st.session_state["all_locations"])
        st.checkbox("All locations", key="all_locations")

    has_industry = st.session_state["all_industries"] or bool(st.session_state["category_text"].strip())
    has_location = st.session_state["all_locations"] or bool(st.session_state["location"])
    get_news_disabled = not (has_industry and has_location)

else:
    st.button("Randomize", on_click=lambda: st.session_state.update({
        "company_text": random.choice(COMPANIES) if COMPANIES else ""
    }))
    st.text_input("Company name", key="company_text")
    get_news_disabled = not bool(st.session_state["company_text"].strip())

active_providers = [p for p in PROVIDER_CONFIG if st.session_state.get(f"use_{p['key']}")]

if not active_providers:
    st.warning("Select at least one source in the sidebar.")

if st.button("Get News", disabled=get_news_disabled or not active_providers):
    for p in PROVIDER_CONFIG:
        st.session_state[p["data_key"]] = None

    for col, provider in zip(st.columns(len(active_providers)), active_providers):
        with col:
            with st.spinner(f"Querying {provider['label']} ..."):
                try:
                    t0 = time.time()
                    if search_mode == "Company":
                        result = provider["fetch_company"](st.session_state["company_text"].strip())
                    else:
                        industry = "All" if st.session_state["all_industries"] else st.session_state["category_text"].strip()
                        location = "All" if st.session_state["all_locations"] else st.session_state["location"]
                        result = provider["fetch_category"](industry, location)
                    st.session_state[provider["data_key"]] = result
                    st.session_state[f"{provider['key']}_elapsed"] = time.time() - t0
                except httpx.HTTPStatusError as e:
                    st.error(f"{provider['label']} error ({e.response.status_code}): {e.response.text}")
                except Exception as e:
                    st.error(f"{provider['label']} error: {e}")

providers_with_results = [p for p in PROVIDER_CONFIG if st.session_state.get(p["data_key"]) is not None]

if providers_with_results:
    for col, provider in zip(st.columns(len(providers_with_results)), providers_with_results):
        with col:
            st.subheader(provider["label"])
            elapsed = st.session_state.get(f"{provider['key']}_elapsed", 0)
            st.caption(f"Query took {elapsed:.1f}s")
            RENDER_FUNCS[provider["key"]](st.session_state[provider["data_key"]])
