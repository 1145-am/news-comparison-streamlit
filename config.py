import json
from datetime import date, timedelta

import streamlit as st

NUM_DAYS = 90
MAX_DATE = date.today()
MIN_DATE = MAX_DATE - timedelta(days=NUM_DAYS)

LOCATIONS = json.loads(st.secrets.get("LOCATIONS_JSON", '["North America", "Europe"]'))
CATEGORIES = json.loads(st.secrets.get("CATEGORIES_JSON", "{}"))
COMPANIES = json.loads(st.secrets.get("COMPANIES_JSON", "[]"))

SYRACUSE_API_KEY = st.secrets.get("SYRACUSE_API_KEY", "")
PERPLEXITY_API_KEY = st.secrets.get("PERPLEXITY_API_KEY", "")
EXA_API_KEY = st.secrets.get("EXA_API_KEY", "")
LINKUP_API_KEY = st.secrets.get("LINKUP_API_KEY", "")

SYRACUSE_BASE_URL = st.secrets.get("SYRACUSE_BASE_URL", "https://syracuse.1145.am")
PERPLEXITY_ENDPOINT = "https://api.perplexity.ai/chat/completions"
