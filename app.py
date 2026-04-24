# ⚡ H2 Project Ranking Engine
# Evaluate and rank hydrogen projects based on project viability and Delphy chance to win.

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

st.markdown("""
<style>
/* ── Global ── */
body { font-family: 'Inter', sans-serif; }
.main-header { padding: 1.5rem 0 1rem 0; border-bottom: 2px solid #e0e0e0; margin-bottom: 1.5rem; }
.main-header h1 { font-size: 1.8rem; font-weight: 700; color: #1a1a2e; margin: 0; }
.main-header p { color: #5a5a7a; margin: 0.3rem 0 0 0; font-size: 0.95rem; }
.section-card { background: #f8f9ff; border: 1px solid #e2e4f0; border-radius: 12px;
                padding: 1.2rem 1.4rem; margin-bottom: 1.2rem; }
.section-title { font-size: 1.05rem; font-weight: 700; color: #1a1a2e;
                 margin-bottom: 1rem; padding-bottom: 0.5rem; border-bottom: 1px solid #e2e4f0; }
.score-card { background: white; border: 1px solid #e2e4f0; border-radius: 10px;
              padding: 1rem; margin-bottom: 0.8rem; }
.score-label { font-size: 0.8rem; font-weight: 600; text-transform: uppercase;
               letter-spacing: 0.05em; color: #5a5a7a; margin-bottom: 0.3rem; }
.score-value { font-size: 1.8rem; font-weight: 700; color: #1a1a2e; }
.score-max { font-size: 0.95rem; color: #5a5a7a; }
.rating-badge { display: inline-block; font-size: 2.5rem; font-weight: 800;
                padding: 0.3rem 1rem; border-radius: 8px; }
.rating-A { background: #d4edda; color: #155724; }
.rating-B { background: #d1ecf1; color: #0c5460; }
.rating-C { background: #fff3cd; color: #856404; }
.rating-D { background: #f8d7da; color: #721c24; }
.vm-summary { background: #f0f2ff; border-radius: 8px; padding: 0.8rem 1rem; margin-bottom: 0.5rem; }
.vm-summary-row { display: flex; justify-content: space-between; font-size: 0.85rem; padding: 0.15rem 0; }
.vm-muted { font-size: 0.8rem; color: #888; font-style: italic; margin-bottom: 0.5rem; }
.bracket-tag { display: inline-block; font-size: 0.7rem; font-weight: 600;
               padding: 0.15rem 0.5rem; border-radius: 20px; margin-left: 0.4rem; vertical-align: middle; }
.bracket-viability { background: #d4edda; color: #155724; }
.bracket-delphy { background: #cce5ff; color: #004085; }
.calc-note { font-size: 0.72rem; color: #888; font-style: italic; margin-top: 0.4rem; }
</style>
""", unsafe_allow_html=True)

# ── Scoring rules ──────────────────────────────────────────────────────────────

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

STABLE_POLICY      = {"Yes": 1, "No": 0, "Cannot say": 0.5}
VALLOUREC_REACH    = {"Yes": 1, "No": 0, "Progressive": 0.5}
NATIONAL_PRIORITY  = {"Yes": 1, "No": 0, "Not sure": 0.5}
GOV_FUNDED         = {"Yes": 1, "No": 0, "Applied": 0.5}
H2_SOURCE_OPTIONS  = {"Produced on site": 1, "Purchased via Pipeline": 0, "Purchased through other way": 0.5}
PIPELINE_TYPE      = {"Dedicated through a producer": 1, "Connected to network": 0, "Not sure": 0.5}
PPA_SIGNED         = {"Yes, self-production": 1, "Yes, with others": 1, "No": 0}
H2_PURCHASE_SIGNED = {"Yes": 1, "No": 0, "In negotiation": 0.5}
OTHER_PURCHASE_AGR = {"Yes": 1, "No": 0, "In negotiation": 0.5}
POWER_SOURCE       = {"Onsite-wind and solar": 1, "Hydro and Nuclear": 0.5, "Stable Grid": 0.5, "Dynamic Grid": 1}
CONTRACT_SIGNED    = {"Yes": 1, "A Few": 0.5, "Not Any": 0}
OFFTAKER           = {"Yes, Binding": 1, "Yes, Self Consumption": 1, "Yes, MoU": 0.5, "No": 0}
LAND_AREA          = {"Yes": 1, "No": 0, "In Process": 0.5}
PERMITS            = {"Permitted": 1, "Applied": 0.5, "No Update": 0}
ENG_MATURITY       = {"Conceptual": 0.25, "Feed": 0.75, "Waiting FID less than 2 years": 0.5,
                      "Waiting more than 2 years": 1, "Under Construction": 0.5}
