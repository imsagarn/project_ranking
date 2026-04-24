import streamlit as st
from datetime import date

st.set_page_config(page_title="H2 Project Ranking Engine", page_icon="⚡", layout="wide")

# ─── Custom Styles ────────────────────────────────────────
st.markdown("""
<style>
.question-label { font-weight: 600; font-size: 1rem; color:#006072;}
.score-row      { display:flex; gap:2rem; margin-bottom:0.75rem; }
.score-row > div{ flex:1; }
.form-small     { font-size:0.85rem; color: #6c6b66;}
hr { margin: 1.1rem 0; }
</style>
""", unsafe_allow_html=True)

step = 0.25
score_steps = [0, 0.25, 0.5, 0.75, 1.0]

# State initialization for branching UI logic
if "q6_h2_source" not in st.session_state:
    st.session_state["q6_h2_source"] = "Produced on site"
if "q7_dont_know" not in st.session_state:
    st.session_state["q7_dont_know"] = False
if "q_purchased_pipeline_7_dont_know" not in st.session_state:
    st.session_state["q_purchased_pipeline_7_dont_know"] = False

# Categories
VIABILITY = []
DELPHY = []

st.title("⚡ H2 Project Ranking Engine (Refactored)")

with st.form("project_form"):
    st.subheader("Project Information")
    col1, col2 = st.columns(2)
    pname = col1.text_input("Project Name")
    evaluator = col2.text_input("Evaluator")
    col3, col4 = st.columns(2)
    region = col3.text_input("Region")
    eval_date = col4.date_input("Date", date.today())

    st.markdown("----")
    st.subheader("Viability/Delphy Score")
    st.markdown('<div class="form-small">All scores are from 0 to 1, in increments of 0.25.</div>', unsafe_allow_html=True)

    # 1. Application area
    st.markdown('<div class="question-label">1. Application area?</div>', unsafe_allow_html=True)
    q1 = st.selectbox("Choose area", [
        "PtP", "E-Saf", "E-Methanol", "E-Ammonia", "Iron Reduction",
        "Heating", "HRS", "Others"
    ])
    # Choose score for Project Viability (for app), and for storage required (Delphy)
    q1_app_score = st.selectbox("Score for Project Viability", score_steps, key="q1_app")
    q1_storage_score = st.selectbox("Storage Required Score", score_steps, key="q1_storage")
    VIABILITY.append(q1_app_score)
    DELPHY.append(q1_storage_score)

    # 2. Country fit (2-in-1 answer)
    st.markdown('<div class="question-label">2. Country a good fit?</div>', unsafe_allow_html=True)
    ccol1, ccol2 = st.columns(2)
    q2_policy = ccol1.selectbox(
        "Stable policy", ["Yes", "No", "Cannot say"], key="q2_policy"
    )
    q2_policy_score = {"Yes": 1, "No": 0, "Cannot say": 0.5}[q2_policy]
    q2_policy_score = float(q2_policy_score)
    ccol1.write(f"→ Viability: {q2_policy_score}")

    q2_reach = ccol2.selectbox(
        "Vallourec Reach", ["Yes", "No", "Progressive"], key="q2_reach"
    )
    q2_reach_score = {"Yes": 1, "No": 0, "Progressive": 0.5}[q2_reach]
    q2_reach_score = float(q2_reach_score)
    ccol2.write(f"→ Delphy chance: {q2_reach_score}")
    VIABILITY.append(q2_policy_score)
    DELPHY.append(q2_reach_score)

    # 3. National priority
    st.markdown('<div class="question-label">3. Is it the project of national priority?</div>', unsafe_allow_html=True)
    q3 = st.selectbox("National priority?", ["Yes", "No", "Not sure"], key="q3")
    q3_score = {"Yes": 1, "No": 0, "Not sure": 0.5}[q3]
    st.write(f"→ Viability: {q3_score}")
    VIABILITY.append(float(q3_score))

    # 4. Funding status (pair input)
    st.markdown('<div class="question-label">4. What is the current funding status?</div>', unsafe_allow_html=True)
    col4a, col4b = st.columns(2)
    q4_total = col4a.number_input("Total cost (Mil. Euro)", min_value=0.0, step=1.0, key="q4_total")
    q4_secured = col4b.number_input("Secured Cost (Mil. Euro)", min_value=0.0, step=1.0, key="q4_secured")
    if q4_total > 0:
        ratio = q4_secured / q4_total
        if ratio >= 0.6: score = 1.0
        elif ratio >= 0.2: score = 0.5
        else: score = 0.0
    else:
        score = 0.0
    st.write(f"→ Viability: {score}")
    VIABILITY.append(float(score))

    # 5. Funded by governmental entities?
    st.markdown('<div class="question-label">5. Is the project funded by government entities or government grants?</div>', unsafe_allow_html=True)
    q5 = st.selectbox("Gov Funded?", ["Yes", "No", "Applied"], key="q5")
    q5_score = {"Yes": 1, "No": 0, "Applied": 0.5}[q5]
    st.write(f"→ Viability: {q5_score}")
    VIABILITY.append(float(q5_score))

    # 6. Source of hydrogen (branch)
    st.markdown('<div class="question-label">6. What is the source of hydrogen?</div>', unsafe_allow_html=True)
    q6 = st.selectbox("Hydrogen source?", [
        "Produced on site", "Purchased via. Pipeline", "Purchased through other way"
    ], key="q6_h2_source")
    q6_score_map = {
        "Produced on site": 1.0,
        "Purchased via. Pipeline": 1.0,
        "Purchased through other way": 0.5,
    }
    # Delphy bracket for this answer
    q6_score = q6_score_map[q6]
    DELPHY.append(float(q6_score))

    # BRANCHLOGIC
    if q6 == "Produced on site":
        # 7. Electrolyzer size, with "don't know"
        st.markdown('<div class="question-label">7. What is the size of electrolyzer (MW)?</div>', unsafe_allow_html=True)
        q7col1, q7col2 = st.columns([3,1])
        q7_val = q7col1.number_input("Electrolyzer size (MW)", min_value=0.0, step=0.1, key="q7_onsite_size")
        q7_checkbox = q7col2.checkbox("I don't know", key="q7_dont_know")
        ele_ok = not q7_checkbox

        # 8. What is the source of power?
        st.markdown('<div class="question-label">8. What is the source of power?</div>', unsafe_allow_html=True)
        q8 = st.selectbox("Source of power", [
            "Onsite renewables", "Grid (stable)", "Grid (unstable)", "Other"
        ], key="q8_power_source")
        q8_scores = {
            "Onsite renewables": 1.0,
            "Grid (stable)": 0.5,
            "Grid (unstable)": 0.25,
            "Other": 0.0,
        }
        d_pow_score = q8_scores[q8]
        DELPHY.append(d_pow_score)

        # 9. Has the power purchase agreement been signed?
        st.markdown('<div class="question-label">9. Has the power purchase agreement been signed?</div>', unsafe_allow_html=True)
        q9 = st.selectbox("PPA signed?", ["Yes", "No", "Applied"], key="q9_ppa")
        q9_scores = {"Yes": 1.0, "No": 0.0, "Applied": 0.5}
        v_ppa_score = q9_scores[q9]
        VIABILITY.append(v_ppa_score)

        # 10. Estimate tons of H2 likely to be stored + calc tool
        st.markdown('<div class="question-label">10. Estimate the tons of H2 likely to be stored?</div>', unsafe_allow_html=True)
        q10 = st.number_input("Manual entry: Tons of storage", min_value=0.0, step=0.5, key="q10_h2_est")
        # scoring logic per your code: <1 => 0, <5 => 0.5, <15 => 1, else 0.5
        if q10 < 1: s = 0
        elif q10 < 5: s = 0.5
        elif q10 < 15: s = 1
        else: s = 0.5
        DELPHY.append(s)
        st.write(f"→ Delphy Score: {s}")

        # Calculation tool
        st.markdown("**Calculate Storage:**")
        c_elec, c_time = st.columns(2)
        ele_mw = c_elec.number_input("Electrolyzer size for calculation (MW)", min_value=0.0, step=0.1, key="q10_calc_elec")
        hours_storage = c_time.number_input("Hours of storage", min_value=0.0, step=1.0, key="q10_calc_hours")
        if ele_mw and hours_storage:
            h2_storage = ele_mw * 0.7 * hours_storage * 55 / 55
            st.markdown(f"<span class='form-small'>Calculated hydrogen storage: <strong>{h2_storage:.2f} tons</strong></span>", unsafe_allow_html=True)
        st.caption("Calculating based on 70% capacity factor and 55 MWh/ton H2.")

    elif q6 == "Purchased via. Pipeline":
        # 7. What is flowrate of hydrogen kg/day?
        st.markdown('<div class="question-label">7. What is flowrate of hydrogen (kg/day)?</div>', unsafe_allow_html=True)
        f1, f2 = st.columns([3,1])
        q7_pipe = f1.number_input("Flowrate (kg/day)", min_value=0.0, step=10.0, key="q7_pipe_flow")
        q7_pipe_dk = f2.checkbox("I don't know", key="q_purchased_pipeline_7_dont_know")

        # 8. Type of pipeline connection?
        st.markdown('<div class="question-label">8. Type of pipeline connection?</div>', unsafe_allow_html=True)
        q8_pipe = st.selectbox("Pipeline connection", [
            "Dedicitated through a producer", "Connected to network", "Not sure"
        ], key="q8_pipe_type")
        q8_pipe_score = {
            "Dedicitated through a producer": 1.0,
            "Connected to network": 0.0,
            "Not sure": 0.5,
        }[q8_pipe]
        DELPHY.append(q8_pipe_score)

        # 9. Has the hydrogen purchase agreement been signed?
        st.markdown('<div class="question-label">9. Has the hydrogen purchase agreement been signed?</div>', unsafe_allow_html=True)
        q9 = st.selectbox("Purchase agreement signed?", ["Yes", "No", "Applied"], key="q9_pa_pipe")
        q9_score = {"Yes": 1.0, "No": 0.0, "Applied": 0.5}[q9]
        VIABILITY.append(q9_score)

        # 10. Estimate tons of H2 likely to be stored + calc
        st.markdown('<div class="question-label">10. Estimate the tons of H2 likely to be stored?</div>', unsafe_allow_html=True)
        q10_p = st.number_input("Manual entry: Tons of storage", min_value=0.0, step=0.5, key="q10_pipe_storage")
        if q10_p < 1: s = 0
        elif q10_p < 5: s = 0.5
        elif q10_p < 15: s = 1
        else: s = 0.5
        DELPHY.append(s)
        st.write(f"→ Delphy Score: {s}")

        # Calculate utility
        st.markdown("**Calculate Storage:**")
        c_flow, c_h = st.columns(2)
        flow_kg = c_flow.number_input("Hydrogen flowrate for calculation (kg/day)", min_value=0.0, step=10.0, key="q10_calc_flow")
        hours = c_h.number_input("Hours of storage", min_value=0.0, step=1.0, key="q10_pip_hours")
        if flow_kg and hours:
            # Formula: flowrate/(1000*24)*hours_of storage
            tons = (flow_kg / (1000*24)) * hours
            st.markdown(f"<span class='form-small'>Calculated hydrogen storage: <strong>{tons:.2f} tons</strong></span>", unsafe_allow_html=True)
        st.caption("Calculated as: flowrate/(1000*24) * hours of storage.")

    elif q6 == "Purchased through other way":
        # 7. Has the purchase agreement been signed?
        st.markdown('<div class="question-label">7. Has the purchase agreement been signed?</div>', unsafe_allow_html=True)
        q7_other = st.selectbox("Purchase agreement signed?", ["Yes", "No", "Applied"], key="q7_other")
        q7_other_score = {"Yes": 1.0, "No": 0.0, "Applied": 0.5}[q7_other]
        VIABILITY.append(q7_other_score)

        # 8. Estimate tons of H2 likely to be stored
        st.markdown('<div class="question-label">8. Estimate the tons of H2 likely to be stored?</div>',
            unsafe_allow_html=True)
        q8_other_storage = st.number_input("Manual entry: Tons of storage", min_value=0.0, step=0.5, key="q8_other_storage")
        if q8_other_storage < 1: s = 0
        elif q8_other_storage < 5: s = 0.5
        elif q8_other_storage < 15: s = 1
        else: s = 0.5
        DELPHY.append(s)
        st.write(f"→ Delphy Score: {s}")

    # Resume common questions
    # 11. Has contracted been signed with technology suppliers?
    st.markdown('<div class="question-label">11. Has contract been signed with technology suppliers?</div>', unsafe_allow_html=True)
    q11 = st.selectbox("Contract signed?", ["Yes", "No", "Applied"], key="q11_contract_signed")
    q11_score = {"Yes": 1, "No": 0, "Applied": 0.5}[q11]
    VIABILITY.append(float(q11_score))

    # 12. Offtaker found & contract signed?
    st.markdown('<div class="question-label">12. Has the offtaker been found and contract signed?</div>', unsafe_allow_html=True)
    q12 = st.selectbox("Offtaker/contract?", ["Yes", "No", "MoU"], key="q12_offtaker")
    q12_score = {"Yes": 1, "No": 0, "MoU": 0.5}[q12]
    VIABILITY.append(float(q12_score))

    # 13. Land area been secured?
    st.markdown('<div class="question-label">13. Land area been secured?</div>', unsafe_allow_html=True)
    q13 = st.selectbox("Land area secured?", ["Yes", "No", "In process"], key="q13_land")
    q13_score = {"Yes": 1, "No": 0, "In process": 0.5}[q13]
    VIABILITY.append(float(q13_score))

    # 14. Permitting status
    st.markdown('<div class="question-label">14. Whats the status of the permitting?</div>', unsafe_allow_html=True)
    q14 = st.selectbox("Permitting status?", ["Permitted", "Applied", "No Update"], key="q14_permit")
    q14_score = {"Permitted": 1, "Applied": 0.5, "No Update": 0}[q14]
    VIABILITY.append(float(q14_score))

    # 15. Project status
    st.markdown('<div class="question-label">15. What is the current status of project?</div>', unsafe_allow_html=True)
    q15 = st.selectbox("Current status?", [
        "Conceptual", "Feed", "Waiting fid < 2 year", "Waiting >2 years", "Under construction"
    ], key="q15_status")
    q15_map = {
        "Conceptual": 0.25, "Feed": 0.75, "Waiting fid < 2 year": 0.5,
        "Waiting >2 years": 1.0, "Under construction": 0.75,
    }
    q15_score = q15_map[q15]
    VIABILITY.append(q15_score)

    # 16. Is H2 in their DNA?
    st.markdown('<div class="question-label">16. Is H2 in their DNA?</div>', unsafe_allow_html=True)
    q16 = st.selectbox("H2 DNA?", ["Yes", "No", "50-50"], key="q16_dna")
    q16_score = {"Yes": 1, "No": 0, "50-50": 0.5}[q16]
    VIABILITY.append(float(q16_score))

    # 17. Developer track record
    st.markdown('<div class="question-label">17. Developer track record?</div>', unsafe_allow_html=True)
    q17 = st.selectbox("Developer track record?", ["Startup", "Multiple H2 projects", "Industrial giants"], key="q17_track")
    q17_score = {"Startup": 0, "Multiple H2 projects": 0.5, "Industrial giants": 1}[q17]
    VIABILITY.append(float(q17_score))

    # 18. Stakeholders open to innovative solutions?
    st.markdown('<div class="question-label">18. Are the developer and stakeholders open to innovative solutions?</div>', unsafe_allow_html=True)
    q18 = st.selectbox("Open to innovation?", ["Yes", "No", "May be"], key="q18_innov")
    q18_score = {"Yes": 1, "No": 0, "May be": 0.5}[q18]
    DELPHY.append(float(q18_score))

    # 19. Footprint constraint
    st.markdown('<div class="question-label">19. Is there a footprint constraint in the area?</div>', unsafe_allow_html=True)
    q19 = st.selectbox("Footprint constraint?", ["Yes", "Not so much", "Not at all"], key="q19_fp")
    q19_score = {"Yes": 1, "Not so much": 0.5, "Not at all": 0}[q19]
    DELPHY.append(float(q19_score))

    # 20. Safety a big deal?
    st.markdown('<div class="question-label">20. Safety a big deal?</div>', unsafe_allow_html=True)
    q20 = st.selectbox("Safety?", ["Yes, absolutely", "Preferred", "Minimum"], key="q20_safety")
    q20_score = {"Yes, absolutely": 1, "Preferred": 0.5, "Minimum": 0}[q20]
    DELPHY.append(float(q20_score))

    # 21. How is the geology in the area?
    st.markdown('<div class="question-label">21. How is the geology in the area?</div>', unsafe_allow_html=True)
    q21 = st.selectbox("Geology status?", ["No constraints", "Difficult", "Not sure"], key="q21_geo")
    q21_score = {"No constraints": 1, "Difficult": 0, "Not sure": 0.5}[q21]
    DELPHY.append(float(q21_score))

    # Score summary (+ rounding/capping)
    def score_sum(lst):
        return round(sum(lst), 2)
    total_viability = score_sum(VIABILITY)
    total_delphy = score_sum(DELPHY)
    submitted = st.form_submit_button("Calculate/View Scores")

st.markdown("----")
if submitted:
    st.success("Results calculated and shown below:")

    st.markdown(f"""
    <h4>🏆 <u>PROJECT SCORE SUMMARY</u></h4>
    <div class="score-row">
      <div>
        <h5>Project Viability</h5>
        <div style="font-size:2.2rem;font-weight:700;color: #277f5c;">{total_viability} / {len(VIABILITY)}</div>
      </div>
      <div>
        <h5>Delphy Chance to Win</h5>
        <div style="font-size:2.2rem;font-weight:700;color: #4682b4;">{total_delphy} / {len(DELPHY)}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("<hr>", unsafe_allow_html=True)
    st.info("You can further tune the scoring formulae or presentation layout for full production use.", icon='🛠️')
