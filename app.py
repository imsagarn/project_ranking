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
  .stButton>button {
    background: #01696f; color: white; border: none;
    border-radius: 8px; padding: 0.65rem 2rem;
    font-weight: 600; font-size: 1rem; width: 100%;
  }
  .stButton>button:hover { background: #0c4e54; }
  .stProgress > div > div { background-color: #01696f; }

  /* Ghost view/modify button override */
  button.vm-btn {
    background: none !important;
    border: none !important;
    box-shadow: none !important;
    color: #7a7974 !important;
    font-size: 0.75rem !important;
    font-weight: 500 !important;
    padding: 0 2px !important;
    width: auto !important;
    cursor: pointer;
    text-decoration: none;
  }
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
def score_modifier(field_key, auto_score, category, score_table=None,
                   viability_score=None, storage_score=None):
    """
    Minimal inline view/modify toggle.
    Shows only the score type(s) relevant to this question.
    """
    ov_key   = f"ov_val_{field_key}"
    use_key  = f"ov_use_{field_key}"
    cmt_key  = f"cmt_{field_key}"
    show_key = f"show_{field_key}"

    # Determine which score rows to display
    score_rows = []
    if viability_score is not None:
        score_rows.append(("Viability score", viability_score))
    if storage_score is not None:
        score_rows.append(("Storage required score", storage_score))
    if not score_rows:
        # fallback: infer from category
        if category == "Storage Required":
            score_rows.append(("Storage required score", auto_score))
        else:
            score_rows.append(("Viability score", auto_score))

    is_open = st.session_state.get(show_key, False)
    chevron = "▴" if is_open else "▾"

    # Ghost button: right-aligned, no border, no background
    _, btn_col = st.columns([9, 1])
    with btn_col:
        st.markdown(
            f"""
            <style>
            div[data-testid="column"]:last-child .stButton > button {{
                background: none !important;
                border: none !important;
                box-shadow: none !important;
                color: #9a9892 !important;
                font-size: 0.72rem !important;
                font-weight: 500 !important;
                padding: 0 2px !important;
                min-height: unset !important;
                width: auto !important;
                line-height: 1.4 !important;
                letter-spacing: 0.01em;
            }}
            div[data-testid="column"]:last-child .stButton > button:hover {{
                color: #01696f !important;
                background: none !important;
            }}
            </style>
            """,
            unsafe_allow_html=True
        )
        if st.button(f"view/modify {chevron}", key=f"btn_{field_key}"):
            st.session_state[show_key] = not is_open
            st.rerun()

    if st.session_state.get(show_key, False):
        pills_html = "&emsp;&nbsp;".join(
            f"<span style='color:#7a7974;font-size:0.8rem'>{label}:</span>&nbsp;"
            f"<b style='color:#01696f;font-size:0.8rem'>{val:.2f}</b>"
            for label, val in score_rows
        )

        st.markdown(
            f"""
            <div style='
                background:#f9f8f5;
                border:1px solid #e8e5e0;
                border-radius:8px;
                padding:12px 16px 4px 16px;
                margin-bottom:4px;
            '>
                <div style='margin-bottom:10px'>{pills_html}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

        with st.container():
            use_override = st.toggle("Override score", key=use_key)
            if use_override:
                st.number_input(
                    "Override value (0.0–1.0)", min_value=0.0, max_value=1.0,
                    step=0.05, value=float(auto_score), key=ov_key,
                    label_visibility="collapsed"
                )
            st.text_area(
                "Comment", key=cmt_key, height=60,
                placeholder="Add comment…", label_visibility="collapsed"
            )

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
    app_auto    = APPLICATIONS.get(application, {"storage_required": 0.5, "viability": 0.5})
    # Application has BOTH scores — show both in one modifier
    eff["app_sr"] = score_modifier(
        "app_sr", app_auto["storage_required"], "Storage Required",
        storage_score=app_auto["storage_required"],
        viability_score=app_auto["viability"]
    )
    # app_vi shares the same panel — derive from app_auto directly
    # (if user overrides app_sr, we mirror same override intent for viability)
    if st.session_state.get("ov_use_app_sr", False):
        eff["app_vi"] = float(st.session_state.get("ov_val_app_sr", app_auto["viability"]))
    else:
        eff["app_vi"] = app_auto["viability"]

    country_fit_sel = st.selectbox("2. Country a good fit?", list(COUNTRY_FIT.keys()))
    eff["country_fit"] = score_modifier(
        "country_fit", COUNTRY_FIT.get(country_fit_sel, 0), "Viability",
        COUNTRY_FIT, viability_score=COUNTRY_FIT.get(country_fit_sel, 0)
    )

    national_prio = st.selectbox("3. Is it the project of national priority?", list(NATIONAL_PRIORITY.keys()))
    eff["nat_prio"] = score_modifier(
        "nat_prio", NATIONAL_PRIORITY.get(national_prio, 0), "Viability",
        NATIONAL_PRIORITY, viability_score=NATIONAL_PRIORITY.get(national_prio, 0)
    )

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Funding ────────────────────────────────────────────────────────────
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">💰 Funding & Finance</div>', unsafe_allow_html=True)

    fc1, fc2 = st.columns(2)
    total_cost      = fc1.number_input("4. Total project cost (Mil. €)", min_value=0.0, step=10.0)
    funding_secured = fc2.number_input("5. Funding secured (Mil. €)", min_value=0.0, step=10.0)
    auto_fund = funding_score(total_cost if total_cost > 0 else None,
                              funding_secured if funding_secured > 0 else None)
    eff["funding"] = score_modifier(
        "funding", auto_fund, "Viability",
        {"< 20% secured": 0.0, "20–60% secured": 0.5, "> 60% secured": 1.0},
        viability_score=auto_fund
    )

    st.selectbox("6. Funded by government / grants?", ["Yes", "No", "Partial"])
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Technical Setup ────────────────────────────────────────────────────
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">⚙️ Technical Setup</div>', unsafe_allow_html=True)

    h2_source = st.selectbox("7. Hydrogen Source?", list(H2_SOURCE.keys()))
    eff["h2_source"] = score_modifier(
        "h2_source", H2_SOURCE.get(h2_source, 0), "Readiness",
        H2_SOURCE, viability_score=H2_SOURCE.get(h2_source, 0)
    )

    st.number_input("8. Electrolyzer Size (MW)", min_value=0.0, step=1.0)

    ppa_signed = st.selectbox("9. Power/H2 purchase agreement signed?", list(PPA_SIGNED.keys()))
    eff["ppa"] = score_modifier(
        "ppa", PPA_SIGNED.get(ppa_signed, 0), "Readiness",
        PPA_SIGNED, viability_score=PPA_SIGNED.get(ppa_signed, 0)
    )

    power_source = st.selectbox("10. Power Source?", list(POWER_SOURCE.keys()))
    eff["power"] = score_modifier(
        "power", POWER_SOURCE.get(power_source, 0), "Strategic Fit",
        POWER_SOURCE, viability_score=POWER_SOURCE.get(power_source, 0)
    )

    h2_qty = st.number_input("11. Quantity of H2 to be stored (tonnes)", min_value=0.0, step=0.5)
    auto_qty = quantity_score(h2_qty if h2_qty > 0 else None)
    eff["h2_qty"] = score_modifier(
        "h2_qty", auto_qty, "Storage Required",
        {"< 1 t": 0.0, "1–5 t": 0.5, "5–15 t": 1.0, "> 15 t": 0.5},
        storage_score=auto_qty  # storage only — no viability for this question
    )

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Project Readiness ──────────────────────────────────────────────────
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">📊 Project Readiness</div>', unsafe_allow_html=True)

    contract = st.selectbox("12. Contract signed with technology supplier?", list(CONTRACT_SIGNED.keys()))
    eff["contract"] = score_modifier(
        "contract", CONTRACT_SIGNED.get(contract, 0), "Readiness",
        CONTRACT_SIGNED, viability_score=CONTRACT_SIGNED.get(contract, 0)
    )

    offtaker = st.selectbox("13. Offtaker found & contract signed?", list(OFFTAKER.keys()))
    eff["offtaker"] = score_modifier(
        "offtaker", OFFTAKER.get(offtaker, 0), "Viability",
        OFFTAKER, viability_score=OFFTAKER.get(offtaker, 0)
    )

    land_area = st.selectbox("14. Land area secured?", list(LAND_AREA.keys()))
    eff["land"] = score_modifier(
        "land", LAND_AREA.get(land_area, 0), "Readiness",
        LAND_AREA, viability_score=LAND_AREA.get(land_area, 0)
    )

    permits = st.selectbox("15. Permitting status?", list(PERMITS.keys()))
    eff["permits"] = score_modifier(
        "permits", PERMITS.get(permits, 0), "Viability",
        PERMITS, viability_score=PERMITS.get(permits, 0)
    )

    eng = st.selectbox("16. Engineering Maturity / Project Stage?", list(ENG_MATURITY.keys()))
    eff["eng"] = score_modifier(
        "eng", ENG_MATURITY.get(eng, 0), "Readiness",
        ENG_MATURITY, viability_score=ENG_MATURITY.get(eng, 0)
    )

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Developer Profile ──────────────────────────────────────────────────
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">👤 Developer Profile</div>', unsafe_allow_html=True)

    h2_dna = st.selectbox("17. Is H2 in their DNA?", list(H2_DNA.keys()))
    eff["h2_dna"] = score_modifier(
        "h2_dna", H2_DNA.get(h2_dna, 0), "Strategic Fit",
        H2_DNA, viability_score=H2_DNA.get(h2_dna, 0)
    )

    track = st.selectbox("18. Developer track record?", list(TRACK_RECORD.keys()))
    eff["track"] = score_modifier(
        "track", TRACK_RECORD.get(track, 0), "Strategic Fit",
        TRACK_RECORD, viability_score=TRACK_RECORD.get(track, 0)
    )

    innov = st.selectbox("19. Open to innovative solutions?", list(INNOVATION.keys()))
    eff["innov"] = score_modifier(
        "innov", INNOVATION.get(innov, 0), "Strategic Fit",
        INNOVATION, viability_score=INNOVATION.get(innov, 0)
    )

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Site Constraints ───────────────────────────────────────────────────
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">🏗️ Site Constraints</div>', unsafe_allow_html=True)

    footprint = st.selectbox("20. Footprint constraint?", list(FOOTPRINT.keys()))
    eff["footprint"] = score_modifier(
        "footprint", FOOTPRINT.get(footprint, 0), "Storage Required",
        FOOTPRINT, storage_score=FOOTPRINT.get(footprint, 0)
    )

    safety = st.selectbox("21. Safety a big deal?", list(SAFETY.keys()))
    eff["safety"] = score_modifier(
        "safety", SAFETY.get(safety, 0), "Storage Required",
        SAFETY, storage_score=SAFETY.get(safety, 0)
    )

    geo = st.selectbox("22. Geological constraints?", list(GEO_CONSTRAINT.keys()))
    eff["geo"] = score_modifier(
        "geo", GEO_CONSTRAINT.get(geo, 0), "Storage Required",
        GEO_CONSTRAINT, storage_score=GEO_CONSTRAINT.get(geo, 0)
    )

    st.markdown('</div>', unsafe_allow_html=True)

    submitted = st.button("🚀 Evaluate Project")

# ── Compute scores ─────────────────────────────────────────────────────────────
sr = eff["app_sr"] + eff["h2_qty"] + eff["footprint"] + eff["safety"] + eff["geo"]
vi = eff["app_vi"] + eff["funding"] + eff["nat_prio"] + eff["offtaker"] + eff["country_fit"] + eff["permits"]
rd = eff["contract"] + eff["land"] + eff["eng"] + eff["ppa"] + eff["h2_source"]
sf = eff["power"] + eff["h2_dna"] + eff["track"] + eff["innov"]

total     = sr + vi + rd + sf
total_max = 20
pct       = round(total / total_max * 100, 1)

if pct >= 80:   rating = "A"
elif pct >= 60: rating = "B"
elif pct >= 40: rating = "C"
else:           rating = "D"

any_override = any(
    st.session_state.get(f"ov_use_{k}", False)
    for k in ["app_sr","country_fit","nat_prio","funding","h2_source","ppa",
              "power","h2_qty","contract","offtaker","land","permits","eng",
              "h2_dna","track","innov","footprint","safety","geo"]
)

# ── Results panel ─────────────────────────────────────────────────────────────
with col_result:
    st.markdown("### 📈 Evaluation Results")

    if any_override:
        st.warning("⚠️ One or more scores have been manually overridden.")

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

    st.markdown(f"""
    <div class="score-card">
      <div class="score-label">Total Score</div>
      <div>
        <span class="score-value">{total:.1f}</span>
        <span class="score-max"> / {total_max} &nbsp;({pct}%)</span>
      </div>
    </div>
    """, unsafe_allow_html=True)
    st.progress(pct / 100)

    for label, val, mx in [
        ("🗃️ Storage Required", sr, 5),
        ("✅ Viability",        vi, 6),
        ("📋 Readiness",        rd, 5),
        ("🎯 Strategic Fit",    sf, 4),
    ]:
        st.markdown(f"""
        <div class="score-card">
          <div class="score-label">{label}</div>
          <div>
            <span class="score-value" style="font-size:1.4rem;">{val:.1f}</span>
            <span class="score-max"> / {mx}</span>
          </div>
        </div>
        """, unsafe_allow_html=True)
        st.progress(val / mx if mx > 0 else 0)

    # Comments summary
    all_comments = {
        k: st.session_state.get(f"cmt_{k}", "")
        for k in ["app_sr","country_fit","nat_prio","funding","h2_source","ppa",
                  "power","h2_qty","contract","offtaker","land","permits","eng",
                  "h2_dna","track","innov","footprint","safety","geo"]
    }
    filled = {k: v for k, v in all_comments.items() if v and v.strip()}
    if filled:
        with st.expander(f"📝 Comments summary ({len(filled)} note(s))"):
            label_map = {
                "app_sr":"Application (Storage & Viability)","country_fit":"Country Fit",
                "nat_prio":"National Priority","funding":"Funding","h2_source":"H2 Source",
                "ppa":"PPA Signed","power":"Power Source","h2_qty":"H2 Quantity",
                "contract":"Contract Signed","offtaker":"Offtaker","land":"Land Area",
                "permits":"Permits","eng":"Engineering Maturity","h2_dna":"H2 in DNA",
                "track":"Track Record","innov":"Innovation","footprint":"Footprint",
                "safety":"Safety","geo":"Geology",
            }
            for k, v in filled.items():
                st.markdown(f"**{label_map.get(k,k)}:** {v}")

    # Export
    if submitted and project_name:
        overrides_used = {
            k: st.session_state.get(f"ov_val_{k}")
            for k in all_comments
            if st.session_state.get(f"ov_use_{k}", False)
        }
        export = {
            "project_name": project_name,
            "evaluated_by": evaluated_by,
            "region":       region,
            "date":         str(eval_date),
            "overrides":    {k: v for k, v in overrides_used.items() if v is not None},
            "comments":     filled,
            "scores": {
                "storage_required": round(sr, 3),
                "viability":        round(vi, 3),
                "readiness":        round(rd, 3),
                "strategic_fit":    round(sf, 3),
                "total":            round(total, 3),
                "total_max":        total_max,
                "pct":              pct,
                "rating":           rating,
            }
        }
        col_dl1, col_dl2 = st.columns(2)
        col_dl1.download_button(
            "⬇️ JSON", data=json.dumps(export, indent=2),
            file_name=f"{project_name.replace(' ','_')}_score.json",
            mime="application/json"
        )
        df_export = pd.DataFrame([{
            "Project": project_name, "Region": region, "Rating": rating,
            "Score %": pct, "Storage Required": sr, "Viability": vi,
            "Readiness": rd, "Strategic Fit": sf, "Total": total,
            "Overrides": len(overrides_used),
        }])
        col_dl2.download_button(
            "⬇️ CSV", data=df_export.to_csv(index=False),
            file_name=f"{project_name.replace(' ','_')}_score.csv",
            mime="text/csv"
        )
        st.success("✅ Evaluation complete!")
    else:
        st.info("👈 Fill in the form and click **Evaluate Project**.")