H2_DNA             = {"Yes": 1, "50-50": 0.5, "No": 0}
TRACK_RECORD       = {"Startup": 0, "Multiple H2 projects": 0.5, "Industrial giants": 1}
INNOVATION         = {"Yes": 1, "Prefer not to": 0, "May be": 0.5}
FOOTPRINT          = {"Yes": 1, "Not so much": 0.5, "Not at all": 0}
SAFETY             = {"Yes, absolutely": 1, "Preferred": 0.5, "Minimum": 0}
GEO_CONSTRAINT     = {"No constraints": 1, "Difficult": 0, "Not sure": 0.5}

REGIONS = ["Europe", "Middle East", "North America", "South America", "Asia", "Pacific", "Africa"]

RATING_DESC = {
    "A": ("Very Strong Fit", "Excellent candidate. High priority for engagement."),
    "B": ("Promising",       "Good fit with some areas to develop. Engage and monitor closely."),
    "C": ("Moderate",        "Mixed signals. Worth tracking but not a top priority."),
    "D": ("Weak Fit",        "Significant gaps. Low priority unless context changes."),
}
RATING_COLOR = {"A": "rating-A", "B": "rating-B", "C": "rating-C", "D": "rating-D"}

# ── Session state defaults ──────────────────────────────────────────────────────
DEFAULTS = {
    "project_name":      "",
    "evaluated_by":      "",
    "region":            REGIONS[0],
    "eval_date":         date.today(),
    "application":       "PtP",
    "stable_policy":     "Yes",
    "vallourec_reach":   "Yes",
    "national_prio":     "Yes",
    "total_cost":        0.0,
    "funding_secured":   0.0,
    "gov_funded":        "Yes",
    "h2_source":         "Produced on site",
    # Produced on site branch
    "electrolyzer_mw":   0.0,
    "electrolyzer_unknown": False,
    "power_source":      "Onsite-wind and solar",
    "ppa_signed":        "Yes, self-production",
    "h2_qty_onsite":     0.0,
    "hours_storage_onsite": 0.0,
    # Pipeline branch
    "flowrate_kgday":    0.0,
    "flowrate_unknown":  False,
    "pipeline_type":     "Dedicated through a producer",
    "h2_purchase_signed":"Yes",
    "h2_qty_pipeline":   0.0,
    "hours_storage_pipeline": 0.0,
    # Other way branch
    "other_purchase_agr":"Yes",
    "h2_qty_other":      0.0,
    # Common after Q6
    "contract_signed":   "Yes",
    "offtaker":          "Yes, Binding",
    "land_area":         "Yes",
    "permits":           "Permitted",
    "eng_maturity":      "Conceptual",
    "h2_dna":            "Yes",
    "track_record":      "Industrial giants",
    "innovation":        "Yes",
    "footprint":         "Yes",
    "safety":            "Yes, absolutely",
    "geo_constraint":    "No constraints",
}

for k, v in DEFAULTS.items():
    st.session_state.setdefault(k, v)

# Override/comment state for each question
ALL_QIDS = [f"q{i}" for i in range(1, 22)]
for qid in ALL_QIDS:
    st.session_state.setdefault(f"override_{qid}", False)
    st.session_state.setdefault(f"comment_{qid}", "")

# ── Helper functions ─────────────────────────────────────────────────────────────

def funding_score(total, secured):
    if total is None or total == 0:
        return 0
    ratio = (secured or 0) / total
    if ratio < 0.2:  return 0
    if ratio < 0.6:  return 0.5
    return 1

def quantity_score(qty):
    if qty is None: return 0
    if qty < 1:     return 0
    if qty < 5:     return 0.5
    if qty < 15:    return 1
    return 0.5

def h2_source_val():
    return st.session_state.get("h2_source", "Produced on site")

def get_h2_quantity():
    src = h2_source_val()
    if src == "Produced on site":
        return st.session_state.get("h2_qty_onsite", 0.0)
    elif src == "Purchased via Pipeline":
        return st.session_state.get("h2_qty_pipeline", 0.0)
    else:
        return st.session_state.get("h2_qty_other", 0.0)

