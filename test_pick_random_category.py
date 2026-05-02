import sys
from unittest.mock import MagicMock, patch

# Mock streamlit before importing app so the module-level Streamlit calls are no-ops
_mock_st = MagicMock()
_mock_st.secrets.get = lambda key, default="": default
_mock_st.session_state = {}
_mock_st.button.return_value = False   # skip the "Get News" execution block
_mock_st.radio.return_value = "Company"  # skip Category UI so st.columns isn't needed
sys.modules["streamlit"] = _mock_st

from app import pick_random_category  # noqa: E402

CATEGORIES = {
    "RESINS": {
        "Non PET": ["Non PET", "Polyolefins", "Bio-based Resins"],
        "PET": ["Bottle Grade", "Fiber Grade"],
    },
    "MRO": {
        "NON OEM SPARE PARTS": [
            "NON OEM SPARE PARTS - COMPRESSORS",
            "NON OEM SPARE PARTS - PUMPS",
            "Filters",
        ],
        "Consumables": ["Lubricants", "Cleaning Supplies"],
    },
    "IT": {
        "ERP Software": ["SAP", "Oracle", "Microsoft Dynamics"],
        "Hardware": ["Servers", "Laptops"],
    },
}


def test_empty_categories_returns_empty_strings():
    assert pick_random_category({}) == ("", "")


def test_top_level_node_context_is_child_samples():
    with patch("random.random", return_value=0.1), \
         patch("random.choice", return_value="IT"), \
         patch("random.sample", return_value=["ERP Software", "Hardware"]):
        cat, ctx = pick_random_category(CATEGORIES)
    assert cat == "IT"
    assert ctx == "ERP Software, Hardware"


def test_second_level_node_context_is_leaf_samples():
    with patch("random.random", return_value=0.5), \
         patch("random.choice", side_effect=["IT", "ERP Software"]), \
         patch("random.sample", return_value=["SAP", "Oracle", "Microsoft Dynamics"]):
        cat, ctx = pick_random_category(CATEGORIES)
    assert cat == "ERP Software"
    assert ctx == "SAP, Oracle, Microsoft Dynamics"


def test_leaf_node_normal_context_is_immediate_parent():
    with patch("random.random", return_value=0.9), \
         patch("random.choice", side_effect=["IT", "ERP Software", "SAP"]):
        cat, ctx = pick_random_category(CATEGORIES)
    assert cat == "SAP"
    assert ctx == "ERP Software"


def test_leaf_node_parent_same_as_leaf_is_discarded():
    # "Non PET" leaf, parent "Non PET" → parent discarded, context = grandparent "RESINS" only
    with patch("random.random", return_value=0.9), \
         patch("random.choice", side_effect=["RESINS", "Non PET", "Non PET"]):
        cat, ctx = pick_random_category(CATEGORIES)
    assert cat == "Non PET"
    assert ctx == "RESINS"


def test_leaf_node_parent_substring_of_leaf_is_discarded():
    # "NON OEM SPARE PARTS - COMPRESSORS" contains parent "NON OEM SPARE PARTS" → parent discarded
    with patch("random.random", return_value=0.9), \
         patch("random.choice", side_effect=["MRO", "NON OEM SPARE PARTS", "NON OEM SPARE PARTS - COMPRESSORS"]):
        cat, ctx = pick_random_category(CATEGORIES)
    assert cat == "NON OEM SPARE PARTS - COMPRESSORS"
    assert ctx == "MRO"


def test_leaf_node_all_ancestors_filtered_gives_empty_context():
    # Leaf contains both grandparent and parent as substrings → context is empty
    categories = {"MRO": {"MRO SPARE PARTS": ["MRO SPARE PARTS - COMPRESSORS"]}}
    with patch("random.random", return_value=0.9), \
         patch("random.choice", side_effect=["MRO", "MRO SPARE PARTS", "MRO SPARE PARTS - COMPRESSORS"]):
        cat, ctx = pick_random_category(categories)
    assert cat == "MRO SPARE PARTS - COMPRESSORS"
    assert ctx == ""
