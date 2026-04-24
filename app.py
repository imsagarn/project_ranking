import streamlit as st
from datetime import date


st.set_page_config(
    page_title="H2 Project Ranking Engine",
    page_icon="🏗️",
    layout="wide"
)
─────────────────────────────────────────────────────────────
# Custom Styles
# ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
.question-label {
    font-weight: 700;
    font-size: 1rem;
    color: #006072;
    margin-top: 0.75rem;
}
.form-small {
    font-size: 0.85rem;
    color: #6c6b66;
}
.score-box {
    border: 1px solid #dce6ea;
    border-radius: 12px;
    padding: 1rem;
    background: #f8fbfc;
}
.score-big {
    font-size: 2rem;
    font-weight: 800;
}
.section-gap {
    margin-top: 1.25rem;
    margin-bottom: 1rem;
}
.small-note {
    font-size: 0.80rem;
    color: #6c6b66;
}
hr {
    margin: 1.1rem 0;
}
</style>
""",unsafe_allow_html=True)# Allowed score steps
SCORE_STEPS=[0.0,0.25,0.5,0.75,1.0]

# ─────────────────────────────────────────────────────────────
# Editable scoring dictionaries
# ─────────────────────────────────────────────────────────────
# Q1: Application area scoring
# Since your original code did not define fixed logic for Q1,this mapping is editable.
# Format:
#   "Application Area": {"viability": <score>,"delphy": <score>}
APPLICATION_AREA_SCORES={
    "PtP": {"viability": 1.0,"delphy": 1.0},"E-Saf": {"viability": 0.75,"delphy": 0.75},"E-Methanol": {"viability": 0.75,"delphy": 0.50},"E-Ammonia": {"viability": 0.75,"delphy": 0.50},"Iron Reduction": {"viability": 1.0,"delphy": 0.75},"Heating": {"viability": 0.50,"delphy": 0.25},"HRS": {"viability": 0.50,"delphy": 0.50},"Others": {"viability": 0.50,"delphy": 0.50},}

# ─────────────────────────────────────────────────────────────
# Helper functions
# ─────────────────────────────────────────────────────────────
def storage_score(tons: float)-> float:
    """
    Keeps the same logic you had in the original code:
    <1-> 0
    <5-> 0.5
    <15-> 1
    else-> 0.5
    """
    if tons < 1:
        return 0.0
    elif tons < 5:
        return 0.5
    elif tons < 15:
        return 1.0
    else:
        return 0.5

def funding_score(total_cost: float,secured_cost: float)-> float:
    """
    Original funding logic from your code:
    ratio >=0.6-> 1
    ratio >=0.2-> 0.5
    else-> 0
    """
    if total_cost > 0:
        ratio=secured_cost/total_cost
        if ratio >=0.6:
            return 1.0
        elif ratio >=0.2:
            return 0.5
        else:
            return 0.0
    return 0.0

def yes_no_half(option: str,yes_label="Yes",no_label="No",half_label="Applied")-> float:
    mapping={
        yes_label: 1.0,no_label: 0.0,half_label: 0.5
    }
    return mapping[option]

def add_score(bucket,question_text,score):
    bucket.append((question_text,float(score)))def total_score(bucket):
    return round(sum(score for _,score in bucket),2)# ─────────────────────────────────────────────────────────────
# Session state defaults
# ─────────────────────────────────────────────────────────────
if "q6_h2_source" not in st.session_state:
    st.session_state["q6_h2_source"]="Produced on site"

# ─────────────────────────────────────────────────────────────
# Title
# ─────────────────────────────────────────────────────────────
st.title("⚡ H2 Project Ranking Engine")st.markdown('<div class="form-small">All scores are from 0 to 1 in increments of 0.25.</div>',unsafe_allow_html=True)# Buckets
VIABILITY=[]
DELPHY=[]

# ─────────────────────────────────────────────────────────────
# Project information
# ─────────────────────────────────────────────────────────────
st.subheader("Project Information")col1,col2=st.columns(2)project_name=col1.text_input("Project Name")evaluator=col2.text_input("Evaluator")col3,col4=st.columns(2)region=col3.text_input("Region")evaluation_date=col4.date_input("Date",date.today())st.markdown("---")st.subheader("Scoring Questions")# ─────────────────────────────────────────────────────────────
# 1. Application area
# ─────────────────────────────────────────────────────────────
st.markdown('<div class="question-label">1. Application area?</div>',unsafe_allow_html=True)q1=st.selectbox("Choose application area",list(APPLICATION_AREA_SCORES.keys()),key="q1_application_area")q1_viability=APPLICATION_AREA_SCORES[q1]["viability"]
q1_delphy=APPLICATION_AREA_SCORES[q1]["delphy"]

add_score(VIABILITY,"1. Application area-Project Viability",q1_viability)add_score(DELPHY,"1. Application area-Storage Required/Delphy",q1_delphy)c1,c2=st.columns(2)c1.info(f"Viability score:**{q1_viability}**")c2.info(f"Delphy score:**{q1_delphy}**")# ─────────────────────────────────────────────────────────────
# 2. Country a good fit?
# ─────────────────────────────────────────────────────────────
st.markdown('<div class="question-label">2. Country a good fit?</div>',unsafe_allow_html=True)col_policy,col_reach=st.columns(2)q2_policy=col_policy.selectbox("Stable policy",["Yes","No","Cannot say"],key="q2_policy")q2_policy_score={"Yes": 1.0,"No": 0.0,"Cannot say": 0.5}[q2_policy]
add_score(VIABILITY,"2. Stable policy",q2_policy_score)q2_reach=col_reach.selectbox("Vallourec Reach",["Yes","No","Progressive"],key="q2_reach")q2_reach_score={"Yes": 1.0,"No": 0.0,"Progressive": 0.5}[q2_reach]
add_score(DELPHY,"2. Vallourec Reach",q2_reach_score)col_policy.write(f"→ Viability:**{q2_policy_score}**")col_reach.write(f"→ Delphy:**{q2_reach_score}**")# ─────────────────────────────────────────────────────────────
# 3. National priority
# ─────────────────────────────────────────────────────────────
st.markdown('<div class="question-label">3. Is it the project of national priority?</div>',unsafe_allow_html=True)q3=st.selectbox("National priority?",["Yes","No","Not sure"],key="q3")q3_score={"Yes": 1.0,"No": 0.0,"Not sure": 0.5}[q3]
add_score(VIABILITY,"3. National priority",q3_score)st.write(f"→ Viability:**{q3_score}**")# ─────────────────────────────────────────────────────────────
# 4. Funding status
# ─────────────────────────────────────────────────────────────
st.markdown('<div class="question-label">4. What is the current funding status?</div>',unsafe_allow_html=True)f1,f2=st.columns(2)q4_total=f1.number_input("Total cost(Mil. Euro)",min_value=0.0,step=1.0,key="q4_total")q4_secured=f2.number_input("Secured Cost(Mil. Euro)",min_value=0.0,step=1.0,key="q4_secured")q4_score=funding_score(q4_total,q4_secured)add_score(VIABILITY,"4. Funding status",q4_score)st.write(f"→ Viability:**{q4_score}**")# ─────────────────────────────────────────────────────────────
# 5. Government funded?
# ─────────────────────────────────────────────────────────────
st.markdown('<div class="question-label">5. Is the project funded by government entities or government grants?</div>',unsafe_allow_html=True)q5=st.selectbox("Government funding?",["Yes","No","Applied"],key="q5")q5_score={"Yes": 1.0,"No": 0.0,"Applied": 0.5}[q5]
add_score(VIABILITY,"5. Government funding",q5_score)st.write(f"→ Viability:**{q5_score}**")# ─────────────────────────────────────────────────────────────
# 6. Source of hydrogen
# ─────────────────────────────────────────────────────────────
st.markdown('<div class="question-label">6. What is the source of hydrogen?</div>',unsafe_allow_html=True)q6=st.selectbox("Hydrogen source",["Produced on site","Purchased via. Pipeline","Purchased through other way"],key="q6_h2_source")q6_score_map={
    "Produced on site": 1.0,"Purchased via. Pipeline": 1.0,"Purchased through other way": 0.5,}
q6_score=q6_score_map[q6]
add_score(DELPHY,"6. Source of hydrogen",q6_score)st.write(f"→ Delphy:**{q6_score}**")# ─────────────────────────────────────────────────────────────
# Branch A: Produced on site
# ─────────────────────────────────────────────────────────────
if q6=="Produced on site":
    st.markdown("---")st.markdown("### Produced on site path")# 7. Electrolyzer size
    st.markdown('<div class="question-label">7. What is the size of electrolyzer(MW)?</div>',unsafe_allow_html=True)q7_dk=st.checkbox("I don't know",key="q7_onsite_dk")q7_electrolyzer_mw=st.number_input("Electrolyzer size(MW)",min_value=0.0,step=0.1,disabled=q7_dk,key="q7_onsite_mw")# 8. Source of power
    st.markdown('<div class="question-label">8. What is the source of power?</div>',unsafe_allow_html=True)q8=st.selectbox("Source of power",["Onsite renewables","Grid(stable)","Grid(unstable)","Other"],key="q8_power_source")q8_scores={
        "Onsite renewables": 1.0,"Grid(stable)": 0.5,"Grid(unstable)": 0.25,"Other": 0.0
    }
    q8_score=q8_scores[q8]
    add_score(DELPHY,"8. Source of power",q8_score)st.write(f"→ Delphy:**{q8_score}**")# 9. PPA signed
    st.markdown('<div class="question-label">9. Has the power purchase agreement been signed?</div>',unsafe_allow_html=True)q9=st.selectbox("Power purchase agreement signed?",["Yes","No","Applied"],key="q9_ppa")q9_score={"Yes": 1.0,"No": 0.0,"Applied": 0.5}[q9]
    add_score(VIABILITY,"9. Power purchase agreement signed",q9_score)st.write(f"→ Viability:**{q9_score}**")# 10. Estimate tons stored
    st.markdown('<div class="question-label">10. Estimate the tons of H2 likely to be stored?</div>',unsafe_allow_html=True)q10_storage=st.number_input("Manual entry: Tons of H2 storage",min_value=0.0,step=0.5,key="q10_onsite_storage")q10_score=storage_score(q10_storage)add_score(DELPHY,"10. Estimated H2 storage",q10_score)st.write(f"→ Delphy score:**{q10_score}**")show_calc_onsite=st.checkbox("Calculate/View storage requirement",key="show_calc_onsite")if show_calc_onsite:
        st.markdown("#### Storage Calculator")calc1,calc2=st.columns(2)default_ele=0.0 if q7_dk else q7_electrolyzer_mw
        calc_ele_mw=calc1.number_input("Electrolyzer size(MW)for calculation",min_value=0.0,step=0.1,value=float(default_ele),key="calc_ele_mw")calc_hours=calc2.number_input("Hours of storage",min_value=0.0,step=1.0,key="calc_onsite_hours")# NOTE:
        # Your text says: ele_MW*0.7*hours_of_storage*55
        # But your note says "55 MWh per ton",which physically suggests division by 55.
        # I used DIVISION because it matches the note.
        # If you really want the exact typed formula,replace "/" with "*".
        calc_storage_tons=(calc_ele_mw*0.7*calc_hours)/55.0 if calc_hours > 0 else 0.0
        calc_storage_score=storage_score(calc_storage_tons)st.success(f"Calculated H2 storage:**{calc_storage_tons:.2f} tons**")st.info(f"Corresponding Delphy score:**{calc_storage_score}**")st.markdown('<div class="small-note">Calculating based on 70% capacity factor and 55 MWh per ton of hydrogen.</div>',unsafe_allow_html=True)# ─────────────────────────────────────────────────────────────
# Branch B: Purchased via. Pipeline
# ─────────────────────────────────────────────────────────────
elif q6=="Purchased via. Pipeline":
    st.markdown("---")st.markdown("### Purchased via. Pipeline path")# 7. Flowrate kg/day
    st.markdown('<div class="question-label">7. What is flowrate of hydrogen(kg/day)?</div>',unsafe_allow_html=True)q7_pipe_dk=st.checkbox("I don't know",key="q7_pipe_dk")q7_flowrate=st.number_input("Flowrate of hydrogen(kg/day)",min_value=0.0,step=10.0,disabled=q7_pipe_dk,key="q7_pipe_flowrate")# 8. Type of pipeline connection
    st.markdown('<div class="question-label">8. Type of pipeline connection?</div>',unsafe_allow_html=True)q8_pipe=st.selectbox("Pipeline connection type",["Dedicated through a producer","Connected to network","Not sure"],key="q8_pipe_type")q8_pipe_score={
        "Dedicated through a producer": 1.0,"Connected to network": 0.0,"Not sure": 0.5
    }[q8_pipe]
    add_score(DELPHY,"8. Type of pipeline connection",q8_pipe_score)st.write(f"→ Delphy:**{q8_pipe_score}**")# 9. H2 purchase agreement signed
    st.markdown('<div class="question-label">9. Has the hydrogen purchase agreement been signed?</div>',unsafe_allow_html=True)q9_pipe=st.selectbox("Hydrogen purchase agreement signed?",["Yes","No","Applied"],key="q9_pipe")q9_pipe_score={"Yes": 1.0,"No": 0.0,"Applied": 0.5}[q9_pipe]
    add_score(VIABILITY,"9. Hydrogen purchase agreement signed",q9_pipe_score)st.write(f"→ Viability:**{q9_pipe_score}**")# 10. Estimate tons stored
    st.markdown('<div class="question-label">10. Estimate the tons of H2 likely to be stored?</div>',unsafe_allow_html=True)q10_pipe_storage=st.number_input("Manual entry: Tons of H2 storage",min_value=0.0,step=0.5,key="q10_pipe_storage")q10_pipe_score=storage_score(q10_pipe_storage)add_score(DELPHY,"10. Estimated H2 storage",q10_pipe_score)st.write(f"→ Delphy score:**{q10_pipe_score}**")show_calc_pipe=st.checkbox("Calculate/View storage requirement",key="show_calc_pipe")if show_calc_pipe:
        st.markdown("#### Storage Calculator")p1,p2=st.columns(2)default_flow=0.0 if q7_pipe_dk else q7_flowrate
        calc_flowrate=p1.number_input("Hydrogen flowrate(kg/day)for calculation",min_value=0.0,step=10.0,value=float(default_flow),key="calc_pipe_flow")calc_pipe_hours=p2.number_input("Hours of storage",min_value=0.0,step=1.0,key="calc_pipe_hours")calc_storage_tons=(calc_flowrate/(1000*24))*calc_pipe_hours if calc_pipe_hours > 0 else 0.0
        calc_storage_score=storage_score(calc_storage_tons)st.success(f"Calculated H2 storage:**{calc_storage_tons:.2f} tons**")st.info(f"Corresponding Delphy score:**{calc_storage_score}**")st.markdown('<div class="small-note">Calculated as: flowrate/(1000 × 24)× hours of storage.</div>',unsafe_allow_html=True)# ─────────────────────────────────────────────────────────────
# Branch C: Purchased through other way
# ─────────────────────────────────────────────────────────────
elif q6=="Purchased through other way":
    st.markdown("---")st.markdown("### Purchased through other way path")# 7. Purchase agreement signed
    st.markdown('<div class="question-label">7. Has the purchase agreement been signed?</div>',unsafe_allow_html=True)q7_other=st.selectbox("Purchase agreement signed?",["Yes","No","Applied"],key="q7_other")q7_other_score={"Yes": 1.0,"No": 0.0,"Applied": 0.5}[q7_other]
    add_score(VIABILITY,"7. Purchase agreement signed",q7_other_score)st.write(f"→ Viability:**{q7_other_score}**")# 8. Estimate tons stored
    st.markdown('<div class="question-label">8. Estimate the tons of H2 likely to be stored?</div>',unsafe_allow_html=True)q8_other_storage=st.number_input("Manual entry: Tons of H2 storage",min_value=0.0,step=0.5,key="q8_other_storage")q8_other_score=storage_score(q8_other_storage)add_score(DELPHY,"8. Estimated H2 storage",q8_other_score)st.write(f"→ Delphy score:**{q8_other_score}**")# ─────────────────────────────────────────────────────────────
# Continue common questions
# ─────────────────────────────────────────────────────────────
st.markdown("---")# 11. Tech supplier contracts
st.markdown('<div class="question-label">11. Has contract been signed with technology suppliers?</div>',unsafe_allow_html=True)q11=st.selectbox("Technology supplier contract status",["Yes","No","Applied"],key="q11")q11_score={"Yes": 1.0,"No": 0.0,"Applied": 0.5}[q11]
add_score(VIABILITY,"11. Technology supplier contracts",q11_score)st.write(f"→ Viability:**{q11_score}**")# 12. Offtaker found and signed
st.markdown('<div class="question-label">12. Has the offtaker been found and contract signed?</div>',unsafe_allow_html=True)q12=st.selectbox("Offtaker contract status",["Yes","No","MoU"],key="q12")q12_score={"Yes": 1.0,"No": 0.0,"MoU": 0.5}[q12]
add_score(VIABILITY,"12. Offtaker found and contract signed",q12_score)st.write(f"→ Viability:**{q12_score}**")# 13. Land secured
st.markdown('<div class="question-label">13. Land area been secured?</div>',unsafe_allow_html=True)q13=st.selectbox("Land secured?",["Yes","No","In process"],key="q13")q13_score={"Yes": 1.0,"No": 0.0,"In process": 0.5}[q13]
add_score(VIABILITY,"13. Land secured",q13_score)st.write(f"→ Viability:**{q13_score}**")# 14. Permitting
st.markdown('<div class="question-label">14. What\'s the status of the permitting?</div>',unsafe_allow_html=True)q14=st.selectbox("Permitting status",["Permitted","Applied","No Update"],key="q14")q14_score={"Permitted": 1.0,"Applied": 0.5,"No Update": 0.0}[q14]
add_score(VIABILITY,"14. Permitting status",q14_score)st.write(f"→ Viability:**{q14_score}**")# 15. Current status of project
st.markdown('<div class="question-label">15. What is the current status of project?</div>',unsafe_allow_html=True)q15=st.selectbox("Project status",[
        "Conceptual","FEED","Waiting FID less than 2 years","Waiting more than 2 years","Under construction"
    ],key="q15")# NOTE:
# You gave 5 options but only 4 scores in your message.
# I used a logical maturity progression here.
q15_map={
    "Conceptual": 0.25,"FEED": 0.50,"Waiting FID less than 2 years": 0.75,"Waiting more than 2 years": 0.25,"Under construction": 1.0
}
q15_score=q15_map[q15]
add_score(VIABILITY,"15. Current status of project",q15_score)st.write(f"→ Viability:**{q15_score}**")# 16. H2 in their DNA
st.markdown('<div class="question-label">16. Is H2 in their DNA?</div>',unsafe_allow_html=True)q16=st.selectbox("H2 in their DNA?",["Yes","No","50-50"],key="q16")q16_score={"Yes": 1.0,"No": 0.0,"50-50": 0.5}[q16]
add_score(VIABILITY,"16. H2 in their DNA",q16_score)st.write(f"→ Viability:**{q16_score}**")# 17. Developer track record
st.markdown('<div class="question-label">17. Developer track record?</div>',unsafe_allow_html=True)q17=st.selectbox("Developer track record",["Startup","Multiple H2 projects","Industrial giants"],key="q17")q17_score={
    "Startup": 0.0,"Multiple H2 projects": 0.5,"Industrial giants": 1.0
}[q17]
add_score(VIABILITY,"17. Developer track record",q17_score)st.write(f"→ Viability:**{q17_score}**")# 18. Open to innovative solutions
st.markdown('<div class="question-label">18. Are the developer and stakeholders open to innovative solutions?</div>',unsafe_allow_html=True)q18=st.selectbox("Open to innovative solutions?",["Yes","No","May be"],key="q18")q18_score={"Yes": 1.0,"No": 0.0,"May be": 0.5}[q18]
add_score(DELPHY,"18. Open to innovative solutions",q18_score)st.write(f"→ Delphy:**{q18_score}**")# 19. Footprint constraint
st.markdown('<div class="question-label">19. Is there a footprint constrain in the area?</div>',unsafe_allow_html=True)q19=st.selectbox("Footprint constraint?",["Yes","Not so much","Not at all"],key="q19")q19_score={"Yes": 1.0,"Not so much": 0.5,"Not at all": 0.0}[q19]
add_score(DELPHY,"19. Footprint constraint",q19_score)st.write(f"→ Delphy:**{q19_score}**")# 20. Safety
st.markdown('<div class="question-label">20. Safety a big deal?</div>',unsafe_allow_html=True)q20=st.selectbox("Safety importance",["Yes,absolutely","Preferred","Minimum"],key="q20")q20_score={"Yes,absolutely": 1.0,"Preferred": 0.5,"Minimum": 0.0}[q20]
add_score(DELPHY,"20. Safety importance",q20_score)st.write(f"→ Delphy:**{q20_score}**")# 21. Geology
st.markdown('<div class="question-label">21. How is the geology in the area?</div>',unsafe_allow_html=True)q21=st.selectbox("Geology in the area",["No constraints","Difficult","Not sure"],key="q21")q21_score={"No constraints": 1.0,"Difficult": 0.0,"Not sure": 0.5}[q21]
add_score(DELPHY,"21. Geology in the area",q21_score)st.write(f"→ Delphy:**{q21_score}**")# ─────────────────────────────────────────────────────────────
# Results
# ─────────────────────────────────────────────────────────────
st.markdown("---")calculate=st.button("Calculate/View Scores",type="primary")if calculate:
    total_viability=total_score(VIABILITY)total_delphy=total_score(DELPHY)max_viability=len(VIABILITY)max_delphy=len(DELPHY)st.subheader("🏆 Project Score Summary")s1,s2=st.columns(2)with s1:
        st.markdown(f"""
            <div class="score-box">
                <div><strong>Project Viability</strong></div>
                <div class="score-big" style="color:#277f5c;">{total_viability}/{max_viability}</div>
            </div>
            """,unsafe_allow_html=True)with s2:
        st.markdown(f"""
            <div class="score-box">
                <div><strong>Delphy Chance to Win</strong></div>
                <div class="score-big" style="color:#4682b4;">{total_delphy}/{max_delphy}</div>
            </div>
            """,unsafe_allow_html=True)st.markdown("---")st.subheader("Detailed Score Breakdown")d1,d2=st.columns(2)with d1:
        st.markdown("#### Viability breakdown")for question,score in VIABILITY:
            st.write(f"-**{question}**: {score}")with d2:
        st.markdown("#### Delphy breakdown")for question,score in DELPHY:
            st.write(f"-**{question}**: {score}")st.success("Scores calculated successfully.")