def get_answers():
    src = h2_source_val()
    return {
        "application":       st.session_state.get("application", "Others"),
        "stable_policy":     st.session_state.get("stable_policy", "Yes"),
        "vallourec_reach":   st.session_state.get("vallourec_reach", "Yes"),
        "national_priority": st.session_state.get("national_prio", "Yes"),
        "total_cost":        st.session_state.get("total_cost", 0.0) or None,
        "funding_secured":   st.session_state.get("funding_secured", 0.0) or None,
        "gov_funded":        st.session_state.get("gov_funded", "Yes"),
        "h2_source":         src,
        # Power / agreement
        "power_source":      st.session_state.get("power_source", "Onsite-wind and solar"),
        "ppa_signed":        st.session_state.get("ppa_signed", "Yes, self-production"),
        "pipeline_type":     st.session_state.get("pipeline_type", "Dedicated through a producer"),
        "h2_purchase_signed":st.session_state.get("h2_purchase_signed", "Yes"),
        "other_purchase_agr":st.session_state.get("other_purchase_agr", "Yes"),
        "h2_quantity":       get_h2_quantity() or None,
        # Remaining
        "contract_signed":   st.session_state.get("contract_signed", "Yes"),
        "offtaker":          st.session_state.get("offtaker", "Yes, Binding"),
        "land_area":         st.session_state.get("land_area", "Yes"),
        "permits":           st.session_state.get("permits", "Permitted"),
        "eng_maturity":      st.session_state.get("eng_maturity", "Conceptual"),
        "h2_dna":            st.session_state.get("h2_dna", "Yes"),
        "track_record":      st.session_state.get("track_record", "Industrial giants"),
        "innovation":        st.session_state.get("innovation", "Yes"),
        "footprint":         st.session_state.get("footprint", "Yes"),
        "safety":            st.session_state.get("safety", "Yes, absolutely"),
        "geo_constraint":    st.session_state.get("geo_constraint", "No constraints"),
    }

def agreement_score_for_source(answers):
    """Returns (agreement_key, score, label, bracket) depending on H2 source."""
    src = answers.get("h2_source", "Produced on site")
    if src == "Produced on site":
        s = PPA_SIGNED.get(answers.get("ppa_signed"), 0)
        return ("ppa_signed", s, "PPA / power agreement signed", "viability")
    elif src == "Purchased via Pipeline":
        s = H2_PURCHASE_SIGNED.get(answers.get("h2_purchase_signed"), 0)
        return ("h2_purchase_signed", s, "H2 purchase agreement signed", "viability")
    else:
        s = OTHER_PURCHASE_AGR.get(answers.get("other_purchase_agr"), 0)
        return ("other_purchase_agr", s, "Purchase agreement signed", "viability")

