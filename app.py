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
  div[data-testid="stTextInput"] label {
    font-weight: 600; font-size: 0.9rem; color: #28251d;
  }
  .stProgress > div > div { background-color: #01696f; }

  /* Question score panel */
  .q-score-panel {
    background: #f0f7f7;
    border: 1px solid #b2d8da;
    border-radius: 8px;
    padding: 0.75rem 1rem;
    margin-top: 0.4rem;
    margin-bottom: 0.6rem;
    font-size: 0.85rem;
  }
  .q-score-pill {
    display: inline-block;
    background: #01696f;
    color: white;
    font-weight: 700;
    font-size: 0.8rem;
    padding: 0.15rem 0.6rem;
    border-radius: 20px;
    margin-right: 0.5rem;
  }
  .q-score-label {
    color: #4a7c7e;
    font-size: 0.82rem;
  }
  /* Expander tweak: make the "view/modify" label small and inline */
  .small-expander > details > summary {
    font-size: 0.75rem !important;
    color: #7a7974 !important;
    padding: 0.1rem 0 !important;
  }
</style>
""", unsafe_allow_html=True)

# ── Scoring rules ────────────────────────────────────────────────────────────
APPLICATIONS = {
    "PtP":           {"storage_required": 1,   "viability": 0.5},
    "E-Saf":         {"storage_required": 0.5, "viability": 1},
    "E-Methanol":    {"storage_required": 0.5, "viability": 1},
    "E-Ammonia":     {"storage_required": 0.5, "viability": 1},
    "Iron Reduction":{"storage_required": 0.5, "viability": 1},
    "Heating":       {"storage_required": 0.5, "viability": 0.5},
    "HRS":           {"storage_required": 1,   "viability": 0.5},
    "Others":        {"storage_required": 0.5, "viability": 0.5},
}

NATIONAL_PRIORITY  = {"Yes": 1, "No": 0, "Not sure": 0.5}
CONTRACT_SIGNED    = {"Yes": 1, "A Few": 0.5, "Not Any": 0}
H2_SOURCE          = {"Produced Onsite": 1, "Purchased via Pipeline": 0, "Purchased Other": 1}
PPA_SIGNED         = {"Yes, self-production": 1, "Yes, with others": 1, "No": 0}
POWER_SOURCE       = {"Onsite-wind and solar": 1, "Hydro and Nuclear": 0.5,
                      "Stable Grid": 0.5, "Dynamic Grid": 1}
OFFTAKER           = {"Yes, Binding": 1, "Yes, Self Consumption": 1, "Yes, MoU": 0.5, "No": 0}
LAND_AREA          = {"Yes": 1, "No": 0, "In Process": 0.5}
PERMITS            = {"Permitted": 1, "Applied": 0.5, "No Update": 0}
ENG_MATURITY       = {"Pre-Feed": 0.5, "Feed": 1, "Waiting FID": 1, "FID": 1,
                      "Under Construction": 0.5, "Operational": 0}
H2_DNA             = {"Yes": 1, "50-50": 0.5, "No": 0}
TRACK_RECORD       = {"Startup": 0, "Multiple H2 projects": 0.5, "Industrial giants": 1}
INNOVATION         = {"Yes": 1, "Prefer not to": 0, "May be": 0.5}
FOOTPRINT          = {"Yes": 1, "Not so much": 0.5, "Not at all": 0}
SAFETY             = {"Yes, absolutely": 1, "Preferred": 0.5, "Minimum": 0}
GEO_CONSTRAINT     = {"No constraints": 1, "Difficult": 0, "Not sure": 0.5}
COUNTRY_FIT        = {"Yes": 1, "No": 0, "Not Sure": 0.5}

REGIONS = ["Europe", "Middle East", "North America", "South America", "Asia", "Pacific", "Africa"]

def funding_score(total, secured):
    if total is None or total == 0:
        return 0
    ratio = (secured or 0) / total
    if ratio < 0.2:  return 0
    if ratio < 0.6:  return 0.5
    return 1

def quantity_score(qty):
    if qty is None: return 0
    if qty < 1:    return 0
    if qty < 5:    return 0.5
    if qty < 15:   return 1
    return 0.5

# ── Score categories ─────────────────────────────────────────────────────────
def compute_scores(answers, overrides=None):
    if overrides is None:
        overrides = {}
    app    = answers.get("application", "Others")
    app_s  = APPLICATIONS.get(app, {"storage_required": 0.5, "viability": 0.5})

    def get(key, mapping, default=0):
        raw = mapping.get(answers.get(key), default)
        return overrides.get(key, raw)

    def getv(key, val):
        return overrides.get(key, val)

    sr = 0
    sr += getv("app_sr", app_s["storage_required"])
    sr += getv("h2_quantity", quantity_score(answers.get("h2_quantity")))
    sr += get("footprint", FOOTPRINT)
    sr += get("safety", SAFETY)
    sr += get("geo_constraint", GEO_CONSTRAINT)
    sr_max = 5

    vi = 0
    vi += getv("app_vi", app_s["viability"])
    vi += getv("funding", funding_score(answers.get("total_cost"), answers.get("funding_secured")))
    vi += get("national_priority", NATIONAL_PRIORITY)
    vi += get("offtaker", OFFTAKER)
    vi += get("country_fit", COUNTRY_FIT)
    vi += get("permits", PERMITS)
    vi_max = 6

    rd = 0
    rd += get("contract_signed", CONTRACT_SIGNED)
    rd += get("land_area", LAND_AREA)
    rd += get("eng_maturity", ENG_MATURITY)
    rd += get("ppa_signed", PPA_SIGNED)
    rd += get("h2_source", H2_SOURCE)
    rd_max = 5

    sf = 0
    sf += get("power_source", POWER_SOURCE)
    sf += get("h2_dna", H2_DNA)
    sf += get("track_record", TRACK_RECORD)
    sf += get("innovation", INNOVATION)
    sf_max = 4

    total     = sr + vi + rd + sf
    total_max = sr_max + vi_max + rd_max + sf_max

    pct = total / total_max * 100
    if pct >= 80:   rating = "A"
    elif pct >= 60: rating = "B"
    elif pct >= 40: rating = "C"
    else:           rating = "D"

    return {
        "storage_required": (sr, sr_max),
        "viability":        (vi, vi_max),
        "readiness":        (rd, rd_max),
        "strategic_fit":    (sf, sf_max),
        "total":            (total, total_max),
        "pct":              round(pct, 1),
        "rating":           rating,
    }

RATING_DESC = {
    "A": ("Very Strong Fit", "This project is an excellent candidate. High priority for engagement."),
    "B": ("Promising",        "Good fit with some areas to develop. Engage and monitor closely."),
    "C": ("Moderate",         "Mixed signals. Worth tracking but not a top priority right now."),
    "D": ("Weak Fit",         "Significant gaps. Low priority unless context changes."),
}

RATING_COLOR = {"A": "rating-A", "B": "rating-B", "C": "rating-C", "D": "rating-D"}

st.markdown("""
<style>
/* --- EXISTING STYLES (keep yours above this) --- */

/* EXPANDER: remove box completely */
div[data-testid="stExpander"] {
    border: none !important;
    box-shadow: none !important;
    background: transparent !important;
    margin-top: -8px !important;
}

/* remove inner container styling */
div[data-testid="stExpander"] > div {
    border: none !important;
    background: transparent !important;
    padding: 0 !important;
}

/* make expander label small + right aligned */
div[data-testid="stExpander"] summary {
    font-size: 0.72rem !important;
    color: #7a7974 !important;
    padding: 0 !important;
    text-align: right;
}

/* remove extra spacing */
div[data-testid="stExpanderContent"] {
    padding-top: 0.3rem !important;
}
</style>
""", unsafe_allow_html=True)

# ── Helper: render a question row with expander ──────────────────────────────
def q_expander(q_key, label, auto_score, max_score=1, category=""):
    """
    Right-aligned, borderless expander.
    """
    override_key = f"override_{q_key}"
    toggle_key   = f"toggle_{q_key}"
    comment_key  = f"comment_{q_key}"
    score_key    = f"score_{q_key}"

    if override_key not in st.session_state:
        st.session_state[override_key] = False
    if comment_key not in st.session_state:
        st.session_state[comment_key] = ""
    if score_key not in st.session_state:
        st.session_state[score_key] = float(auto_score)

    # 🔥 RIGHT-ALIGNED layout
    col_l, col_r = st.columns([5, 1])

    with col_r:
        with st.expander("⚙️", expanded=False):

            col_a, col_b = st.columns([2, 3])

            with col_a:
                auto_display = f"{auto_score} / {max_score}"
                st.markdown(
                    f"<div style='font-size:0.75rem;color:#7a7974;font-weight:600;'>Auto</div>"
                    f"<div style='font-size:1.1rem;font-weight:700;color:#01696f;'>{auto_display}</div>",
                    unsafe_allow_html=True
                )

            with col_b:
                manual = st.toggle("Override", key=toggle_key, value=st.session_state[override_key])
                st.session_state[override_key] = manual

            if manual:
                new_score = st.number_input(
                    "Manual score",
                    min_value=0.0,
                    max_value=float(max_score),
                    value=float(st.session_state[score_key]),
                    step=0.25,
                    key=f"manual_input_{q_key}",
                    label_visibility="collapsed"
                )
                st.session_state[score_key] = new_score
            else:
                st.session_state[score_key] = float(auto_score)

            comment = st.text_input(
                "Comment",
                value=st.session_state[comment_key],
                placeholder="Add a note…",
                key=f"comment_input_{q_key}",
                label_visibility="collapsed"
            )
            st.session_state[comment_key] = comment

    effective = st.session_state[score_key] if st.session_state[override_key] else float(auto_score)
    return effective, st.session_state[comment_key]


# ── UI ────────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
  <h1>⚡ H2 Project Ranking Engine</h1>
  <p>Evaluate and rank hydrogen projects based on viability, readiness, storage need, and strategic fit.</p>
</div>
""", unsafe_allow_html=True)

