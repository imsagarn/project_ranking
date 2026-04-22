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

# Funding score: ratio of secured / total
def funding_score(total, secured):
    if total is None or total == 0:
        return 0
    ratio = (secured or 0) / total
    if ratio < 0.2:  return 0
    if ratio < 0.6:  return 0.5
    return 1

# H2 quantity score
def quantity_score(qty):
    if qty is None: return 0
    if qty < 1:    return 0
    if qty < 5:    return 0.5
    if qty < 15:   return 1
    return 0.5

# ── Score categories ─────────────────────────────────────────────────────────
def compute_scores(answers):
    app    = answers.get("application", "Others")
    app_s  = APPLICATIONS.get(app, {"storage_required": 0.5, "viability": 0.5})

    # --- Storage Required Score (max 5)
    sr = 0
    sr += app_s["storage_required"]
    sr += quantity_score(answers.get("h2_quantity"))
    sr += FOOTPRINT.get(answers.get("footprint"), 0)
    sr += SAFETY.get(answers.get("safety"), 0)
    sr += GEO_CONSTRAINT.get(answers.get("geo_constraint"), 0)
    sr_max = 5

    # --- Viability Score (max 6)
    vi = 0
    vi += app_s["viability"]
    vi += funding_score(answers.get("total_cost"), answers.get("funding_secured"))
    vi += NATIONAL_PRIORITY.get(answers.get("national_priority"), 0)
    vi += OFFTAKER.get(answers.get("offtaker"), 0)
    vi += COUNTRY_FIT.get(answers.get("country_fit"), 0)
    vi += PERMITS.get(answers.get("permits"), 0)
    vi_max = 6

    # --- Readiness Score (max 5)
    rd = 0
    rd += CONTRACT_SIGNED.get(answers.get("contract_signed"), 0)
    rd += LAND_AREA.get(answers.get("land_area"), 0)
    rd += ENG_MATURITY.get(answers.get("eng_maturity"), 0)
    rd += PPA_SIGNED.get(answers.get("ppa_signed"), 0)
    rd += H2_SOURCE.get(answers.get("h2_source"), 0)
    rd_max = 5

    # --- Strategic Fit Score (max 4)
    sf = 0
    sf += POWER_SOURCE.get(answers.get("power_source"), 0)
    sf += H2_DNA.get(answers.get("h2_dna"), 0)
    sf += TRACK_RECORD.get(answers.get("track_record"), 0)
    sf += INNOVATION.get(answers.get("innovation"), 0)
    sf_max = 4

    total     = sr + vi + rd + sf
    total_max = sr_max + vi_max + rd_max + sf_max  # 20

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

# ── UI ────────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
  <h1>⚡ H2 Project Ranking Engine</h1>
  <p>Evaluate and rank hydrogen projects based on viability, readiness, storage need, and strategic fit.</p>
</div>
""", unsafe_allow_html=True)

col_form, col_result = st.columns([3, 2], gap="large")

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

    # ── Question 1 ──────────────────────────────────────────────────────────
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">🏭 Application & Market</div>', unsafe_allow_html=True)
    application   = st.selectbox("1. Application area?", list(APPLICATIONS.keys()))
    country_fit   = st.selectbox("2. Country a good fit?", list(COUNTRY_FIT.keys()))
    national_prio = st.selectbox("3. Is it the project of national priority?", list(NATIONAL_PRIORITY.keys()))
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Funding ──────────────────────────────────────────────────────────────
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">💰 Funding & Finance</div>', unsafe_allow_html=True)
    c5, c6 = st.columns(2)
    total_cost      = c5.number_input("4. Total project cost (Mil. €)", min_value=0.0, step=10.0)
    funding_secured = c6.number_input("5. Funding secured (Mil. €)", min_value=0.0, step=10.0)
    gov_funded      = st.selectbox("6. Funded by government / grants?", ["Yes", "No", "Partial"])
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Technical ────────────────────────────────────────────────────────────
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">⚙️ Technical Setup</div>', unsafe_allow_html=True)
    h2_source     = st.selectbox("7. Hydrogen Source?", list(H2_SOURCE.keys()))
    electrolyzer  = st.number_input("8. Electrolyzer Size (MW)", min_value=0.0, step=1.0)
    ppa_signed    = st.selectbox("9. Power / H2 purchase agreement signed?", list(PPA_SIGNED.keys()))
    power_source  = st.selectbox("10. Power Source?", list(POWER_SOURCE.keys()))
    h2_quantity   = st.number_input("11. Quantity of H2 to be stored (tonnes)", min_value=0.0, step=0.5)
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Readiness ────────────────────────────────────────────────────────────
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">📊 Project Readiness</div>', unsafe_allow_html=True)
    contract_signed = st.selectbox("12. Contract signed with technology supplier?", list(CONTRACT_SIGNED.keys()))
    offtaker        = st.selectbox("13. Offtaker found & contract signed?", list(OFFTAKER.keys()))
    land_area       = st.selectbox("14. Land area secured?", list(LAND_AREA.keys()))
    permits         = st.selectbox("15. Permitting status?", list(PERMITS.keys()))
    eng_maturity    = st.selectbox("16. Engineering Maturity / Project Stage?", list(ENG_MATURITY.keys()))
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Developer ────────────────────────────────────────────────────────────
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">👤 Developer Profile</div>', unsafe_allow_html=True)
    h2_dna       = st.selectbox("17. Is H2 in their DNA?", list(H2_DNA.keys()))
    track_record = st.selectbox("18. Developer track record?", list(TRACK_RECORD.keys()))
    innovation   = st.selectbox("19. Open to innovative solutions?", list(INNOVATION.keys()))
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Site Constraints ─────────────────────────────────────────────────────
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">🏗️ Site Constraints</div>', unsafe_allow_html=True)
    footprint      = st.selectbox("20. Footprint constraint?", list(FOOTPRINT.keys()))
    safety         = st.selectbox("21. Safety a big deal?", list(SAFETY.keys()))
    geo_constraint = st.selectbox("22. Geological constraints?", list(GEO_CONSTRAINT.keys()))
    st.markdown('</div>', unsafe_allow_html=True)

    submitted = st.button("🚀 Evaluate Project")

# ── Results Panel ─────────────────────────────────────────────────────────────
with col_result:
    st.markdown("### 📈 Evaluation Results")

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
           <span class="score-max"> / {total_m}  ({scores["pct"]}%)</span></div>
      </div>
    """, unsafe_allow_html=True)

    # Progress bar
    st.progress(scores["pct"] / 100)

    # Category scores
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

    # Export
    if submitted and project_name:
        export_data = {
            "project_name": project_name,
            "evaluated_by": evaluated_by,
            "region":       region,
            "date":         str(eval_date),
            "answers":      {k: str(v) for k, v in answers.items()},
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

        # CSV export
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
