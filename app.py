import random
from pathlib import Path
import runpy
import streamlit as st

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / ".venv" / "examples" / "config.py"

# Load config
config_vars = {}
if CONFIG_PATH.exists():
    config_vars = runpy.run_path(str(CONFIG_PATH))

LOCATIONS = config_vars.get("LOCATIONS", ["North America", "Europe"])
CATEGORIES = config_vars.get("CATEGORIES", {})
INDUSTRY_PREFIXES = config_vars.get("INDUSTRY_PREFIXES", ["Packaging"])

st.title("News Comparison")


def pick_random_category(categories):
    """Pick a random category entry.

    Either a top-level key (with up to 3 randomly-selected second-level keys),
    or a leaf value (shown with its top > second-level path).
    """
    tops = list(categories.keys())
    if not tops:
        return ""

    # 50/50: top-level key or leaf item
    if random.random() < 0.5:
        # Top-level key with up to 3 random children
        top = random.choice(tops)
        second_map = categories[top]
        children = list(second_map.keys()) if isinstance(second_map, dict) else []
        sample = random.sample(children, min(3, len(children))) if children else []
        return f"{top} ({', '.join(sample)})" if sample else top
    else:
        # Leaf item with path
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


# Session state defaults
if "industry_prefix" not in st.session_state:
    st.session_state["industry_prefix"] = ""
if "category_text" not in st.session_state:
    st.session_state["category_text"] = ""
if "location" not in st.session_state:
    st.session_state["location"] = LOCATIONS[0] if LOCATIONS else ""


def do_randomize():
    st.session_state["industry_prefix"] = random.choice(INDUSTRY_PREFIXES) + ":"
    st.session_state["category_text"] = pick_random_category(CATEGORIES)
    st.session_state["location"] = random.choice(LOCATIONS) if LOCATIONS else ""


st.button("Randomize", on_click=do_randomize)

col_prefix, col_category, col_in, col_location = st.columns(
    [2, 6, 0.3, 2]
)

with col_prefix:
    st.text_input("Industry Prefix", key="industry_prefix")

with col_category:
    st.text_input("Category", key="category_text")

with col_in:
    st.markdown(
        "<div style='padding-top:2.35rem; text-align:center;'>in</div>",
        unsafe_allow_html=True,
    )

with col_location:
    st.selectbox("Location", options=LOCATIONS, key="location")