def build_components(answers):
    app = answers.get("application", "Others")
    app_s = APPLICATIONS.get(app, {"storage_required": 0.5, "viability": 0.5})
    src = answers.get("h2_source", "Produced on site")
    agr_key, agr_score, agr_label, agr_cat = agreement_score_for_source(answers)

    components = {
        # Q1
        "application_viability": {
            "id": "application_viability", "question": "q1",
            "label": "Application – Project Viability",
            "category": "viability", "score": app_s["viability"], "max": 1.0,
        },
        "application_storage": {
            "id": "application_storage", "question": "q1",
            "label": "Application – Storage Required",
            "category": "delphy", "score": app_s["storage_required"], "max": 1.0,
        },
        # Q2
        "stable_policy": {
            "id": "stable_policy", "question": "q2",
            "label": "Stable policy",
            "category": "viability", "score": STABLE_POLICY.get(answers.get("stable_policy"), 0), "max": 1.0,
        },
        "vallourec_reach": {
            "id": "vallourec_reach", "question": "q2",
            "label": "Vallourec reach",
            "category": "delphy", "score": VALLOUREC_REACH.get(answers.get("vallourec_reach"), 0), "max": 1.0,
        },
        # Q3
        "national_priority": {
            "id": "national_priority", "question": "q3",
            "label": "National priority",
            "category": "viability", "score": NATIONAL_PRIORITY.get(answers.get("national_priority"), 0), "max": 1.0,
        },
        # Q4/Q5
        "funding": {
            "id": "funding", "question": "q4",
            "label": "Funding ratio",
            "category": "viability",
            "score": funding_score(answers.get("total_cost"), answers.get("funding_secured")), "max": 1.0,
        },
        # Q5
        "gov_funded": {
            "id": "gov_funded", "question": "q5",
            "label": "Government funded",
            "category": "viability", "score": GOV_FUNDED.get(answers.get("gov_funded"), 0), "max": 1.0,
        },
        # Q6
        "h2_source": {
            "id": "h2_source", "question": "q6",
            "label": "H2 source",
            "category": "delphy", "score": H2_SOURCE_OPTIONS.get(src, 0), "max": 1.0,
        },
        # Q9 (agreement – varies by source)
        "agreement_signed": {
            "id": "agreement_signed", "question": "q9",
            "label": agr_label,
            "category": agr_cat, "score": agr_score, "max": 1.0,
        },
    }

    # Q8 power source (only for Produced on site)
    if src == "Produced on site":
        components["power_source"] = {
            "id": "power_source", "question": "q8",
            "label": "Power source",
            "category": "delphy", "score": POWER_SOURCE.get(answers.get("power_source"), 0), "max": 1.0,
        }
    # Q8 pipeline type (only for pipeline)
    if src == "Purchased via Pipeline":
        components["pipeline_type"] = {
            "id": "pipeline_type", "question": "q8",
            "label": "Pipeline connection type",
            "category": "delphy", "score": PIPELINE_TYPE.get(answers.get("pipeline_type"), 0), "max": 1.0,
        }

    # Q10 H2 quantity
    components["h2_quantity"] = {
        "id": "h2_quantity", "question": "q10",
        "label": "H2 quantity to store",
        "category": "delphy", "score": quantity_score(answers.get("h2_quantity")), "max": 1.0,
    }

    # Q11 Contract signed
    components["contract_signed"] = {
        "id": "contract_signed", "question": "q11",
        "label": "Contract with technology supplier",
        "category": "viability", "score": CONTRACT_SIGNED.get(answers.get("contract_signed"), 0), "max": 1.0,
    }
    # Q12 Offtaker
    components["offtaker"] = {
        "id": "offtaker", "question": "q12",
        "label": "Offtaker contract",
        "category": "viability", "score": OFFTAKER.get(answers.get("offtaker"), 0), "max": 1.0,
    }
    # Q13 Land
    components["land_area"] = {
        "id": "land_area", "question": "q13",
        "label": "Land secured",
        "category": "viability", "score": LAND_AREA.get(answers.get("land_area"), 0), "max": 1.0,
    }
    # Q14 Permits
    components["permits"] = {
        "id": "permits", "question": "q14",
        "label": "Permitting status",
        "category": "viability", "score": PERMITS.get(answers.get("permits"), 0), "max": 1.0,
    }
    # Q15 Eng maturity
    components["eng_maturity"] = {
        "id": "eng_maturity", "question": "q15",
        "label": "Project status",
        "category": "viability", "score": ENG_MATURITY.get(answers.get("eng_maturity"), 0), "max": 1.0,
    }
    # Q16 H2 DNA
    components["h2_dna"] = {
        "id": "h2_dna", "question": "q16",
        "label": "H2 in their DNA",
        "category": "viability", "score": H2_DNA.get(answers.get("h2_dna"), 0), "max": 1.0,
    }
    # Q17 Track record
    components["track_record"] = {
        "id": "track_record", "question": "q17",
        "label": "Developer track record",
        "category": "viability", "score": TRACK_RECORD.get(answers.get("track_record"), 0), "max": 1.0,
    }
    # Q18 Innovation
    components["innovation"] = {
        "id": "innovation", "question": "q18",
        "label": "Open to innovative solutions",
        "category": "delphy", "score": INNOVATION.get(answers.get("innovation"), 0), "max": 1.0,
    }
    # Q19 Footprint
    components["footprint"] = {
        "id": "footprint", "question": "q19",
        "label": "Footprint constraint",
        "category": "delphy", "score": FOOTPRINT.get(answers.get("footprint"), 0), "max": 1.0,
    }
    # Q20 Safety
    components["safety"] = {
        "id": "safety", "question": "q20",
        "label": "Safety importance",
        "category": "delphy", "score": SAFETY.get(answers.get("safety"), 0), "max": 1.0,
    }
    # Q21 Geology
    components["geo_constraint"] = {
        "id": "geo_constraint", "question": "q21",
        "label": "Geology / geological constraints",
        "category": "delphy", "score": GEO_CONSTRAINT.get(answers.get("geo_constraint"), 0), "max": 1.0,
    }

    return components

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
    viability_score = 0.0; viability_max = 0.0
    delphy_score = 0.0;    delphy_max = 0.0
    for comp in resolved.values():
        if comp["category"] == "viability":
            viability_score += comp["score"]
            viability_max   += comp["max"]
        else:
            delphy_score += comp["score"]
            delphy_max   += comp["max"]
    total = viability_score + delphy_score
    total_max = viability_max + delphy_max
    pct = (total / total_max * 100) if total_max else 0
    if pct >= 80:   rating = "A"
    elif pct >= 60: rating = "B"
    elif pct >= 40: rating = "C"
    else:           rating = "D"
    return {
        "viability": (viability_score, viability_max),
        "delphy":    (delphy_score, delphy_max),
        "total":     (total, total_max),
        "pct":       round(pct, 1),
        "rating":    rating,
        "components": resolved,
    }

# ── Bracket tag HTML helpers ───────────────────────────────────────────────────
def vtag():
    return '<span class="bracket-tag bracket-viability">Project Viability</span>'

def dtag():
    return '<span class="bracket-tag bracket-delphy">Delphy Chance to Win</span>'

