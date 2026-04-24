import streamlit as st
import pandas as pd
import json
from datetime import date

st.set_page_config(
    page_title="H2 Project Ranking Engine",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Custom CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

  .main-header {
    background: linear-gradient(135deg, #01696f 0%, #0c4e54 100%);
    color: white; padding: 2rem 2.5rem; border-radius: 12px;
    margin-bottom: 2rem;
  }
  .main-header h1 { margin: 0; font-size: 2rem; font-weight: 700; }
  .main-header p  { margin: 0.4rem 0 0; opacity: 0.85; font-size: 1rem; }

  .section-card {
    background: #f9f8f5; border: 1px solid #dcd9d5;
    border-radius: 10px; padding: 1.5rem; margin-bottom: 1.5rem;
  }
  .section-title {
    font-size: 1rem; font-weight: 700; color: #01696f;
    text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 1rem;
  }

  .score-card {
    background: white; border: 1px solid #dcd9d5;
    border-radius: 10px; padding: 1.2rem 1.5rem;
    margin-bottom: 0.8rem; box-shadow: 0 2px 8px rgba(0,0,0,0.05);
  }
  .score-label { font-size: 0.78rem; font-weight: 600; color: #7a7974;
                 text-transform: uppercase; letter-spacing: 0.06em; }
  .score-value { font-size: 2rem; font-weight: 700; color: #01696f; line-height: 1.2; }
  .score-max   { font-size: 0.85rem; color: #bab9b4; }

  .rating-A { background:#d4efcc; color:#1a5c10; }
  .rating-B { background:#d6eaf8; color:#0b4d80; }
  .rating-C { background:#fef9c3; color:#7a5c00; }
  .rating-D { background:#fde8e8; color:#7a1c1c; }
  .rating-badge {
    display:inline-block; font-size:1.2rem; font-weight:700;
    padding:0.4rem 1.2rem; border-radius:6px; margin-bottom:0.5rem;
  }

  .stButton>button {
    background: #01696f; color: white; border: none;
    border-radius: 8px; padding: 0.65rem 2rem;
    font-weight: 600; font-size: 1rem; width: 100%;
    transition: background 0.2s;
  }
  .stButton>button:hover { background: #0c4e54; }

  div[data-testid="stSelectbox"] label,
  div[data-testid="stNumberInput"] label,
  div[data-testid="stTextInput"] label,
  div[data-testid="stDateInput"] label,
  div[data-testid="stTextArea"] label,
  div[data-testid="stToggle"] label {
    font-weight: 600; font-size: 0.9rem; color: #28251d;
  }

  .stProgress > div > div { background-color: #01696f; }

  /* Minimal View/Modify panel */
  div[data-testid="stExpander"] {
    margin-top: -0.2rem;
    margin-bottom: 0.9rem;
  }
  div[data-testid="stExpander"] details {
    border: 1px solid #e4e1dc;
    border-radius: 8px;
    background: #ffffff;
  }
  div[data-testid="stExpander"] summary {
    padding-top: 0.1rem !important;
    padding-bottom: 0.1rem !important;
  }
  div[data-testid="stExpander"] summary p {
    font-size: 0.76rem !important;
    font-weight: 700 !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #7a7974 !important;
  }

  .vm-summary {
    background: #fbfbf9;
    border: 1px solid #e7e4df;
    border-radius: 8px;
    padding: 0.8rem 1rem;
    margin-bottom: 0.75rem;
  }
  .vm-summary-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 1rem;
    font-size: 0.88rem;
    color: #28251d;
    margin-bottom: 0.35rem;
  }
  .vm-summary-row:last-child { margin-bottom: 0; }
  .vm-muted {
    color: #7a7974;
    font-size: 0.82rem;
  }
</style>
""", unsafe_allow_html=True)

# ── Scoring rules ────────────────────────────────────────────────────────────
APPLICATIONS = {
    "PtP":            {"storage_required": 1,   "viability": 0.5},
    "E-Saf":          {"storage_required": 0.5, "viability": 1},
    "E-Methanol":     {"storage_required": 0.5, "viability": 1},
    "E-Ammonia":      {"storage_required": 0.5, "viability": 1},
    "Iron Reduction": {"storage_required": 0.5, "viability": 1},
    "Heating":        {"storage_required": 0.5, "viability": 0.5},
    "HRS":            {"storage_required": 1,   "viability": 0.5},
    "Others":         {"storage_required": 0.5, "viability": 0.5},
}

NATIONAL_PRIORITY = {"Yes": 1, "No": 0, "Not sure": 0.5}
CONTRACT_SIGNED   = {"Yes": 1, "A Few": 0.5, "Not Any": 0}
H2_SOURCE         = {"Produced Onsite": 1, "Purchased via Pipeline": 0, "Purchased Other": 1}
PPA_SIGNED        = {"Yes, self-production": 1, "Yes, with others": 1, "No": 0}
POWER_SOURCE      = {"Onsite-wind and solar": 1, "Hydro and Nuclear": 0.5,
                     "Stable Grid": 0.5, "Dynamic Grid": 1}
OFFTAKER          = {"Yes, Binding": 1, "Yes, Self Consumption": 1, "Yes, MoU": 0.5, "No": 0}
LAND_AREA         = {"Yes": 1, "No": 0, "In Process": 0.5}
PERMITS           = {"Permitted": 1, "Applied": 0.5, "No Update": 0}
ENG_MATURITY      = {"Pre-Feed": 0.5, "Feed": 1, "Waiting FID": 1, "FID": 1,
                     "Under Construction": 0.5, "Operational": 0}
H2_DNA            = {"Yes": 1, "50-50": 0.5, "No": 0}
TRACK_RECORD      = {"Startup": 0, "Multiple H2 projects": 0.5, "Industrial giants": 1}
INNOVATION        = {"Yes": 1, "Prefer not to": 0, "May be": 0.5}
FOOTPRINT         = {"Yes": 1, "Not so much": 0.5, "Not at all": 0}
SAFETY            = {"Yes, absolutely": 1, "Preferred": 0.5, "Minimum": 0}
GEO_CONSTRAINT    = {"No constraints": 1, "Difficult": 0, "Not sure": 0.5}
COUNTRY_FIT       = {"Yes": 1, "No": 0, "Not Sure": 0.5}

REGIONS = ["Europe", "Middle East", "North America", "South America", "Asia", "Pacific", "Africa"]

RATING_DESC = {
    "A": ("Very Strong Fit", "This project is an excellent candidate. High priority for engagement."),
    "B": ("Promising",        "Good fit with some areas to develop. Engage and monitor closely."),
    "C": ("Moderate",         "Mixed signals. Worth tracking but not a top priority right now."),
    "D": ("Weak Fit",         "Significant gaps. Low priority unless context changes."),
}

RATING_COLOR = {"A": "rating-A", "B": "rating-B", "C": "rating-C", "D": "rating-D"}

CATEGORY_LABELS = {
    "storage_required": "Storage Required",
    "viability": "Viability",
    "readiness": "Readiness",
    "strategic_fit": "Strategic Fit",
}

QUESTION_COMPONENTS = {
    "q1":  ["Storage Required", "Application Viability"], #check with project status
    "q2":  ["country_fit"],
    "q3":  ["national_priority"],
    "q4":  [],
    "q5":  ["funding"],
    "q6":  [],
    "q7":  ["h2_source"],
    "q8":  [],
    "q9":  ["ppa_signed"],
    "q10": ["power_source"],
    "q11": ["h2_quantity"],
    "q12": ["contract_signed"],
    "q13": ["offtaker"],
    "q14": ["land_area"],
    "q15": ["permits"],
    "q16": ["eng_maturity"],
    "q17": ["h2_dna"],
    "q18": ["track_record"],
    "q19": ["innovation"],
    "q20": ["footprint"],
    "q21": ["safety"],
    "q22": ["geo_constraint"],
}

QUESTION_NOTES = {
    "q1":  "This question contributes to two categories: storage need and viability.",
    "q4":  "Used together with funding secured to calculate the funding score.",
    "q5":  "This score is calculated from total project cost and funding secured.",
    "q6":  "Captured for context only. It does not affect the current scoring model.",
    "q8":  "Captured for context only. It does not affect the current scoring model.",
}

QUESTION_TEXT = {
    "q1":  "1. Application area?",
    "q2":  "2. Country a good fit?",
    "q3":  "3. Is it the project of national priority?",
    "q4":  "4. Total project cost (Mil. €)",
    "q5":  "5. Funding secured (Mil. €)",
    "q6":  "6. Funded by government / grants?",
    "q7":  "7. Hydrogen Source?",
    "q8":  "8. Electrolyzer Size (MW)",
    "q9":  "9. Power / H2 purchase agreement signed?",
    "q10": "10. Power Source?",
    "q11": "11. Quantity of H2 to be stored (tonnes)",
    "q12": "12. Contract signed with technology supplier?",
    "q13": "13. Offtaker found & contract signed?",
    "q14": "14. Land area secured?",
    "q15": "15. Permitting status?",
    "q16": "16. Engineering Maturity / Project Stage?",
    "q17": "17. Is H2 in their DNA?",
    "q18": "18. Developer track record?",
    "q19": "19. Open to innovative solutions?",
    "q20": "20. Footprint constraint?",
    "q21": "21. Safety a big deal?",
    "q22": "22. Geological constraints?",
}

# ── Defaults ────────────────────────────────────────────────────────────────
DEFAULTS = {
    "project_name": "",
    "evaluated_by": "",
    "region": REGIONS[0],
    "eval_date": date.today(),
    "application": list(APPLICATIONS.keys())[0],
    "country_fit": list(COUNTRY_FIT.keys())[0],
    "national_prio": list(NATIONAL_PRIORITY.keys())[0],
    "total_cost": 0.0,
    "funding_secured": 0.0,
    "gov_funded": "Yes",
    "h2_source": list(H2_SOURCE.keys())[0],
    "electrolyzer": 0.0,
    "ppa_signed": list(PPA_SIGNED.keys())[0],
    "power_source": list(POWER_SOURCE.keys())[0],
    "h2_quantity": 0.0,
    "contract_signed": list(CONTRACT_SIGNED.keys())[0],
    "offtaker": list(OFFTAKER.keys())[0],
    "land_area": list(LAND_AREA.keys())[0],
    "permits": list(PERMITS.keys())[0],
    "eng_maturity": list(ENG_MATURITY.keys())[0],
    "h2_dna": list(H2_DNA.keys())[0],
    "track_record": list(TRACK_RECORD.keys())[0],
    "innovation": list(INNOVATION.keys())[0],
    "footprint": list(FOOTPRINT.keys())[0],
    "safety": list(SAFETY.keys())[0],
    "geo_constraint": list(GEO_CONSTRAINT.keys())[0],
}

for key, value in DEFAULTS.items():
    st.session_state.setdefault(key, value)

for qid in QUESTION_TEXT:
    st.session_state.setdefault(f"override_{qid}", False)
    st.session_state.setdefault(f"comment_{qid}", "")

# ── Helper functions ────────────────────────────────────────────────────────
def funding_score(total, secured):
    if total is None or total == 0:
        return 0
    ratio = (secured or 0) / total
    if ratio < 0.2:
        return 0
    if ratio < 0.6:
        return 0.5
    return 1

def quantity_score(qty):
    if qty is None:
        return 0
    if qty < 1:
        return 0
    if qty < 5:
        return 0.5
    if qty < 15:
        return 1
    return 0.5

def get_current_answers():
    total_cost = st.session_state.get("total_cost", 0.0)
    funding_secured = st.session_state.get("funding_secured", 0.0)
    h2_quantity = st.session_state.get("h2_quantity", 0.0)

    return {
        "application":       st.session_state.get("application", "Others"),
        "country_fit":       st.session_state.get("country_fit", "Yes"),
        "national_priority": st.session_state.get("national_prio", "Yes"),
        "total_cost":        total_cost if total_cost > 0 else None,
        "funding_secured":   funding_secured if funding_secured > 0 else None,
        "gov_funded":        st.session_state.get("gov_funded", "Yes"),
        "h2_source":         st.session_state.get("h2_source", "Produced Onsite"),
        "electrolyzer":      st.session_state.get("electrolyzer", 0.0),
        "ppa_signed":        st.session_state.get("ppa_signed", "Yes, self-production"),
        "power_source":      st.session_state.get("power_source", "Onsite-wind and solar"),
        "h2_quantity":       h2_quantity if h2_quantity > 0 else None,
        "contract_signed":   st.session_state.get("contract_signed", "Yes"),
        "offtaker":          st.session_state.get("offtaker", "Yes, Binding"),
        "land_area":         st.session_state.get("land_area", "Yes"),
        "permits":           st.session_state.get("permits", "Permitted"),
        "eng_maturity":      st.session_state.get("eng_maturity", "Feed"),
        "h2_dna":            st.session_state.get("h2_dna", "Yes"),
        "track_record":      st.session_state.get("track_record", "Industrial giants"),
        "innovation":        st.session_state.get("innovation", "Yes"),
        "footprint":         st.session_state.get("footprint", "Yes"),
        "safety":            st.session_state.get("safety", "Yes, absolutely"),
        "geo_constraint":    st.session_state.get("geo_constraint", "No constraints"),
    }

def build_components(answers):
    app = answers.get("application", "Others")
    app_s = APPLICATIONS.get(app, {"storage_required": 0.5, "viability": 0.5})

    return {
        "application_storage": {
            "id": "application_storage",
            "question": "q1",
            "label": "Storage need contribution",
            "category": "storage_required",
            "score": app_s["storage_required"],
            "max": 1.0,
        },
        "application_viability": {
            "id": "application_viability",
            "question": "q1",
            "label": "Viability contribution",
            "category": "viability",
            "score": app_s["viability"],
            "max": 1.0,
        },
        "country_fit": {
            "id": "country_fit",
            "question": "q2",
            "label": "Country fit",
            "category": "viability",
            "score": COUNTRY_FIT.get(answers.get("country_fit"), 0),
            "max": 1.0,
        },
        "national_priority": {
            "id": "national_priority",
            "question": "q3",
            "label": "National priority",
            "category": "viability",
            "score": NATIONAL_PRIORITY.get(answers.get("national_priority"), 0),
            "max": 1.0,
        },
        "funding": {
            "id": "funding",
            "question": "q5",
            "label": "Funding ratio",
            "category": "viability",
            "score": funding_score(answers.get("total_cost"), answers.get("funding_secured")),
            "max": 1.0,
        },
        "h2_source": {
            "id": "h2_source",
            "question": "q7",
            "label": "Hydrogen source",
            "category": "readiness",
            "score": H2_SOURCE.get(answers.get("h2_source"), 0),
            "max": 1.0,
        },
        "ppa_signed": {
            "id": "ppa_signed",
            "question": "q9",
            "label": "PPA / agreement signed",
            "category": "readiness",
            "score": PPA_SIGNED.get(answers.get("ppa_signed"), 0),
            "max": 1.0,
        },
        "power_source": {
            "id": "power_source",
            "question": "q10",
            "label": "Power source",
            "category": "strategic_fit",
            "score": POWER_SOURCE.get(answers.get("power_source"), 0),
            "max": 1.0,
        },
        "h2_quantity": {
            "id": "h2_quantity",
            "question": "q11",
            "label": "H2 quantity",
            "category": "storage_required",
            "score": quantity_score(answers.get("h2_quantity")),
            "max": 1.0,
        },
        "contract_signed": {
            "id": "contract_signed",
            "question": "q12",
            "label": "Contract signed",
            "category": "readiness",
            "score": CONTRACT_SIGNED.get(answers.get("contract_signed"), 0),
            "max": 1.0,
        },
        "offtaker": {
            "id": "offtaker",
            "question": "q13",
            "label": "Offtaker",
            "category": "viability",
            "score": OFFTAKER.get(answers.get("offtaker"), 0),
            "max": 1.0,
        },
        "land_area": {
            "id": "land_area",
            "question": "q14",
            "label": "Land secured",
            "category": "readiness",
            "score": LAND_AREA.get(answers.get("land_area"), 0),
            "max": 1.0,
        },
        "permits": {
            "id": "permits",
            "question": "q15",
            "label": "Permits",
            "category": "viability",
            "score": PERMITS.get(answers.get("permits"), 0),
            "max": 1.0,
        },
        "eng_maturity": {
            "id": "eng_maturity",
            "question": "q16",
            "label": "Engineering maturity",
            "category": "readiness",
            "score": ENG_MATURITY.get(answers.get("eng_maturity"), 0),
            "max": 1.0,
        },
        "h2_dna": {
            "id": "h2_dna",
            "question": "q17",
            "label": "H2 DNA",
            "category": "strategic_fit",
            "score": H2_DNA.get(answers.get("h2_dna"), 0),
            "max": 1.0,
        },
        "track_record": {
            "id": "track_record",
            "question": "q18",
            "label": "Track record",
            "category": "strategic_fit",
            "score": TRACK_RECORD.get(answers.get("track_record"), 0),
            "max": 1.0,
        },
        "innovation": {
            "id": "innovation",
            "question": "q19",
            "label": "Innovation openness",
            "category": "strategic_fit",
            "score": INNOVATION.get(answers.get("innovation"), 0),
            "max": 1.0,
        },
        "footprint": {
            "id": "footprint",
            "question": "q20",
            "label": "Footprint constraint",
            "category": "storage_required",
            "score": FOOTPRINT.get(answers.get("footprint"), 0),
            "max": 1.0,
        },
        "safety": {
            "id": "safety",
            "question": "q21",
            "label": "Safety importance",
            "category": "storage_required",
            "score": SAFETY.get(answers.get("safety"), 0),
            "max": 1.0,
        },
        "geo_constraint": {
            "id": "geo_constraint",
            "question": "q22",
            "label": "Geological constraints",
            "category": "storage_required",
            "score": GEO_CONSTRAINT.get(answers.get("geo_constraint"), 0),
            "max": 1.0,
        },
    }

def resolve_components(components):
    resolved = {}
    for comp_id, comp in components.items():
        qid = comp["question"]
        manual_key = f"manual_{comp_id}"
        override_key = f"override_{qid}"

        if manual_key not in st.session_state or not st.session_state.get(override_key, False):
            st.session_state[manual_key] = float(comp["score"])

        score = st.session_state[manual_key] if st.session_state.get(override_key, False) else comp["score"]
        score = max(0.0, min(float(score), float(comp["max"])))

        resolved[comp_id] = {**comp, "score": score, "base_score": comp["score"]}
    return resolved

def compute_scores(answers):
    components = build_components(answers)
    resolved = resolve_components(components)

    category_scores = {
        "storage_required": 0.0,
        "viability": 0.0,
        "readiness": 0.0,
        "strategic_fit": 0.0,
    }
    category_max = {
        "storage_required": 0.0,
        "viability": 0.0,
        "readiness": 0.0,
        "strategic_fit": 0.0,
    }

    for comp in resolved.values():
        category_scores[comp["category"]] += comp["score"]
        category_max[comp["category"]] += comp["max"]

    total = sum(category_scores.values())
    total_max = sum(category_max.values())
    pct = (total / total_max * 100) if total_max else 0

    if pct >= 80:
        rating = "A"
    elif pct >= 60:
        rating = "B"
    elif pct >= 40:
        rating = "C"
    else:
        rating = "D"

    return {
        "storage_required": (category_scores["storage_required"], category_max["storage_required"]),
        "viability":        (category_scores["viability"], category_max["viability"]),
        "readiness":        (category_scores["readiness"], category_max["readiness"]),
        "strategic_fit":    (category_scores["strategic_fit"], category_max["strategic_fit"]),
        "total":            (total, total_max),
        "pct":              round(pct, 1),
        "rating":           rating,
        "components":       resolved,
    }

def render_view_modify(qid):
    answers = get_current_answers()
    components = build_components(answers)
    comp_ids = QUESTION_COMPONENTS.get(qid, [])
    relevant = [components[cid] for cid in comp_ids if cid in components]
    note = QUESTION_NOTES.get(qid, "")

    with st.expander("View/Modify", expanded=False):
        if relevant:
            auto_total = sum(c["score"] for c in relevant)
            total_max = sum(c["max"] for c in relevant)

            st.markdown(
                f"""
                <div class="vm-summary">
                  <div class="vm-summary-row">
                    <span><strong>Auto score</strong></span>
                    <span>{auto_total:.1f} / {total_max:.1f}</span>
                  </div>
                  {"".join([f'<div class="vm-summary-row"><span>{c["label"]}</span><span>{c["score"]:.1f} / {c["max"]:.1f}</span></div>' for c in relevant])}
                </div>
                """,
                unsafe_allow_html=True
            )

            if note:
                st.markdown(f'<div class="vm-muted">{note}</div>', unsafe_allow_html=True)

            override_key = f"override_{qid}"
            st.toggle("Manual overwrite", key=override_key)

            if st.session_state.get(override_key, False):
                for comp in relevant:
                    manual_key = f"manual_{comp['id']}"
                    if manual_key not in st.session_state:
                        st.session_state[manual_key] = float(comp["score"])
                    st.number_input(
                        f"{comp['label']} score",
                        min_value=0.0,
                        max_value=float(comp["max"]),
                        step=0.5,
                        key=manual_key
                    )
            else:
                for comp in relevant:
                    st.session_state[f"manual_{comp['id']}"] = float(comp["score"])

            st.text_area(
                "Comment",
                key=f"comment_{qid}",
                height=75,
                placeholder="Add comment..."
            )
        else:
            if note:
                st.markdown(f'<div class="vm-muted">{note}</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="vm-muted">This question does not affect the score.</div>', unsafe_allow_html=True)

            st.text_area(
                "Comment",
                key=f"comment_{qid}",
                height=75,
                placeholder="Add comment..."
            )

def collect_question_comments():
    return {
        qid: st.session_state.get(f"comment_{qid}", "")
        for qid in QUESTION_TEXT
        if st.session_state.get(f"comment_{qid}", "").strip()
    }

def collect_active_overrides(scores):
    overrides = {}
    for comp_id, comp in scores["components"].items():
        qid = comp["question"]
        if st.session_state.get(f"override_{qid}", False):
            overrides[comp_id] = {
                "question": QUESTION_TEXT.get(qid, qid),
                "manual_score": comp["score"],
                "auto_score": comp["base_score"],
                "max": comp["max"],
            }
    return overrides

# ── UI ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
  <h1>⚡ H2 Project Ranking Engine</h1>
  <p>Evaluate and rank hydrogen projects based on viability, readiness, storage need, and strategic fit.</p>
</div>
""", unsafe_allow_html=True)

col_form, col_result = st.columns([3, 2], gap="large")

with col_form:
    # ── Project Info ────────────────────────────────────────────────────────
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">📋 Project Information</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    project_name = c1.text_input("Project Name", placeholder="e.g. Masdar Green H2", key="project_name")
    evaluated_by = c2.text_input("Evaluated by", placeholder="Your name", key="evaluated_by")
    c3, c4 = st.columns(2)
    region = c3.selectbox("Project Region", REGIONS, key="region")
    eval_date = c4.date_input("Date", value=st.session_state["eval_date"], key="eval_date")
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Application & Market ────────────────────────────────────────────────
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">🏭 Application & Market</div>', unsafe_allow_html=True)

    application = st.selectbox("1. Application area?", list(APPLICATIONS.keys()), key="application")
    render_view_modify("q1")

    country_fit = st.selectbox("2. Country a good fit?", list(COUNTRY_FIT.keys()), key="country_fit")
    render_view_modify("q2")

    national_prio = st.selectbox("3. Is it the project of national priority?", list(NATIONAL_PRIORITY.keys()), key="national_prio")
    render_view_modify("q3")

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Funding ─────────────────────────────────────────────────────────────
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">💰 Funding & Finance</div>', unsafe_allow_html=True)

    total_cost = st.number_input("4. Total project cost (Mil. €)", min_value=0.0, step=10.0, key="total_cost")
    render_view_modify("q4")

    funding_secured = st.number_input("5. Funding secured (Mil. €)", min_value=0.0, step=10.0, key="funding_secured")
    render_view_modify("q5")

    gov_funded = st.selectbox("6. Funded by government / grants?", ["Yes", "No", "Partial"], key="gov_funded")
    render_view_modify("q6")

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Technical ───────────────────────────────────────────────────────────
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">⚙️ Technical Setup</div>', unsafe_allow_html=True)

    h2_source = st.selectbox("7. Hydrogen Source?", list(H2_SOURCE.keys()), key="h2_source")
    render_view_modify("q7")

    electrolyzer = st.number_input("8. Electrolyzer Size (MW)", min_value=0.0, step=1.0, key="electrolyzer")
    render_view_modify("q8")

    ppa_signed = st.selectbox("9. Power / H2 purchase agreement signed?", list(PPA_SIGNED.keys()), key="ppa_signed")
    render_view_modify("q9")

    power_source = st.selectbox("10. Power Source?", list(POWER_SOURCE.keys()), key="power_source")
    render_view_modify("q10")

    h2_quantity = st.number_input("11. Quantity of H2 to be stored (tonnes)", min_value=0.0, step=0.5, key="h2_quantity")
    render_view_modify("q11")

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Readiness ───────────────────────────────────────────────────────────
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">📊 Project Readiness</div>', unsafe_allow_html=True)

    contract_signed = st.selectbox("12. Contract signed with technology supplier?", list(CONTRACT_SIGNED.keys()), key="contract_signed")
    render_view_modify("q12")

    offtaker = st.selectbox("13. Offtaker found & contract signed?", list(OFFTAKER.keys()), key="offtaker")
    render_view_modify("q13")

    land_area = st.selectbox("14. Land area secured?", list(LAND_AREA.keys()), key="land_area")
    render_view_modify("q14")

    permits = st.selectbox("15. Permitting status?", list(PERMITS.keys()), key="permits")
    render_view_modify("q15")

    eng_maturity = st.selectbox("16. Engineering Maturity / Project Stage?", list(ENG_MATURITY.keys()), key="eng_maturity")
    render_view_modify("q16")

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Developer ───────────────────────────────────────────────────────────
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">👤 Developer Profile</div>', unsafe_allow_html=True)

    h2_dna = st.selectbox("17. Is H2 in their DNA?", list(H2_DNA.keys()), key="h2_dna")
    render_view_modify("q17")

    track_record = st.selectbox("18. Developer track record?", list(TRACK_RECORD.keys()), key="track_record")
    render_view_modify("q18")

    innovation = st.selectbox("19. Open to innovative solutions?", list(INNOVATION.keys()), key="innovation")
    render_view_modify("q19")

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Site Constraints ────────────────────────────────────────────────────
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">🏗️ Site Constraints</div>', unsafe_allow_html=True)

    footprint = st.selectbox("20. Footprint constraint?", list(FOOTPRINT.keys()), key="footprint")
    render_view_modify("q20")

    safety = st.selectbox("21. Safety a big deal?", list(SAFETY.keys()), key="safety")
    render_view_modify("q21")

    geo_constraint = st.selectbox("22. Geological constraints?", list(GEO_CONSTRAINT.keys()), key="geo_constraint")
    render_view_modify("q22")

    st.markdown('</div>', unsafe_allow_html=True)

    submitted = st.button("🚀 Evaluate Project")

# ── Results Panel ───────────────────────────────────────────────────────────
with col_result:
    st.markdown("### 📈 Evaluation Results")

    answers = get_current_answers()
    scores = compute_scores(answers)

    rating = scores["rating"]
    rname, rdesc = RATING_DESC[rating]
    rcolor = RATING_COLOR[rating]

    # Rating badge
    st.markdown(f"""
    <div class="score-card" style="text-align:center;">
      <div class="score-label">Overall Rating</div>
      <div style="margin:0.5rem 0;">
        <span class="rating-badge {rcolor}">{rating}</span>
      </div>
      <div style="font-size:1rem;font-weight:600;color:#28251d;">{rname}</div>
      <div style="font-size:0.85rem;color:#7a7974;margin-top:0.3rem;">{rdesc}</div>
    </div>
    """, unsafe_allow_html=True)

    # Total score
    total_v, total_m = scores["total"]
    st.markdown(f"""
    <div class="score-card">
      <div class="score-label">Total Score</div>
      <div><span class="score-value">{total_v:.1f}</span>
           <span class="score-max"> / {total_m:.0f}  ({scores["pct"]}%)</span></div>
      </div>
    """, unsafe_allow_html=True)

    st.progress(scores["pct"] / 100 if scores["pct"] else 0)

    cats = [
        ("🗃️ Storage Required", "storage_required"),
        ("✅ Viability", "viability"),
        ("📋 Readiness", "readiness"),
        ("🎯 Strategic Fit", "strategic_fit"),
    ]

    for label, key in cats:
        v, m = scores[key]
        pct_cat = v / m if m > 0 else 0
        st.markdown(f"""
        <div class="score-card">
          <div class="score-label">{label}</div>
          <div><span class="score-value" style="font-size:1.4rem;">{v:.1f}</span>
               <span class="score-max"> / {m:.0f}</span></div>
        </div>
        """, unsafe_allow_html=True)
        st.progress(pct_cat)

    # Export
    if submitted and project_name:
        export_data = {
            "project_name": project_name,
            "evaluated_by": evaluated_by,
            "region": region,
            "date": str(eval_date),
            "answers": {k: str(v) for k, v in answers.items()},
            "comments": collect_question_comments(),
            "manual_overrides": collect_active_overrides(scores),
            "scores": {
                "storage_required": scores["storage_required"][0],
                "viability":        scores["viability"][0],
                "readiness":        scores["readiness"][0],
                "strategic_fit":    scores["strategic_fit"][0],
                "total":            scores["total"][0],
                "total_max":        scores["total"][1],
                "pct":              scores["pct"],
                "rating":           rating,
            }
        }

        st.download_button(
            label="⬇️ Download Evaluation (JSON)",
            data=json.dumps(export_data, indent=2),
            file_name=f"{project_name.replace(' ', '_')}_score.json",
            mime="application/json"
        )

        df_export = pd.DataFrame([{
            "Project": project_name,
            "Region": region,
            "Rating": rating,
            "Score %": scores["pct"],
            "Storage Required": scores["storage_required"][0],
            "Viability": scores["viability"][0],
            "Readiness": scores["readiness"][0],
            "Strategic Fit": scores["strategic_fit"][0],
            "Total": scores["total"][0],
        }])

        st.download_button(
            label="⬇️ Download Evaluation (CSV)",
            data=df_export.to_csv(index=False),
            file_name=f"{project_name.replace(' ', '_')}_score.csv",
            mime="text/csv"
        )

    if submitted:
        st.success("✅ Evaluation complete! Scores updated above.")
    else:
        st.info("👈 Fill in the form and click **Evaluate Project**.")
    