col_form, col_result = st.columns([3, 2], gap="large")

# Collect all overrides
overrides = {}
comments  = {}

with col_form:
    # ── Project Info ─────────────────────────────────────────────────────────
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">📋 Project Information</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    project_name  = c1.text_input("Project Name", placeholder="e.g. Masdar Green H2")
    evaluated_by  = c2.text_input("Evaluated by", placeholder="Your name")
    c3, c4 = st.columns(2)
    region        = c3.selectbox("Project Region", REGIONS)
    eval_date     = c4.date_input("Date", value=date.today())
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Application & Market ─────────────────────────────────────────────────
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">🏭 Application & Market</div>', unsafe_allow_html=True)

    application = st.selectbox("1. Application area?", list(APPLICATIONS.keys()))
    app_s = APPLICATIONS.get(application, {"storage_required": 0.5, "viability": 0.5})
    v, c_ = q_expander("app_sr", "Application – Storage", app_s["storage_required"], 1)
    overrides["app_sr"] = v; comments["app_sr"] = c_

    country_fit = st.selectbox("2. Country a good fit?", list(COUNTRY_FIT.keys()))
    v, c_ = q_expander("country_fit", "Country fit", COUNTRY_FIT.get(country_fit, 0), 1)
    overrides["country_fit"] = v; comments["country_fit"] = c_

    national_prio = st.selectbox("3. Is it the project of national priority?", list(NATIONAL_PRIORITY.keys()))
    v, c_ = q_expander("national_priority", "National priority", NATIONAL_PRIORITY.get(national_prio, 0), 1)
    overrides["national_priority"] = v; comments["national_priority"] = c_

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Funding ──────────────────────────────────────────────────────────────
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">💰 Funding & Finance</div>', unsafe_allow_html=True)
    c5, c6 = st.columns(2)
    total_cost      = c5.number_input("4. Total project cost (Mil. €)", min_value=0.0, step=10.0)
    funding_secured = c6.number_input("5. Funding secured (Mil. €)", min_value=0.0, step=10.0)
    fs = funding_score(total_cost if total_cost > 0 else None,
                       funding_secured if funding_secured > 0 else None)
    v, c_ = q_expander("funding", "Funding ratio", fs, 1)
    overrides["funding"] = v; comments["funding"] = c_

    gov_funded = st.selectbox("6. Funded by government / grants?", ["Yes", "No", "Partial"])
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Technical ────────────────────────────────────────────────────────────
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">⚙️ Technical Setup</div>', unsafe_allow_html=True)

    h2_source = st.selectbox("7. Hydrogen Source?", list(H2_SOURCE.keys()))
    v, c_ = q_expander("h2_source", "H2 source", H2_SOURCE.get(h2_source, 0), 1)
    overrides["h2_source"] = v; comments["h2_source"] = c_

    electrolyzer = st.number_input("8. Electrolyzer Size (MW)", min_value=0.0, step=1.0)

    ppa_signed = st.selectbox("9. Power / H2 purchase agreement signed?", list(PPA_SIGNED.keys()))
    v, c_ = q_expander("ppa_signed", "PPA signed", PPA_SIGNED.get(ppa_signed, 0), 1)
    overrides["ppa_signed"] = v; comments["ppa_signed"] = c_

    power_source = st.selectbox("10. Power Source?", list(POWER_SOURCE.keys()))
    v, c_ = q_expander("power_source", "Power source", POWER_SOURCE.get(power_source, 0), 1)
    overrides["power_source"] = v; comments["power_source"] = c_

    h2_quantity = st.number_input("11. Quantity of H2 to be stored (tonnes)", min_value=0.0, step=0.5)
    qs = quantity_score(h2_quantity if h2_quantity > 0 else None)
    v, c_ = q_expander("h2_quantity", "H2 quantity", qs, 1)
    overrides["h2_quantity"] = v; comments["h2_quantity"] = c_

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Readiness ────────────────────────────────────────────────────────────
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">📊 Project Readiness</div>', unsafe_allow_html=True)

    contract_signed = st.selectbox("12. Contract signed with technology supplier?", list(CONTRACT_SIGNED.keys()))
    v, c_ = q_expander("contract_signed", "Contract", CONTRACT_SIGNED.get(contract_signed, 0), 1)
    overrides["contract_signed"] = v; comments["contract_signed"] = c_

    offtaker = st.selectbox("13. Offtaker found & contract signed?", list(OFFTAKER.keys()))
    v, c_ = q_expander("offtaker", "Offtaker", OFFTAKER.get(offtaker, 0), 1)
    overrides["offtaker"] = v; comments["offtaker"] = c_

    land_area = st.selectbox("14. Land area secured?", list(LAND_AREA.keys()))
    v, c_ = q_expander("land_area", "Land area", LAND_AREA.get(land_area, 0), 1)
    overrides["land_area"] = v; comments["land_area"] = c_

    permits = st.selectbox("15. Permitting status?", list(PERMITS.keys()))
    v, c_ = q_expander("permits", "Permits", PERMITS.get(permits, 0), 1)
    overrides["permits"] = v; comments["permits"] = c_

    eng_maturity = st.selectbox("16. Engineering Maturity / Project Stage?", list(ENG_MATURITY.keys()))
    v, c_ = q_expander("eng_maturity", "Eng. maturity", ENG_MATURITY.get(eng_maturity, 0), 1)
    overrides["eng_maturity"] = v; comments["eng_maturity"] = c_

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Developer ────────────────────────────────────────────────────────────
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">👤 Developer Profile</div>', unsafe_allow_html=True)

    h2_dna = st.selectbox("17. Is H2 in their DNA?", list(H2_DNA.keys()))
    v, c_ = q_expander("h2_dna", "H2 DNA", H2_DNA.get(h2_dna, 0), 1)
    overrides["h2_dna"] = v; comments["h2_dna"] = c_

    track_record = st.selectbox("18. Developer track record?", list(TRACK_RECORD.keys()))
    v, c_ = q_expander("track_record", "Track record", TRACK_RECORD.get(track_record, 0), 1)
    overrides["track_record"] = v; comments["track_record"] = c_

    innovation = st.selectbox("19. Open to innovative solutions?", list(INNOVATION.keys()))
    v, c_ = q_expander("innovation", "Innovation", INNOVATION.get(innovation, 0), 1)
    overrides["innovation"] = v; comments["innovation"] = c_

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Site Constraints ─────────────────────────────────────────────────────
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">🏗️ Site Constraints</div>', unsafe_allow_html=True)

    footprint = st.selectbox("20. Footprint constraint?", list(FOOTPRINT.keys()))
    v, c_ = q_expander("footprint", "Footprint", FOOTPRINT.get(footprint, 0), 1)
    overrides["footprint"] = v; comments["footprint"] = c_

    safety = st.selectbox("21. Safety a big deal?", list(SAFETY.keys()))
    v, c_ = q_expander("safety", "Safety", SAFETY.get(safety, 0), 1)
    overrides["safety"] = v; comments["safety"] = c_

    geo_constraint = st.selectbox("22. Geological constraints?", list(GEO_CONSTRAINT.keys()))
    v, c_ = q_expander("geo_constraint", "Geo constraint", GEO_CONSTRAINT.get(geo_constraint, 0), 1)
    overrides["geo_constraint"] = v; comments["geo_constraint"] = c_

    st.markdown('</div>', unsafe_allow_html=True)

    submitted = st.button("🚀 Evaluate Project")