# ── View/Modify (or calculate/view) ──────────────────────────────────────────
def render_view_modify(qid, label="View/Modify"):
    answers = get_answers()
    components = build_components(answers)
    # Find components for this question
    relevant = [c for c in components.values() if c["question"] == qid]

    with st.expander(label, expanded=False):
        if relevant:
            auto_total = sum(c["score"] for c in relevant)
            total_max  = sum(c["max"] for c in relevant)
            rows_html = "".join([
                f'<div class="vm-summary-row"><span>{c["label"]}</span>'
                f'<span>{c["score"]:.2f} / {c["max"]:.1f}</span></div>'
                for c in relevant
            ])
            st.markdown(
                f'<div class="vm-summary">'
                f'<div class="vm-summary-row"><span><strong>Auto score</strong></span>'
                f'<span>{auto_total:.2f} / {total_max:.1f}</span></div>'
                f'{rows_html}</div>',
                unsafe_allow_html=True
            )
            override_key = f"override_{qid}"
            st.toggle("Manual overwrite", key=override_key)
            if st.session_state.get(override_key, False):
                for comp in relevant:
                    mk = f"manual_{comp['id']}"
                    if mk not in st.session_state:
                        st.session_state[mk] = float(comp["score"])
                    st.select_slider(
                        f"{comp['label']} score",
                        options=[0.0, 0.25, 0.5, 0.75, 1.0],
                        key=mk
                    )
            else:
                for comp in relevant:
                    st.session_state[f"manual_{comp['id']}"] = float(comp["score"])
        else:
            st.markdown('<div class="vm-muted">This question is used for calculation only, not direct scoring.</div>', unsafe_allow_html=True)

        st.text_area("Comment", key=f"comment_{qid}", height=65, placeholder="Add comment...")

# ── UI ─────────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
  <h1>⚡ H2 Project Ranking Engine</h1>
  <p>Evaluate and rank hydrogen projects — Project Viability &amp; Delphy Chance to Win.</p>
