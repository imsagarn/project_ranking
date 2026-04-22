import streamlit as st
import pandas as pd
import json
from datetime import date

st.set_page_config(
    page_title="H2 Project Ranking Engine",
    page_icon="⚡",
    layout="wide",
)

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

  .main-header {
    background: linear-gradient(135deg, #01696f 0%, #0c4e54 100%);
    color: white; padding: 2rem 2.5rem; border-radius: 12px; margin-bottom: 2rem;
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
    background: white; border: 1px solid #dcd9d5; border-radius: 10px;
    padding: 1.2rem 1.5rem; margin-bottom: 0.8rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
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
  div[data-testid="stExpander"] {
    border: 1px solid #e8e5e0 !important;
    border-radius: 8px !important;
    margin-top: 0.3rem !important;
    margin-bottom: 0.8rem !important;
  }
  .stButton>button {
    background: #01696f; color: white; border: none;
    border-radius: 8px; padding: 0.65rem 2rem;
    font-weight: 600; font-size: 1rem; width: 100%;
  }
  .stButton>button:hover { background: #0c4e54; }
  .stProgress > div > div { background-color: #01696f; }
</style>
""", unsafe_allow_html=True)

# ── Scoring tables ────────────────────────────────────────────────────────────
APPLICATIONS = {
    "PtP":            {"storage_required": 1.0, "viability": 0.5},
    "E-Saf":          {"storage_required": 0.5, "viability": 1.0},
    "E-Methanol":     {"storage_required": 0.5, "viability": 1.0},
    "E-Ammonia":      {"storage_required": 0.5, "viability": 1.0},
    "Iron Reduction": {"storage_required": 0.5, "viability": 1.0},
    "Heating":        {"storage_required": 0.5, "viability": 0.5},
    "HRS":            {"storage_required": 1.0, "viability": 0.5},
    "Others":         {"storage_required": 0.5, "viability": 0.5},
}
NATIONAL_PRIORITY = {"Yes": 1.0, "No": 0.0, "Not sure": 0.5}
CONTRACT_SIGNED   = {"Yes": 1.0, "A Few": 0.5, "Not Any": 0.0}
H2_SOURCE         = {"Produced Onsite": 1.0, "Purchased via Pipeline": 0.0, "Purchased Other": 1.0}
PPA_SIGNED        = {"Yes, self-production": 1.0, "Yes, with others": 1.0, "No": 0.0}
POWER_SOURCE      = {"Onsite-wind and solar": 1.0, "Hydro and Nuclear": 0.5,
                     "Stable Grid": 0.5, "Dynamic Grid": 1.0}
OFFTAKER          = {"Yes, Binding": 1.0, "Yes, Self Consumption": 1.0, "Yes, MoU": 0.5, "No": 0.0}
LAND_AREA         = {"Yes": 1.0, "No": 0.0, "In Process": 0.5}
PERMITS           = {"Permitted": 1.0, "Applied": 0.5, "No Update": 0.0}
ENG_MATURITY      = {"Pre-Feed": 0.5, "Feed": 1.0, "Waiting FID": 1.0, "FID": 1.0,
                     "Under Construction": 0.5, "Operational": 0.0}
H2_DNA            = {"Yes": 1.0, "50-50": 0.5, "No": 0.0}
TRACK_RECORD      = {"Startup": 0.0, "Multiple H2 projects": 0.5, "Industrial giants": 1.0}
INNOVATION        = {"Yes": 1.0, "Prefer not to": 0.0, "May be": 0.5}
FOOTPRINT         = {"Yes": 1.0, "Not so much": 0.5, "Not at all": 0.0}
SAFETY            = {"Yes, absolutely": 1.0, "Preferred": 0.5, "Minimum": 0.0}
GEO_CONSTRAINT    = {"No constraints": 1.0, "Difficult": 0.0, "Not sure": 0.5}
COUNTRY_FIT       = {"Yes": 1.0, "No": 0.0, "Not Sure": 0.5}
REGIONS           = ["Europe", "Middle East", "North America", "South America", "Asia", "Pacific", "Africa"]

def funding_score(total, secured):
    if not total or total == 0: return 0.0
    ratio = (secured or 0) / total
    if ratio < 0.2: return 0.0
    if ratio < 0.6: return 0.5
    return 1.0

def quantity_score(qty):
    if not qty or qty <= 0: return 0.0
    if qty < 1:  return 0.0
    if qty < 5:  return 0.5
    if qty < 15: return 1.0
    return 0.5

# ── Score modifier widget ─────────────────────────────────────────────────────
# Returns effective score (after possible override) and stores comment in session_state
def score_modifier(field_key, auto_score, category, score_table=None):
    """
    Shows an expander below a question with:
      - Score table for that field
      - Override option
      - Comment box
    Returns the effective score to use.
    """
    ov_key  = f"ov_val_{field_key}"
    use_key = f"ov_use_{field_key}"
    cmt_key = f"cmt_{field_key}"

    with st.expander("🔍 View / Modify score & add comment"):
        # Score table
        if score_table:
            st.markdown("**Score table for this question:**")
            table_rows = "".join(
                f"<tr style='border-bottom:1px solid #eee'>"
                f"<td style='padding:3px 16px 3px 0;color:#28251d'>{opt}</td>"
                f"<td style='font-weight:700;color:#01696f'>{val}</td>"
                f"</tr>"
                for opt, val in score_table.items()
            )
            st.markdown(
                f"<table style='font-size:0.83rem;margin-bottom:6px'>{table_rows}</table>",
                unsafe_allow_html=True
            )
        st.markdown(
            f"<div style='background:#f0faf9;border-radius:6px;padding:6px 10px;"
            f"font-size:0.85rem;margin-bottom:8px'>"
            f"<b>Auto-score:</b> <span style='color:#01696f;font-weight:700'>{auto_score:.2f}</span>"
            f" &nbsp;|&nbsp; <b>Category:</b> {category}</div>",
            unsafe_allow_html=True
        )

        use_override = st.checkbox("✏️ Override this score", key=use_key)
        if use_override:
            st.number_input(
                "Override value (0.0 – 1.0)", min_value=0.0, max_value=1.0,
                step=0.05, value=float(auto_score), key=ov_key
            )

        st.text_area(
            "💬 Comment / notes", key=cmt_key, height=70,
            placeholder="Optional: add context, caveats, or observations…"
        )

    # Return effective score
    if st.session_state.get(use_key, False):
        return float(st.session_state.get(ov_key, auto_score))
    return float(auto_score)


RATING_DESC = {
    "A": ("Very Strong Fit",  "Excellent candidate. High priority for engagement."),
    "B": ("Promising",         "Good fit with some areas to develop. Engage and monitor."),
    "C": ("Moderate",          "Mixed signals. Worth tracking but not top priority."),
    "D": ("Weak Fit",          "Significant gaps. Low priority unless context changes."),
}
RATING_COLOR = {"A":"rating-A","B":"rating-B","C":"rating-C","D":"rating-D"}

# ════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="main-header">
  <h1>⚡ H2 Project Ranking Engine</h1>
  <p>Evaluate and rank hydrogen projects based on viability, readiness, storage need, and strategic fit.</p>
</div>
""", unsafe_allow_html=True)

col_form, col_result = st.columns([3, 2], gap="large")

# All effective scores collected here (filled during form rendering)
eff = {}

with col_form:

    # ── Project Info ───────────────────────────────────────────────────────
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">📋 Project Information</div>', unsafe_allow_html=True)
    r1c1, r1c2 = st.columns(2)
    project_name = r1c1.text_input("Project Name", placeholder="e.g. Masdar Green H2")
    evaluated_by = r1c2.text_input("Evaluated by", placeholder="Your name")
    r2c1, r2c2 = st.columns(2)
    region    = r2c1.selectbox("Project Region", REGIONS)
    eval_date = r2c2.date_input("Date", value=date.today())
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Application & Market ───────────────────────────────────────────────
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">🏭 Application & Market</div>', unsafe_allow_html=True)

    application = st.selectbox("1. Application area?", list(APPLICATIONS.keys()))
    app_auto    = APPLICATIONS.get(application, {"storage_required":0.5,"viability":0.5})
    eff["app_sr"] = score_modifier("app_sr", app_auto["storage_required"], "Storage Required",
        {k: v["storage_required"] for k,v in APPLICATIONS.items()})
    eff["app_vi"] = score_modifier("app_vi", app_auto["viability"], "Viability",
        {k: v["viability"] for k,v in APPLICATIONS.items()})

    country_fit = st.selectbox("2. Country a good fit?", list(COUNTRY_FIT.keys()))
    eff["country_fit"] = score_modifier("country_fit", COUNTRY_FIT.get(country_fit,0), "Viability", COUNTRY_FIT)

    national_prio = st.selectbox("3. Is it the project of national priority?", list(NATIONAL_PRIORITY.keys()))
    eff["nat_prio"] = score_modifier("nat_prio", NATIONAL_PRIORITY.get(national_prio,0), "Viability", NATIONAL_PRIORITY)

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Funding ────────────────────────────────────────────────────────────
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">💰 Funding & Finance</div>', unsafe_allow_html=True)

    fc1, fc2 = st.columns(2)
    total_cost      = fc1.number_input("4. Total project cost (Mil. €)", min_value=0.0, step=10.0)
    funding_secured = fc2.number_input("5. Funding secured (Mil. €)", min_value=0.0, step=10.0)
    auto_fund = funding_score(total_cost if total_cost>0 else None, fun
