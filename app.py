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

  .override-box {
    background: #fff8e1; border: 1px solid #ffe082;
    border-radius: 8px; padding: 0.8rem 1rem; margin-top: 0.5rem;
    font-size: 0.85rem;
  }
  .score-chip {
    display:inline-block; background:#cedcd8; color:#01696f;
    font-size:0.78rem; font-weight:700; padding:0.2rem 0.6rem;
    border-radius:20px; margin-left:0.4rem;
  }
  .override-chip {
    display:inline-block; background:#fff3cd; color:#856404;
    font-size:0.78rem; font-weight:700; padding:0.2rem 0.6rem;
    border-radius:20px; margin-left:0.4rem;
  }

  .stButton>button {
    background: #01696f; color: white; border: none;
    border-radius: 8px; padding: 0.65rem 2rem;
    font-weight: 600; font-size: 1rem; width: 100%;
    transition: background 0.2s;
  }
  .stButton>button:hover { background: #0c4e54; }
  .stProgress > div > div { background-color: #01696f; }
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

def funding_score(total, secured):
    if not total or total == 0: return 0
    ratio = (secured or 0) / total
    if ratio < 0.2: return 0
    if ratio < 0.6: return 0.5
    return 1

def quantity_score(qty):
    if qty is None: return 0
    if qty < 1:  return 0
    if qty < 5:  return 0.5
    if qty < 15: return 1
    return 0.5

# ── Helper: render a question row with View/Modify expander ─────────────────
def question_row(label, key, auto_score, category_tag, score_map_hint=None):
    """
    Renders the auto score chip and an expander with:
    - score explanation
    - optional override (0..max_score slider)
    - comment text box
    Returns (effective_score, comment)
    """
    override_key = f"override_{key}"
    comment_key  = f"comment_{key}"
    use_override_key = f"use_override_{key}"

    # Show score chip inline after the question label
    col_lbl, col_chip = st.columns([6, 1])
    with col_lbl:
        st.caption(f"**Auto-score:** {auto_score:.2f}  |  Category: *{category_tag}*")

    with st.expander("🔍 View / Modify score & comments"):
        st.markdown(f"<div class='override-box'>", unsafe_allow_html=True)

        # Score explanation
        if score_map_hint:
            rows = "".join(
                f"<tr><td style='padding:2px 10px 2px 0'>{opt}</td>"
                f"<td style='font-weight:600;color:#01696f'>{sc}</td></tr>"
                for opt, sc in score_map_hint.items()
            )
            st.markdown(
                f"<b>Score table for this question:</b><br>"
                f"<table style='font-size:0.82rem;margin-top:4px'>{rows}</table>",
                unsafe_allow_html=True
            )
        else:
            st.markdown(f"**Calculated auto-score:** `{auto_score:.2f}`")

        st.markdown("</div>", unsafe_allow_html=True)

        use_ov = st.checkbox("✏️ Override this score", key=use_override_key)
        if use_ov:
            override_val = st.number_input(
                "Override score (0.0 – 1.0)",
                min_value=0.0, max_value=1.0, step=0.05,
                value=float(auto_score),
                key=override_key
            )
        else:
            override_val = auto_score

        comment = st.text_area("💬 Comment / notes", key=comment_key, height=68,
                               placeholder="Optional: add context, caveats, or observations…")

    effective = override_val if use_ov else auto_score
    return effective, comment

# ── Main score calculator ────────────────────────────────────────────────────
def compute_scores(raw, overrides):
    def eff(key, auto): return overrides.get(key, auto)

    app    = raw.get("application", "Others")
    app_s  = APPLICATIONS.get(app, {"storage_required": 0.5, "viability": 0.5})

    # Storage Required (max 5)
    sr = 0
    sr += eff("application_sr",    app_s["storage_required"])
    sr += eff("h2_quantity",        quantity_score(raw.get("h2_quantity")))
    sr += eff("footprint",          FOOTPRINT.get(raw.get("footprint"), 0))
    sr += eff("safety",             SAFETY.get(raw.get("safety"), 0))
    sr += eff("geo_constraint",     GEO_CONSTRAINT.get(raw.get("geo_constraint"), 0))

    # Viability (max 6)
    vi = 0
    vi += eff("application_vi",     app_s["viability"])
    vi += eff("funding",            funding_score(raw.get("total_cost"), raw.get("funding_secured")))
    vi += eff("national_priority",  NATIONAL_PRIORITY.get(raw.get("national_priority"), 0))
    vi += eff("offtaker",           OFFTAKER.get(raw.get("offtaker"), 0))
    vi += eff("country_fit",        COUNTRY_FIT.get(raw.get("country_fit"), 0))
    vi += eff("permits",            PERMITS.get(raw.get("permits"), 0))

    # Readiness (max 5)
    rd = 0
    rd += eff("contract_signed",    CONTRACT_SIGNED.get(raw.get("contract_signed"), 0))
    rd += eff("land_area",          LAND_AREA.get(raw.get("land_area"), 0))
    rd += eff("eng_maturity",       ENG_MATURITY.get(raw.get("eng_maturity"), 0))
    rd += eff("ppa_signed",         PPA_SIGNED.get(raw.get("ppa_signed"), 0))
    rd += eff("h2_source",          H2_SOURCE.get(raw.get("h2_source"), 0))

    # Strategic Fit (max 4)
    sf = 0
    sf += eff("power_source",       POWER_SOURCE.get(raw.get("power_source"), 0))
    sf += eff("h2_dna",             H2_DNA.get(raw.get("h2_dna"), 0))
    sf += eff("track_record",       TRACK_RECORD.get(raw.get("track_record"), 0))
    sf += eff("innovation",         INNOVATION.get(raw.get("innovation"), 0))

    total     = sr + vi + rd + sf
    total_max = 20
    pct       = total / total_max * 100

    if pct >= 80:   rating = "A"
    elif pct >= 60: rating = "B"
    elif pct >= 40: rating = "C"
    else:           rating = "D"

    return {
        "storage_required": (sr, 5),
        "viability":        (vi, 6),
        "readiness":        (rd, 5),
        "strategic_fit":    (sf, 4),
        "total":            (total, total_max),
        "pct":              round(pct, 1),
        "rating":           rating,
    }

RATING_DESC = {
    "A": ("Very Strong Fit", "Excellent candidate. High priority for engagement."),
    "B": ("Promising",       "Good fit with some areas to develop. Engage and monitor."),
    "C": ("Moderate",        "Mixed signals. Worth tracking but not top priority."),
    "D": ("Weak Fit",        "Significant gaps. Low priority unless context changes."),
}
RATING_COLOR = {"A": "rating-A", "B": "rating-B", "C": "rating-C", "D": "rating-D"}

# ═════════════════════════════════════════