</div>
""", unsafe_allow_html=True)

col_form, col_result = st.columns([3, 2], gap="large")

with col_form:

    # ── Project Info ──────────────────────────────────────────────────────────
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">📋 Project Information</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    c1.text_input("Project Name", placeholder="e.g. Masdar Green H2", key="project_name")
    c2.text_input("Evaluated by", placeholder="Your name", key="evaluated_by")
    c3, c4 = st.columns(2)
    c3.selectbox("Project Region", REGIONS, key="region")
    c4.date_input("Date", value=st.session_state["eval_date"], key="eval_date")
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Application & Market ──────────────────────────────────────────────────
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">🏭 Application & Market</div>', unsafe_allow_html=True)

    # Q1
    st.markdown(f'**1. Application area?** {vtag()} {dtag()}', unsafe_allow_html=True)
    st.selectbox("", list(APPLICATIONS.keys()), key="application", label_visibility="collapsed")
    render_view_modify("q1")

    # Q2
    st.markdown(f'**2. Country a good fit?**', unsafe_allow_html=True)
    cq2a, cq2b = st.columns(2)
    with cq2a:
        st.markdown(f'Stable policy {vtag()}', unsafe_allow_html=True)
        st.selectbox("", list(STABLE_POLICY.keys()), key="stable_policy", label_visibility="collapsed")
    with cq2b:
        st.markdown(f'Vallourec Reach {dtag()}', unsafe_allow_html=True)
        st.selectbox("", list(VALLOUREC_REACH.keys()), key="vallourec_reach", label_visibility="collapsed")
    render_view_modify("q2")

    # Q3
    st.markdown(f'**3. Is it the project of national priority?** {vtag()}', unsafe_allow_html=True)
    st.selectbox("", list(NATIONAL_PRIORITY.keys()), key="national_prio", label_visibility="collapsed")
    render_view_modify("q3")

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Funding & Finance ──────────────────────────────────────────────────────
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">💰 Funding & Finance</div>', unsafe_allow_html=True)

    # Q4
    st.markdown(f'**4. What is the current funding status?** {vtag()}', unsafe_allow_html=True)
    cq4a, cq4b = st.columns(2)
    with cq4a:
        st.number_input("Total cost (Mil. Euro)", min_value=0.0, step=10.0, key="total_cost")
    with cq4b:
        st.number_input("Secured cost (Mil. Euro)", min_value=0.0, step=10.0, key="funding_secured")
    render_view_modify("q4")

    # Q5
    st.markdown(f'**5. Is the project funded by government entities or grants?** {vtag()}', unsafe_allow_html=True)
    st.selectbox("", list(GOV_FUNDED.keys()), key="gov_funded", label_visibility="collapsed")
    render_view_modify("q5")

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Technical Setup ────────────────────────────────────────────────────────
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">⚙️ Technical Setup</div>', unsafe_allow_html=True)

    # Q6
    st.markdown(f'**6. What is the source of hydrogen?** {dtag()}', unsafe_allow_html=True)
    st.selectbox("", list(H2_SOURCE_OPTIONS.keys()), key="h2_source", label_visibility="collapsed")
    render_view_modify("q6")

    h2_src = st.session_state.get("h2_source", "Produced on site")

    # ── Branch: Produced on site ──────────────────────────────────────────────
    if h2_src == "Produced on site":

        # Q7
        st.markdown("**7. What is the size of electrolyzer (MW)?**", unsafe_allow_html=True)
        ele_unknown = st.checkbox("I don't know", key="electrolyzer_unknown")
        if not ele_unknown:
            st.number_input("Electrolyzer size (MW)", min_value=0.0, step=1.0, key="electrolyzer_mw", label_visibility="visible")
        else:
            st.session_state["electrolyzer_mw"] = 0.0
            st.caption("Electrolyzer size not available — size-based storage calculator will be disabled.")

        # Q8
        st.markdown(f'**8. What is the source of power?** {dtag()}', unsafe_allow_html=True)
        st.selectbox("", list(POWER_SOURCE.keys()), key="power_source", label_visibility="collapsed")
        render_view_modify("q8")

        # Q9
        st.markdown(f'**9. Has the Power Purchase Agreement been signed?** {vtag()}', unsafe_allow_html=True)
        st.selectbox("", list(PPA_SIGNED.keys()), key="ppa_signed", label_visibility="collapsed")
        render_view_modify("q9")

        # Q10
        st.markdown(f'**10. Estimate the tons of H₂ likely to be stored?** {dtag()}', unsafe_allow_html=True)
        st.number_input("Tonnes of H₂ to store", min_value=0.0, step=0.5, key="h2_qty_onsite", label_visibility="visible")

        # Calculate/View expander
        with st.expander("Calculate / View", expanded=False):
            ele_mw = st.session_state.get("electrolyzer_mw", 0.0)
            if ele_unknown or ele_mw == 0:
                st.warning("Enter the electrolyzer size in Q7 to use the calculator.")
            else:
                hrs = st.number_input("Hours of storage", min_value=0.0, step=1.0, value=4.0, key="hours_storage_onsite")
                calc_tons = ele_mw * 0.7 * hrs * 55 / 1000  # MWh/(MWh/tonne)=tonne; 55 MWh/tonne
                # Actually formula: ele_MW * 0.7 * hours * 55 gives kg if 55 is kg/MWh? Let's use as given:
                # formula: ele_MW * 0.7 * hours_of_storage * 55 (result in kg based on user spec)
                calc_tons_raw = ele_mw * 0.7 * hrs * 55
                st.metric("Calculated H₂ storage need", f"{calc_tons_raw:,.0f} kg  /  {calc_tons_raw/1000:.2f} tonnes")
                st.markdown('<p class="calc-note">Calculated based on 70% capacity factor and 55 kg of hydrogen per MWh produced.</p>', unsafe_allow_html=True)
                st.info(f"💡 You can enter **{calc_tons_raw/1000:.2f} tonnes** in the field above to use this estimate.")

            # Score preview
            qty = st.session_state.get("h2_qty_onsite", 0.0)
            sc = quantity_score(qty)
            st.markdown(f"**Current score for {qty:.1f} t entered:** `{sc:.2f} / 1.0`")

        render_view_modify("q10", label="View/Modify Score")

    # ── Branch: Purchased via Pipeline ───────────────────────────────────────
    elif h2_src == "Purchased via Pipeline":

        # Q7
        st.markdown("**7. What is the flowrate of hydrogen (kg/day)?**", unsafe_allow_html=True)
        flow_unknown = st.checkbox("I don't know", key="flowrate_unknown")
        if not flow_unknown:
            st.number_input("Flowrate (kg/day)", min_value=0.0, step=100.0, key="flowrate_kgday", label_visibility="visible")
        else:
            st.session_state["flowrate_kgday"] = 0.0
            st.caption("Flowrate not available — flowrate-based storage calculator will be disabled.")

        # Q8
        st.markdown(f'**8. Type of pipeline connection?** {dtag()}', unsafe_allow_html=True)
        st.selectbox("", list(PIPELINE_TYPE.keys()), key="pipeline_type", label_visibility="collapsed")
        render_view_modify("q8")

        # Q9
        st.markdown(f'**9. Has the hydrogen purchase agreement been signed?** {vtag()}', unsafe_allow_html=True)
        st.selectbox("", list(H2_PURCHASE_SIGNED.keys()), key="h2_purchase_signed", label_visibility="collapsed")
        render_view_modify("q9")

        # Q10
        st.markdown(f'**10. Estimate the tons of H₂ likely to be stored?** {dtag()}', unsafe_allow_html=True)
        st.number_input("Tonnes of H₂ to store", min_value=0.0, step=0.5, key="h2_qty_pipeline", label_visibility="visible")

        with st.expander("Calculate / View", expanded=False):
            flowrate = st.session_state.get("flowrate_kgday", 0.0)
            if flow_unknown or flowrate == 0:
                st.warning("Enter the flowrate in Q7 to use the calculator.")
            else:
                hrs = st.number_input("Hours of storage", min_value=0.0, step=1.0, value=4.0, key="hours_storage_pipeline")
                # formula: flowrate / (1000 * 24) * hours_of_storage → tonnes
                calc_tons = flowrate / (1000 * 24) * hrs
                st.metric("Calculated H₂ storage need", f"{calc_tons:.4f} tonnes  /  {calc_tons*1000:.1f} kg")
                st.info(f"💡 You can enter **{calc_tons:.4f} tonnes** in the field above to use this estimate.")

            qty = st.session_state.get("h2_qty_pipeline", 0.0)
            sc = quantity_score(qty)
            st.markdown(f"**Current score for {qty:.1f} t entered:** `{sc:.2f} / 1.0`")

        render_view_modify("q10", label="View/Modify Score")

    # ── Branch: Purchased through other way ──────────────────────────────────
    else:  # Purchased through other way

        # Q7
        st.markdown(f'**7. Has the purchase agreement been signed?** {vtag()}', unsafe_allow_html=True)
        st.selectbox("", list(OTHER_PURCHASE_AGR.keys()), key="other_purchase_agr", label_visibility="collapsed")
        render_view_modify("q9")   # reuses q9 override slot for agreement

        # Q8
        st.markdown(f'**8. Estimate the tons of H₂ likely to be stored?** {dtag()}', unsafe_allow_html=True)
        st.number_input("Tonnes of H₂ to store", min_value=0.0, step=0.5, key="h2_qty_other", label_visibility="visible")
        render_view_modify("q10", label="View/Modify Score")

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Project Readiness ──────────────────────────────────────────────────────
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">📊 Project Readiness</div>', unsafe_allow_html=True)

    # Q11
    st.markdown(f'**11. Has a contract been signed with technology suppliers?** {vtag()}', unsafe_allow_html=True)
    st.selectbox("", list(CONTRACT_SIGNED.keys()), key="contract_signed", label_visibility="collapsed")
    render_view_modify("q11")

    # Q12
    st.markdown(f'**12. Has the offtaker been found and contract signed?** {vtag()}', unsafe_allow_html=True)
    st.selectbox("", list(OFFTAKER.keys()), key="offtaker", label_visibility="collapsed")
    render_view_modify("q12")

    # Q13
    st.markdown(f'**13. Has land area been secured?** {vtag()}', unsafe_allow_html=True)
    st.selectbox("", list(LAND_AREA.keys()), key="land_area", label_visibility="collapsed")
    render_view_modify("q13")

    # Q14
    st.markdown(f'**14. What is the status of the permitting?** {vtag()}', unsafe_allow_html=True)
    st.selectbox("", list(PERMITS.keys()), key="permits", label_visibility="collapsed")
    render_view_modify("q14")

    # Q15
    st.markdown(f'**15. What is the current status of the project?** {vtag()}', unsafe_allow_html=True)
    st.selectbox("", list(ENG_MATURITY.keys()), key="eng_maturity", label_visibility="collapsed")
    render_view_modify("q15")

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Strategic Fit ──────────────────────────────────────────────────────────
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">🎯 Strategic Fit</div>', unsafe_allow_html=True)

    # Q16
    st.markdown(f'**16. Is H₂ in their DNA?** {vtag()}', unsafe_allow_html=True)
    st.selectbox("", list(H2_DNA.keys()), key="h2_dna", label_visibility="collapsed")
    render_view_modify("q16")

    # Q17
    st.markdown(f'**17. Developer track record?** {vtag()}', unsafe_allow_html=True)
    st.selectbox("", list(TRACK_RECORD.keys()), key="track_record", label_visibility="collapsed")
    render_view_modify("q17")

    # Q18
    st.markdown(f'**18. Are the developer and stakeholders open to innovative solutions?** {dtag()}', unsafe_allow_html=True)
    st.selectbox("", list(INNOVATION.keys()), key="innovation", label_visibility="collapsed")
    render_view_modify("q18")

    # Q19
    st.markdown(f'**19. Is there a footprint constraint in the area?** {dtag()}', unsafe_allow_html=True)
    st.selectbox("", list(FOOTPRINT.keys()), key="footprint", label_visibility="collapsed")
    render_view_modify("q19")

    # Q20
    st.markdown(f'**20. Safety a big deal?** {dtag()}', unsafe_allow_html=True)
    st.selectbox("", list(SAFETY.keys()), key="safety", label_visibility="collapsed")
    render_view_modify("q20")

    # Q21
    st.markdown(f'**21. How is the geology in the area?** {dtag()}', unsafe_allow_html=True)
    st.selectbox("", list(GEO_CONSTRAINT.keys()), key="geo_constraint", label_visibility="collapsed")
    render_view_modify("q21")

    st.markdown('</div>', unsafe_allow_html=True)

    submitted = st.button("🚀 Evaluate Project")

# ── Results Panel ──────────────────────────────────────────────────────────────
with col_result:
    st.markdown("### 📈 Evaluation Results")
    answers = get_answers()
    scores  = compute_scores(answers)

    rating = scores["rating"]
    rname, rdesc = RATING_DESC[rating]
    rcolor = RATING_COLOR[rating]

    st.markdown(f"""
    <div class="score-card" style="text-align:center;">
      <div class="score-label">Overall Rating</div>
      <div style="margin:0.5rem 0;"><span class="rating-badge {rcolor}">{rating}</span></div>
      <div style="font-size:1rem;font-weight:600;color:#28251d;">{rname}</div>
      <div style="font-size:0.85rem;color:#7a7974;margin-top:0.3rem;">{rdesc}</div>
    </div>
    """, unsafe_allow_html=True)

    total_v, total_m = scores["total"]
    st.markdown(f"""
    <div class="score-card">
      <div class="score-label">Total Score</div>
      <div><span class="score-value">{total_v:.2f}</span>
           <span class="score-max"> / {total_m:.0f}  ({scores["pct"]}%)</span></div>
    </div>
    """, unsafe_allow_html=True)
    st.progress(scores["pct"] / 100 if scores["pct"] else 0)

    vv, vm = scores["viability"]
    dv, dm = scores["delphy"]

    st.markdown(f"""
    <div class="score-card">
      <div class="score-label">✅ Project Viability</div>
      <div><span class="score-value" style="font-size:1.4rem;">{vv:.2f}</span>
           <span class="score-max"> / {vm:.0f}</span></div>
    </div>
    """, unsafe_allow_html=True)
    st.progress(vv / vm if vm > 0 else 0)

    st.markdown(f"""
    <div class="score-card">
      <div class="score-label">🎯 Delphy Chance to Win</div>
      <div><span class="score-value" style="font-size:1.4rem;">{dv:.2f}</span>
           <span class="score-max"> / {dm:.0f}</span></div>
    </div>
    """, unsafe_allow_html=True)
    st.progress(dv / dm if dm > 0 else 0)

    # Component breakdown
    st.markdown("#### Score Breakdown")
    comps = scores["components"]
    viab_comps  = [c for c in comps.values() if c["category"] == "viability"]
    delphy_comps = [c for c in comps.values() if c["category"] == "delphy"]

    with st.expander("📗 Project Viability — Details", expanded=False):
        for c in viab_comps:
            st.markdown(f"**{c['label']}**: `{c['score']:.2f}` / {c['max']:.1f}")

    with st.expander("📘 Delphy Chance to Win — Details", expanded=False):
        for c in delphy_comps:
            st.markdown(f"**{c['label']}**: `{c['score']:.2f}` / {c['max']:.1f}")

    # Export
    project_name = st.session_state.get("project_name", "")
    region       = st.session_state.get("region", "")
    eval_date    = st.session_state.get("eval_date", date.today())

    if submitted and project_name:
        export_data = {
            "project_name": project_name,
            "evaluated_by": st.session_state.get("evaluated_by", ""),
            "region":       region,
            "date":         str(eval_date),
            "answers":      {k: str(v) for k, v in answers.items()},
            "scores": {
                "viability":  scores["viability"][0],
                "viability_max": scores["viability"][1],
                "delphy":     scores["delphy"][0],
                "delphy_max": scores["delphy"][1],
                "total":      scores["total"][0],
                "total_max":  scores["total"][1],
                "pct":        scores["pct"],
                "rating":     rating,
            }
        }
        st.download_button(
            label="⬇️ Download Evaluation (JSON)",
            data=json.dumps(export_data, indent=2),
            file_name=f"{project_name.replace(' ', '_')}_score.json",
            mime="application/json"
        )
        df_export = pd.DataFrame([{
            "Project":           project_name,
            "Region":            region,
            "Rating":            rating,
            "Score %":           scores["pct"],
            "Project Viability": scores["viability"][0],
            "Delphy Chance Win": scores["delphy"][0],
            "Total":             scores["total"][0],
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
