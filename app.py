import streamlit as st
import pandas as pd
import json
from datetime import date

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="H2 Project Ranking Engine",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Session state init ───────────────────────────────────────────────────────
if "manual_scores" not in st.session_state:
    st.session_state.manual_scores = {}

if "score_comments" not in st.session_state:
    st.session_state.score_comments = {}

# ── Helper: Score review UI ──────────────────────────────────────────────────
def score_review_ui(key, auto_score, max_score):
    st.markdown(f"**Auto score:** `{auto_score:.2f} / {max_score}`")

    c1, c2 = st.columns([1, 2])
    with c1:
        override = st.number_input(
            "Override score",
            min_value=0.0,
            max_value=float(max_score),
            value=st.session_state.manual_scores.get(key, auto_score),
            step=0.1,
            key=f"{key}_override"
        )

    with c2:
        comment = st.text_area(
            "Comment / justification",
            value=st.session_state.score_comments.get(key, ""),
            height=70,
            key=f"{key}_comment"
        )

    st.session_state.manual_scores[key] = override
    st.session_state.score_comments[key] = comment
    return override

# ── Scoring dictionaries ────────────────────────────────────────────────────
APPLICATIONS = {
    "PtP": {"storage_required": 1, "viability": 0.5},
    "E-Saf": {"storage_required": 0.5, "viability": 1},
    "E-Methanol": {"storage_required": 0.5, "viability": 1},
    "E-Ammonia": {"storage_required": 0.5, "viability": 1},
    "Iron Reduction": {"storage_required": 0.5, "viability": 1},
    "Heating": {"storage_required": 0.5, "viability": 0.5},
    "HRS": {"storage_required": 1, "viability": 0.5},
    "Others": {"storage_required": 0.5, "viability": 0.5},
}

NATIONAL_PRIORITY = {"Yes": 1, "No": 0, "Not sure": 0.5}
CONTRACT_SIGNED = {"Yes": 1, "A Few": 0.5, "Not Any": 0}
H2_SOURCE = {"Produced Onsite": 1, "Purchased via Pipeline": 0, "Purchased Other": 1}
PPA_SIGNED = {"Yes, self-production": 1, "Yes, with others": 1, "No": 0}
POWER_SOURCE = {"Onsite-wind and solar": 1, "Hydro and Nuclear": 0.5,
                "Stable Grid": 0.5, "Dynamic Grid": 1}
OFFTAKER = {"Yes, Binding": 1, "Yes, Self Consumption": 1, "Yes, MoU": 0.5, "No": 0}
LAND_AREA = {"Yes": 1, "No": 0, "In Process": 0.5}
PERMITS = {"Permitted": 1, "Applied": 0.5, "No Update": 0}
ENG_MATURITY = {"Pre-Feed": 0.5, "Feed": 1, "Waiting FID": 1,
                "FID": 1, "Under Construction": 0.5, "Operational": 0}
H2_DNA = {"Yes": 1, "50-50": 0.5, "No": 0}
TRACK_RECORD = {"Startup": 0, "Multiple H2 projects": 0.5, "Industrial giants": 1}
INNOVATION = {"Yes": 1, "Prefer not to": 0, "May be": 0.5}
FOOTPRINT = {"Yes": 1, "Not so much": 0.5, "Not at all": 0}
SAFETY = {"Yes, absolutely": 1, "Preferred": 0.5, "Minimum": 0}
GEO_CONSTRAINT = {"No constraints": 1, "Difficult": 0, "Not sure": 0.5}
COUNTRY_FIT = {"Yes": 1, "No": 0, "Not Sure": 0.5}

# ── Utility scoring ─────────────────────────────────────────────────────────
def funding_score(total, secured):
    if not total:
        return 0
    ratio = (secured or 0) / total
    if ratio < 0.2: return 0
    if ratio < 0.6: return 0.5
    return 1

def quantity_score(qty):
    if not qty: return 0
    if qty < 1: return 0
    if qty < 5: return 0.5
    if qty < 15: return 1
    return 0.5

# ── UI Layout ────────────────────────────────────────────────────────────────
st.title("⚡ H2 Project Ranking Engine")

st.markdown("### 📋 Project Info")
project_name = st.text_input("Project Name")
evaluated_by = st.text_input("Evaluated by")
region = st.selectbox("Project Region", ["Europe", "Middle East", "North America", "Asia"])
eval_date = st.date_input("Date", value=date.today())

# ── Application ─────────────────────────────────────────────────────────────
st.markdown("## 🏭 Application & Market")
application = st.selectbox("Application", list(APPLICATIONS))
country_fit = st.selectbox("Country fit", list(COUNTRY_FIT))
national_priority = st.selectbox("National priority", list(NATIONAL_PRIORITY))

auto_viability = (
    APPLICATIONS[application]["viability"] +
    COUNTRY_FIT[country_fit] +
    NATIONAL_PRIORITY[national_priority]
)

final_viability = score_review_ui("viability", auto_viability, 6)

# ── Funding ─────────────────────────────────────────────────────────────────
st.markdown("## 💰 Funding")
total_cost = st.number_input("Total cost (M€)", min_value=0.0)
funding_secured = st.number_input("Funding secured (M€)", min_value=0.0)

auto_funding = funding_score(total_cost, funding_secured)
final_funding = score_review_ui("funding", auto_funding, 1)

# ── Technical ───────────────────────────────────────────────────────────────
st.markdown("## ⚙️ Technical")
h2_source = st.selectbox("H2 source", list(H2_SOURCE))
power_source = st.selectbox("Power source", list(POWER_SOURCE))
h2_quantity = st.number_input("H2 quantity (t)", min_value=0.0)

auto_storage = (
    APPLICATIONS[application]["storage_required"] +
    quantity_score(h2_quantity)
)

final_storage = score_review_ui("storage_required", auto_storage, 5)

# ── Readiness ───────────────────────────────────────────────────────────────
st.markdown("## 📊 Readiness")
contract_signed = st.selectbox("Contract signed", list(CONTRACT_SIGNED))
land_area = st.selectbox("Land secured", list(LAND_AREA))
permits = st.selectbox("Permits", list(PERMITS))

auto_readiness = (
    CONTRACT_SIGNED[contract_signed] +
    LAND_AREA[land_area] +
    PERMITS[permits]
)

final_readiness = score_review_ui("readiness", auto_readiness, 5)

# ── Final score ──────────────────────────────────────────────────────────────
total_score = (
    final_viability +
    final_funding +
    final_storage +
    final_readiness
)

st.markdown("## 📈 Final Result")
st.metric("Total Score", f"{total_score:.1f}")

# ── Export ───────────────────────────────────────────────────────────────────
export = {
    "project": project_name,
    "evaluated_by": evaluated_by,
    "date": str(eval_date),
    "scores": st.session_state.manual_scores,
    "comments": st.session_state.score_comments
}

st.download_button(
    "⬇️ Download JSON",
    data=json.dumps(export, indent=2),
    file_name="evaluation.json"
)