# ── Build answers dict ────────────────────────────────────────────────────────
answers = {
    "application":      application,
    "country_fit":      country_fit,
    "national_priority":national_prio,
    "total_cost":       total_cost if total_cost > 0 else None,
    "funding_secured":  funding_secured if funding_secured > 0 else None,
    "h2_source":        h2_source,
    "ppa_signed":       ppa_signed,
    "power_source":     power_source,
    "h2_quantity":      h2_quantity if h2_quantity > 0 else None,
    "contract_signed":  contract_signed,
    "offtaker":         offtaker,
    "land_area":        land_area,
    "permits":          permits,
    "eng_maturity":     eng_maturity,
    "h2_dna":           h2_dna,
    "track_record":     track_record,
    "innovation":       innovation,
    "footprint":        footprint,
    "safety":           safety,
    "geo_constraint":   geo_constraint,
}

# Only pass overrides for keys where user actually toggled override on
active_overrides = {
    k: v for k, v in overrides.items()
    if st.session_state.get(f"toggle_{k}", False)
}

scores = compute_scores(answers, active_overrides)

# ── Results Panel ─────────────────────────────────────────────────────────────
with col_result:
    st.markdown("### 📈 Evaluation Results")

    rating = scores["rating"]
    rname, rdesc = RATING_DESC[rating]
    rcolor = RATING_COLOR[rating]

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

    total_v, total_m = scores["total"]
    st.markdown(f"""
    <div class="score-card">
      <div class="score-label">Total Score</div>
      <div><span class="score-value">{total_v:.1f}</span>
           <span class="score-max"> / {total_m}  ({scores["pct"]}%)</span></div>
      </div>
    """, unsafe_allow_html=True)

    st.progress(scores["pct"] / 100)

    cats = [
        ("🗃️ Storage Required",  "storage_required"),
        ("✅ Viability",         "viability"),
        ("📋 Readiness",         "readiness"),
        ("🎯 Strategic Fit",     "strategic_fit"),
    ]
    for label, key in cats:
        v, m = scores[key]
        pct_cat = v / m if m > 0 else 0
        st.markdown(f"""
        <div class="score-card">
          <div class="score-label">{label}</div>
          <div><span class="score-value" style="font-size:1.4rem;">{v:.1f}</span>
               <span class="score-max"> / {m}</span></div>
        </div>
        """, unsafe_allow_html=True)
        st.progress(pct_cat)

    # Show active overrides summary
    if any(st.session_state.get(f"toggle_{k}", False) for k in overrides):
        st.markdown("---")
        st.markdown("**⚠️ Active score overrides:**")
        for k in overrides:
            if st.session_state.get(f"toggle_{k}", False):
                st.markdown(f"- `{k}`: **{active_overrides[k]}**")

    # Export
    if submitted and project_name:
        export_data = {
            "project_name": project_name,
            "evaluated_by": evaluated_by,
            "region":       region,
            "date":         str(eval_date),
            "answers":      {k: str(v) for k, v in answers.items()},
            "overrides":    {k: v for k, v in active_overrides.items()},
            "comments":     {k: v for k, v in comments.items() if v},
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
            file_name=f"{project_name.replace(' ','_')}_score.json",
            mime="application/json"
        )

        df_export = pd.DataFrame([{
            "Project": project_name,
            "Region":  region,
            "Rating":  rating,
            "Score %": scores["pct"],
            "Storage Required": scores["storage_required"][0],
            "Viability":        scores["viability"][0],
            "Readiness":        scores["readiness"][0],
            "Strategic Fit":    scores["strategic_fit"][0],
            "Total":            scores["total"][0],
        }])
        st.download_button(
            label="⬇️ Download Evaluation (CSV)",
            data=df_export.to_csv(index=False),
            file_name=f"{project_name.replace(' ','_')}_score.csv",
            mime="text/csv"
        )

    if submitted:
        st.success("✅ Evaluation complete! Scores updated above.")
    else:
        st.info("👈 Fill in the form and click **Evaluate Project**.")
