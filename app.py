# ⚡ H2 Project Ranking Engine
# Evaluate, save, compare, edit, and rank hydrogen projects
# based on project viability and Delphy chance to win.

import streamlit as st
import pandas as pd
import json
import os
import plotly.graph_objects as go
from datetime import date, datetime

st.set_page_config(
    page_title="H2 Project Ranking Engine",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

SAVE_FILE = "saved_project_scores.json"

st.markdown("""
<style>
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
.small-note { font-size: 0.82rem; color: #666; margin-top: -0.25rem; margin-bottom: 0.5rem; }
.manage-box { background: #ffffff; border: 1px solid #e2e4f0; border-radius: 10px; padding: 1rem; margin-top: 1rem; }
.edit-banner { background: #fff8e1; border: 1px solid #ffe082; color: #7c5b00; border-radius: 10px; padding: 0.85rem 1rem; margin-bottom: 1rem; }
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
ENG_MATURITY       = {
    "Conceptual": 0.25,
    "Feed": 0.75,
    "Waiting FID less than 2 years": 0.5,
    "Waiting more than 2 years": 1,
    "Under Construction": 0.5
}
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
RATING_DOT = {"A": "#2E8B57", "B": "#1E88E5", "C": "#F9A825", "D": "#D32F2F"}

# ── Session state defaults ─────────────────────────────────────────────────────

DEFAULTS = {
    "project_name": "",
    "evaluated_by": "",
    "region": None,
    "eval_date": None,

    "application": None,
    "stable_policy": None,
    "vallourec_reach": None,
    "national_prio": None,

    "total_cost": "",
    "funding_secured": "",
    "gov_funded": None,

    "h2_source": None,
    "electrolyzer_mw": "",
    "electrolyzer_unknown": False,
    "power_source": None,
    "ppa_signed": None,
    "h2_qty_onsite": "",
    "hours_storage_onsite": "",
    "flowrate_kgday": "",
    "flowrate_unknown": False,
    "pipeline_type": None,
    "h2_purchase_signed": None,
    "h2_qty_pipeline": "",
    "hours_storage_pipeline": "",
    "other_purchase_agr": None,
    "h2_qty_other": "",

    "contract_signed": None,
    "offtaker": None,
    "land_area": None,
    "permits": None,
    "eng_maturity": None,

    "h2_dna": None,
    "track_record": None,
    "innovation": None,
    "footprint": None,
    "safety": None,
    "geo_constraint": None,

    "selected_saved_project": None,
    "flash_message": "",
    "flash_type": "success",
    "editing_original_key": None,
    "editing_label": "",
}

ALL_QIDS = [f"q{i}" for i in range(1, 22)]

for k, v in DEFAULTS.items():
    st.session_state.setdefault(k, v)

for qid in ALL_QIDS:
    st.session_state.setdefault(f"override_{qid}", False)
    st.session_state.setdefault(f"comment_{qid}", "")

# FIX: pending actions so widget-bound state is only modified
# BEFORE widgets are rendered on the next rerun.
st.session_state.setdefault("pending_load_record", None)
st.session_state.setdefault("pending_reset_form", None)

# ── Persistence helpers ────────────────────────────────────────────────────────

def project_key(name, region):
    return f"{(name or '').strip().lower()}__{(region or '').strip().lower()}"

def load_saved_projects():
    if not os.path.exists(SAVE_FILE):
        return []
    try:
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []

def save_saved_projects(records):
    with open(SAVE_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)

def delete_saved_project(name, region):
    records = load_saved_projects()
    key_to_delete = project_key(name, region)
    new_records = [
        r for r in records
        if project_key(r.get("project_name", ""), r.get("region", "")) != key_to_delete
    ]
    save_saved_projects(new_records)

def get_saved_projects_df():
    records = load_saved_projects()
    if not records:
        return pd.DataFrame(columns=[
            "project_name", "region", "date", "rating",
            "viability_pct", "delphy_pct", "h2_quantity_tonnes", "total_pct"
        ])
    df = pd.DataFrame(records)

    numeric_cols = [
        "viability_score", "viability_max", "viability_pct",
        "delphy_score", "delphy_max", "delphy_pct",
        "total_score", "total_max", "total_pct",
        "h2_quantity_tonnes"
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    if "updated_at" in df.columns:
        df = df.sort_values(by=["updated_at"], ascending=False)
    return df

# ── Helpers ────────────────────────────────────────────────────────────────────


def distinct_entry_colors(n):
    """
    Generate visually distinct colors for each saved entry.
    """
    if n <= 0:
        return []
    return [f"hsl({(i * 137.508) % 360:.1f}, 70%, 48%)" for i in range(n)]


def parse_float(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "")
    if text == "":
        return None
    try:
        return float(text)
    except Exception:
        return None

def parse_date_string(value):
    if not value:
        return None
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except Exception:
        return None

def optional_select(label, options, key):
    items = [None] + list(options)
    return st.selectbox(
        label,
        options=items,
        key=key,
        format_func=lambda x: "Select..." if x is None else x,
        label_visibility="collapsed"
    )

def text_input_optional(label, key, placeholder="", help_text=None):
    return st.text_input(label, key=key, placeholder=placeholder, help=help_text)

def format_tonnes_label(value):
    value = 0 if value is None else float(value)
    text = f"{value:.2f}".rstrip("0").rstrip(".")
    return f"{text}t"

def bubble_pixel_sizes(values, min_px=28, max_px=60):
    vals = list(values)
    if not vals:
        return []
    max_val = max(vals)
    if max_val <= 0:
        return [min_px for _ in vals]
    sizes = []
    for v in vals:
        scaled = min_px + ((max(v, 0) / max_val) ** 0.5) * (max_px - min_px)
        sizes.append(round(scaled, 1))
    return sizes

def serialize_form_state():
    data = {}
    for key in DEFAULTS:
        if key in ["selected_saved_project", "flash_message", "flash_type", "editing_original_key", "editing_label"]:
            continue
        value = st.session_state.get(key)
        if isinstance(value, date):
            data[key] = value.isoformat()
        else:
            data[key] = value
    return data

def serialize_review_state():
    review = {"overrides": {}, "comments": {}, "manual_scores": {}}
    for qid in ALL_QIDS:
        review["overrides"][qid] = bool(st.session_state.get(f"override_{qid}", False))
        review["comments"][qid] = st.session_state.get(f"comment_{qid}", "")
    for key, value in st.session_state.items():
        if key.startswith("manual_"):
            review["manual_scores"][key] = value
    return review

def clear_review_state():
    for qid in ALL_QIDS:
        st.session_state[f"override_{qid}"] = False
        st.session_state[f"comment_{qid}"] = ""
    manual_keys = [k for k in st.session_state.keys() if k.startswith("manual_")]
    for mk in manual_keys:
        del st.session_state[mk]

def reset_form(clear_editing=True):
    for k, v in DEFAULTS.items():
        if k in ["flash_message", "flash_type"]:
            continue
        if k in ["editing_original_key", "editing_label"] and not clear_editing:
            continue
        st.session_state[k] = v
    clear_review_state()

def load_project_into_form(record):
    reset_form(clear_editing=False)

    form_state = record.get("form_state", {})
    for key in DEFAULTS:
        if key in ["selected_saved_project", "flash_message", "flash_type", "editing_original_key", "editing_label"]:
            continue
        if key in form_state:
            value = form_state[key]
            if key == "eval_date":
                st.session_state[key] = parse_date_string(value)
            else:
                st.session_state[key] = value

    if not form_state:
        st.session_state["project_name"] = record.get("project_name", "")
        st.session_state["evaluated_by"] = record.get("evaluated_by", "")
        st.session_state["region"] = record.get("region", None)
        st.session_state["eval_date"] = parse_date_string(record.get("date", ""))
        answers = record.get("answers", {})
        map_back = {
            "application": "application",
            "stable_policy": "stable_policy",
            "vallourec_reach": "vallourec_reach",
            "national_priority": "national_prio",
            "gov_funded": "gov_funded",
            "h2_source": "h2_source",
            "power_source": "power_source",
            "ppa_signed": "ppa_signed",
            "pipeline_type": "pipeline_type",
            "h2_purchase_signed": "h2_purchase_signed",
            "other_purchase_agr": "other_purchase_agr",
            "contract_signed": "contract_signed",
            "offtaker": "offtaker",
            "land_area": "land_area",
            "permits": "permits",
            "eng_maturity": "eng_maturity",
            "h2_dna": "h2_dna",
            "track_record": "track_record",
            "innovation": "innovation",
            "footprint": "footprint",
            "safety": "safety",
            "geo_constraint": "geo_constraint",
        }
        for answer_key, state_key in map_back.items():
            st.session_state[state_key] = answers.get(answer_key)

        st.session_state["total_cost"] = "" if answers.get("total_cost") in [None, "None", ""] else str(answers.get("total_cost"))
        st.session_state["funding_secured"] = "" if answers.get("funding_secured") in [None, "None", ""] else str(answers.get("funding_secured"))

        qty = answers.get("h2_quantity")
        if qty not in [None, "None", ""]:
            if st.session_state.get("h2_source") == "Produced on site":
                st.session_state["h2_qty_onsite"] = str(qty)
            elif st.session_state.get("h2_source") == "Purchased via Pipeline":
                st.session_state["h2_qty_pipeline"] = str(qty)
            else:
                st.session_state["h2_qty_other"] = str(qty)

    clear_review_state()
    review_state = record.get("review_state", {})
    for qid, value in review_state.get("overrides", {}).items():
        st.session_state[f"override_{qid}"] = bool(value)
    for qid, value in review_state.get("comments", {}).items():
        st.session_state[f"comment_{qid}"] = value
    for key, value in review_state.get("manual_scores", {}).items():
        st.session_state[key] = value

    st.session_state["editing_original_key"] = project_key(record.get("project_name", ""), record.get("region", ""))
    st.session_state["editing_label"] = f"{record.get('project_name', 'Unnamed project')} | {record.get('region', 'Unknown region')}"

def build_saved_project_options(records):
    options = []
    for r in records:
        name = r.get("project_name", "Unnamed project")
        region = r.get("region", "Unknown region")
        date_txt = r.get("date", "")
        options.append(f"{name} | {region} | {date_txt}")
    return options

def find_record_by_option(option_text, records):
    for r in records:
        candidate = f"{r.get('project_name', 'Unnamed project')} | {r.get('region', 'Unknown region')} | {r.get('date', '')}"
        if candidate == option_text:
            return r
    return None

# ── Score helpers ──────────────────────────────────────────────────────────────

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
        return 0.25
    if qty < 50:
        return 1
    if qty < 100:
        return 0.5
    if qty <500:
        return 0.25
    return 0.5

def h2_source_val():
    return st.session_state.get("h2_source")

def get_h2_quantity():
    src = h2_source_val()
    if src == "Produced on site":
        return parse_float(st.session_state.get("h2_qty_onsite"))
    elif src == "Purchased via Pipeline":
        return parse_float(st.session_state.get("h2_qty_pipeline"))
    elif src == "Purchased through other way":
        return parse_float(st.session_state.get("h2_qty_other"))
    return None

def get_answers():
    src = h2_source_val()
    return {
        "application":        st.session_state.get("application"),
        "stable_policy":      st.session_state.get("stable_policy"),
        "vallourec_reach":    st.session_state.get("vallourec_reach"),
        "national_priority":  st.session_state.get("national_prio"),
        "total_cost":         parse_float(st.session_state.get("total_cost")),
        "funding_secured":    parse_float(st.session_state.get("funding_secured")),
        "gov_funded":         st.session_state.get("gov_funded"),
        "h2_source":          src,
        "power_source":       st.session_state.get("power_source"),
        "ppa_signed":         st.session_state.get("ppa_signed"),
        "pipeline_type":      st.session_state.get("pipeline_type"),
        "h2_purchase_signed": st.session_state.get("h2_purchase_signed"),
        "other_purchase_agr": st.session_state.get("other_purchase_agr"),
        "h2_quantity":        get_h2_quantity(),
        "contract_signed":    st.session_state.get("contract_signed"),
        "offtaker":           st.session_state.get("offtaker"),
        "land_area":          st.session_state.get("land_area"),
        "permits":            st.session_state.get("permits"),
        "eng_maturity":       st.session_state.get("eng_maturity"),
        "h2_dna":             st.session_state.get("h2_dna"),
        "track_record":       st.session_state.get("track_record"),
        "innovation":         st.session_state.get("innovation"),
        "footprint":          st.session_state.get("footprint"),
        "safety":             st.session_state.get("safety"),
        "geo_constraint":     st.session_state.get("geo_constraint"),
    }

def agreement_score_for_source(answers):
    src = answers.get("h2_source")
    if src == "Produced on site":
        s = PPA_SIGNED.get(answers.get("ppa_signed"), 0)
        return ("ppa_signed", s, "PPA / power agreement signed", "viability")
    elif src == "Purchased via Pipeline":
        s = H2_PURCHASE_SIGNED.get(answers.get("h2_purchase_signed"), 0)
        return ("h2_purchase_signed", s, "H2 purchase agreement signed", "viability")
    elif src == "Purchased through other way":
        s = OTHER_PURCHASE_AGR.get(answers.get("other_purchase_agr"), 0)
        return ("other_purchase_agr", s, "Purchase agreement signed", "viability")
    return ("agreement_signed", 0, "Agreement signed", "viability")

def build_components(answers):
    app = answers.get("application")
    app_s = APPLICATIONS.get(app, {"storage_required": 0, "viability": 0})
    src = answers.get("h2_source")
    agr_key, agr_score, agr_label, agr_cat = agreement_score_for_source(answers)

    components = {
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
        "national_priority": {
            "id": "national_priority", "question": "q3",
            "label": "National priority",
            "category": "viability", "score": NATIONAL_PRIORITY.get(answers.get("national_priority"), 0), "max": 1.0,
        },
        "funding": {
            "id": "funding", "question": "q4",
            "label": "Funding ratio",
            "category": "viability",
            "score": funding_score(answers.get("total_cost"), answers.get("funding_secured")), "max": 1.0,
        },
        "gov_funded": {
            "id": "gov_funded", "question": "q5",
            "label": "Government funded",
            "category": "viability", "score": GOV_FUNDED.get(answers.get("gov_funded"), 0), "max": 1.0,
        },
        "h2_source": {
            "id": "h2_source", "question": "q6",
            "label": "H2 source",
            "category": "delphy", "score": H2_SOURCE_OPTIONS.get(src, 0), "max": 1.0,
        },
        "agreement_signed": {
            "id": "agreement_signed", "question": "q9",
            "label": agr_label,
            "category": agr_cat, "score": agr_score, "max": 1.0,
        },
    }

    if src == "Produced on site":
        components["power_source"] = {
            "id": "power_source", "question": "q8",
            "label": "Power source",
            "category": "delphy", "score": POWER_SOURCE.get(answers.get("power_source"), 0), "max": 1.0,
        }

    if src == "Purchased via Pipeline":
        components["pipeline_type"] = {
            "id": "pipeline_type", "question": "q8",
            "label": "Pipeline connection type",
            "category": "delphy", "score": PIPELINE_TYPE.get(answers.get("pipeline_type"), 0), "max": 1.0,
        }

    components["h2_quantity"] = {
        "id": "h2_quantity", "question": "q10",
        "label": "H2 quantity to store",
        "category": "delphy", "score": quantity_score(answers.get("h2_quantity")), "max": 1.0,
    }

    components["contract_signed"] = {
        "id": "contract_signed", "question": "q11",
        "label": "Contract with technology supplier",
        "category": "viability", "score": CONTRACT_SIGNED.get(answers.get("contract_signed"), 0), "max": 1.0,
    }
    components["offtaker"] = {
        "id": "offtaker", "question": "q12",
        "label": "Offtaker contract",
        "category": "viability", "score": OFFTAKER.get(answers.get("offtaker"), 0), "max": 1.0,
    }
    components["land_area"] = {
        "id": "land_area", "question": "q13",
        "label": "Land secured",
        "category": "viability", "score": LAND_AREA.get(answers.get("land_area"), 0), "max": 1.0,
    }
    components["permits"] = {
        "id": "permits", "question": "q14",
        "label": "Permitting status",
        "category": "viability", "score": PERMITS.get(answers.get("permits"), 0), "max": 1.0,
    }
    components["eng_maturity"] = {
        "id": "eng_maturity", "question": "q15",
        "label": "Project status",
        "category": "viability", "score": ENG_MATURITY.get(answers.get("eng_maturity"), 0), "max": 1.0,
    }
    components["h2_dna"] = {
        "id": "h2_dna", "question": "q16",
        "label": "H2 in their DNA",
        "category": "viability", "score": H2_DNA.get(answers.get("h2_dna"), 0), "max": 1.0,
    }
    components["track_record"] = {
        "id": "track_record", "question": "q17",
        "label": "Developer track record",
        "category": "viability", "score": TRACK_RECORD.get(answers.get("track_record"), 0), "max": 1.0,
    }
    components["innovation"] = {
        "id": "innovation", "question": "q18",
        "label": "Open to innovative solutions",
        "category": "delphy", "score": INNOVATION.get(answers.get("innovation"), 0), "max": 1.0,
    }
    components["footprint"] = {
        "id": "footprint", "question": "q19",
        "label": "Footprint constraint",
        "category": "delphy", "score": FOOTPRINT.get(answers.get("footprint"), 0), "max": 1.0,
    }
    components["safety"] = {
        "id": "safety", "question": "q20",
        "label": "Safety importance",
        "category": "delphy", "score": SAFETY.get(answers.get("safety"), 0), "max": 1.0,
    }
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
    viability_score = 0.0
    viability_max = 0.0
    delphy_score = 0.0
    delphy_max = 0.0

    for comp in resolved.values():
        if comp["category"] == "viability":
            viability_score += comp["score"]
            viability_max += comp["max"]
        else:
            delphy_score += comp["score"]
            delphy_max += comp["max"]

    total = viability_score + delphy_score
    total_max = viability_max + delphy_max
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
        "viability": (viability_score, viability_max),
        "delphy":    (delphy_score, delphy_max),
        "total":     (total, total_max),
        "pct":       round(pct, 1),
        "rating":    rating,
        "components": resolved,
    }

def build_project_record(answers, scores):
    vv, vm = scores["viability"]
    dv, dm = scores["delphy"]
    tv, tm = scores["total"]
    viability_pct = round((vv / vm * 100), 1) if vm else 0.0
    delphy_pct = round((dv / dm * 100), 1) if dm else 0.0
    qty = float(get_h2_quantity() or 0.0)
    eval_date_value = st.session_state.get("eval_date")
    eval_date_text = eval_date_value.isoformat() if isinstance(eval_date_value, date) else ""

    return {
        "project_name": st.session_state.get("project_name", "").strip(),
        "evaluated_by": st.session_state.get("evaluated_by", "").strip(),
        "region": st.session_state.get("region", ""),
        "date": eval_date_text,
        "application": answers.get("application", ""),
        "h2_source": answers.get("h2_source", ""),
        "h2_quantity_tonnes": round(qty, 4),
        "viability_score": round(vv, 2),
        "viability_max": round(vm, 2),
        "viability_pct": viability_pct,
        "delphy_score": round(dv, 2),
        "delphy_max": round(dm, 2),
        "delphy_pct": delphy_pct,
        "total_score": round(tv, 2),
        "total_max": round(tm, 2),
        "total_pct": round(scores["pct"], 1),
        "rating": scores["rating"],
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "answers": {k: ("" if v is None else str(v)) for k, v in answers.items()},
        "form_state": serialize_form_state(),
        "review_state": serialize_review_state(),
    }

def upsert_project_record(record, original_key=None):
    records = load_saved_projects()
    new_key = project_key(record.get("project_name", ""), record.get("region", ""))
    remove_keys = {new_key}
    if original_key:
        remove_keys.add(original_key)

    records = [
        r for r in records
        if project_key(r.get("project_name", ""), r.get("region", "")) not in remove_keys
    ]
    records.append(record)
    records = sorted(records, key=lambda x: (
        x.get("project_name", "").lower(),
        x.get("region", "").lower()
    ))
    save_saved_projects(records)

# ── Bracket tag HTML helpers ───────────────────────────────────────────────────

def vtag():
    return '<span class="bracket-tag bracket-viability">Project Viability</span>'

def dtag():
    return '<span class="bracket-tag bracket-delphy">Delphy Chance to Win</span>'

# ── View/Modify ────────────────────────────────────────────────────────────────

def render_view_modify(qid, label="View/Modify"):
    answers = get_answers()
    components = build_components(answers)
    relevant = [c for c in components.values() if c["question"] == qid]

    with st.expander(label, expanded=False):
        if relevant:
            auto_total = sum(c["score"] for c in relevant)
            total_max = sum(c["max"] for c in relevant)
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
            st.markdown(
                '<div class="vm-muted">This question is used for calculation only, not direct scoring.</div>',
                unsafe_allow_html=True
            )

        st.text_area("Comment", key=f"comment_{qid}", height=65, placeholder="Add comment...")

def render_portfolio_chart():
    df = get_saved_projects_df()

    st.markdown("#### 🫧 Saved Project Portfolio")
    st.markdown(
        '<div class="small-note">X-axis = Project Viability (%), Y-axis = Delphy Chance to Win (%), '
        'bubble size = H₂ quantity to store (tonnes), legend = project name.</div>',
        unsafe_allow_html=True
    )

    if df.empty:
        st.info("No saved projects yet. Evaluate a project to create the portfolio chart.")
        return

    chart_df = df.copy()
    chart_df["project_name"] = chart_df["project_name"].fillna("Unnamed project")
    chart_df["region"] = chart_df["region"].fillna("Unknown region")
    counts = chart_df["project_name"].value_counts()

    chart_df["project_label"] = chart_df.apply(
        lambda r: r["project_name"] if counts.get(r["project_name"], 0) == 1 else f"{r['project_name']} | {r['region']}",
        axis=1
    )
    chart_df["size_value"] = pd.to_numeric(
        chart_df["h2_quantity_tonnes"], errors="coerce"
    ).fillna(0.0).clip(lower=0.0)
    chart_df["size_px"] = bubble_pixel_sizes(chart_df["size_value"].tolist())
    chart_df["size_text"] = chart_df["size_value"].apply(format_tonnes_label)

    # Unique color per saved entry
    chart_df = chart_df.reset_index(drop=True)
    chart_df["point_color"] = distinct_entry_colors(len(chart_df))

    fig = go.Figure()

    for _, row in chart_df.iterrows():
        fig.add_trace(go.Scatter(
            x=[row["viability_pct"]],
            y=[row["delphy_pct"]],
            mode="markers+text",
            name=row["project_label"],
            text=[row["size_text"]],
            textposition="middle center",
            textfont=dict(color="white", size=12, family="Inter, sans-serif"),
            marker=dict(
                size=row["size_px"],
                color=row["point_color"],  # unique fill color for each entry
                opacity=0.85,
                line=dict(
                    width=2,
                    color=RATING_DOT.get(row["rating"], "#FFFFFF")  # keep rating as border
                )
            ),
            hovertemplate=(
                f"<b>{row['project_name']}</b><br>"
                f"Region: {row['region']}<br>"
                f"Application: {row.get('application', '')}<br>"
                f"Date: {row.get('date', '')}<br>"
                f"Rating: {row.get('rating', '')}<br>"
                f"Project Viability: {row.get('viability_pct', 0):.1f}%<br>"
                f"Delphy Chance to Win: {row.get('delphy_pct', 0):.1f}%<br>"
                f"H₂ Qty: {row.get('h2_quantity_tonnes', 0):.2f} t<br>"
                f"Total: {row.get('total_pct', 0):.1f}%<extra></extra>"
            )
        ))

    fig.update_layout(
        xaxis_title="Project Viability (%)",
        yaxis_title="Delphy Chance to Win (%)",
        xaxis=dict(range=[0, 100]),
        yaxis=dict(range=[0, 100]),
        height=520,
        legend_title_text="Project",
        margin=dict(l=20, r=20, t=20, b=20)
    )

    fig.add_vline(x=50, line_dash="dash", line_color="#A0A0A0", opacity=0.7)
    fig.add_hline(y=50, line_dash="dash", line_color="#A0A0A0", opacity=0.7)

    st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": False})

    table_df = chart_df[[
        "project_name", "region", "date", "rating",
        "viability_pct", "delphy_pct", "h2_quantity_tonnes", "total_pct"
    ]].copy()
    table_df.columns = [
        "Project", "Region", "Date", "Rating",
        "Viability %", "Delphy %", "H2 Qty (t)", "Total %"
    ]
    st.dataframe(table_df, use_container_width=True, hide_index=True)



# ── FIX: process pending actions BEFORE any widgets are rendered ──────────────

def process_pending_actions():
    if st.session_state.get("pending_reset_form") is not None:
        clear_editing = st.session_state["pending_reset_form"]
        st.session_state["pending_reset_form"] = None
        reset_form(clear_editing=clear_editing)

    record = st.session_state.get("pending_load_record")
    if record is not None:
        st.session_state["pending_load_record"] = None
        load_project_into_form(record)

process_pending_actions()

# ── Header ─────────────────────────────────────────────────────────────────────

st.markdown("""
<div class="main-header">
  <h1>⚡ H2 Project Ranking Engine</h1>
  <p>Evaluate and rank hydrogen projects — Project Viability &amp; Delphy Chance to Win.</p>
</div>
""", unsafe_allow_html=True)

if st.session_state.get("flash_message"):
    if st.session_state.get("flash_type") == "success":
        st.success(st.session_state["flash_message"])
    elif st.session_state.get("flash_type") == "warning":
        st.warning(st.session_state["flash_message"])
    else:
        st.info(st.session_state["flash_message"])
    st.session_state["flash_message"] = ""

if st.session_state.get("editing_original_key"):
    st.markdown(
        f'<div class="edit-banner">✏️ Editing saved project: <strong>{st.session_state.get("editing_label", "")}</strong>. '
        f'Press save to overwrite the saved project.</div>',
        unsafe_allow_html=True
    )

col_form, col_result = st.columns([3, 2], gap="large")

# ── Form panel ─────────────────────────────────────────────────────────────────

with col_form:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">📋 Project Information</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.text_input("Project Name", placeholder="e.g. Masdar Green H2", key="project_name")
    with c2:
        st.text_input("Evaluated by", placeholder="Your name", key="evaluated_by")
    c3, c4 = st.columns(2)
    with c3:    
        st.markdown("Project Region")
        optional_select("", REGIONS, key="region")
    with c4:
        st.date_input("Date", key="eval_date", value=st.session_state.get("eval_date"))
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">🏭 Application &amp; Market</div>', unsafe_allow_html=True)

    st.markdown(f'**1. Application area?** {vtag()} {dtag()}', unsafe_allow_html=True)
    optional_select("Application area", APPLICATIONS.keys(), key="application")
    render_view_modify("q1")

    st.markdown('**2. Country a good fit?**', unsafe_allow_html=True)
    cq2a, cq2b = st.columns(2)
    with cq2a:
        st.markdown(f'Stable policy {vtag()}', unsafe_allow_html=True)
        optional_select("Stable policy", STABLE_POLICY.keys(), key="stable_policy")
    with cq2b:
        st.markdown(f'Vallourec Reach {dtag()}', unsafe_allow_html=True)
        optional_select("Vallourec reach", VALLOUREC_REACH.keys(), key="vallourec_reach")
    render_view_modify("q2")

    st.markdown(f'**3. Is it the project of national priority?** {vtag()}', unsafe_allow_html=True)
    optional_select("National priority", NATIONAL_PRIORITY.keys(), key="national_prio")
    render_view_modify("q3")

    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">💰 Funding &amp; Finance</div>', unsafe_allow_html=True)

    st.markdown(f'**4. What is the current funding status?** {vtag()}', unsafe_allow_html=True)
    cq4a, cq4b = st.columns(2)
    with cq4a:
        text_input_optional("Total cost (Mil. Euro)", key="total_cost", placeholder="e.g. 250")
    with cq4b:
        text_input_optional("Secured cost (Mil. Euro)", key="funding_secured", placeholder="e.g. 120")
    render_view_modify("q4")

    st.markdown(f'**5. Is the project funded by government entities or grants?** {vtag()}', unsafe_allow_html=True)
    optional_select("Government funded", GOV_FUNDED.keys(), key="gov_funded")
    render_view_modify("q5")

    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">⚙️ Technical Setup</div>', unsafe_allow_html=True)

    st.markdown(f'**6. What is the source of hydrogen?** {dtag()}', unsafe_allow_html=True)
    optional_select("Hydrogen source", H2_SOURCE_OPTIONS.keys(), key="h2_source")
    render_view_modify("q6")

    h2_src = st.session_state.get("h2_source")

    if h2_src == "Produced on site":
        st.markdown("**7. What is the size of electrolyzer (MW)?**", unsafe_allow_html=True)
        st.checkbox("I don't know", key="electrolyzer_unknown")
        if not st.session_state.get("electrolyzer_unknown", False):
            text_input_optional("Electrolyzer size (MW)", key="electrolyzer_mw", placeholder="e.g. 100")
        else:
            st.session_state["electrolyzer_mw"] = ""
            st.caption("Electrolyzer size not available — size-based storage calculator will be disabled.")

        st.markdown(f'**8. What is the source of power?** {dtag()}', unsafe_allow_html=True)
        optional_select("Power source", POWER_SOURCE.keys(), key="power_source")
        render_view_modify("q8")

        st.markdown(f'**9. Has the Power Purchase Agreement been signed?** {vtag()}', unsafe_allow_html=True)
        optional_select("PPA signed", PPA_SIGNED.keys(), key="ppa_signed")
        render_view_modify("q9")

        st.markdown(f'**10. Estimate the tons of H₂ likely to be stored?** {dtag()}', unsafe_allow_html=True)
        text_input_optional("Tonnes of H₂ to store", key="h2_qty_onsite", placeholder="e.g. 10")

        with st.expander("Calculate / View", expanded=False):
            ele_mw = parse_float(st.session_state.get("electrolyzer_mw"))
            if st.session_state.get("electrolyzer_unknown", False) or ele_mw is None or ele_mw == 0:
                st.warning("Enter the electrolyzer size in Q7 to use the calculator.")
            else:
                text_input_optional("Hours of storage", key="hours_storage_onsite", placeholder="e.g. 4")
                hrs = parse_float(st.session_state.get("hours_storage_onsite"))
                if hrs is not None:
                    calc_kg = ele_mw * 0.7 * hrs * 55
                    st.metric("Calculated H₂ storage need", f"{calc_kg:,.0f} kg  /  {calc_kg/1000:.2f} tonnes")
                    st.markdown(
                        '<p class="calc-note">Calculated based on 70% capacity factor and 55 kg of hydrogen per MWh produced.</p>',
                        unsafe_allow_html=True
                    )
                    st.info(f"💡 You can enter **{calc_kg/1000:.2f} tonnes** in the field above to use this estimate.")

            qty = parse_float(st.session_state.get("h2_qty_onsite")) or 0.0
            sc = quantity_score(qty)
            st.markdown(f"**Current score for {qty:.1f} t entered:** `{sc:.2f} / 1.0`")

        render_view_modify("q10", label="View/Modify Score")

    elif h2_src == "Purchased via Pipeline":
        st.markdown("**7. What is the flowrate of hydrogen (kg/day)?**", unsafe_allow_html=True)
        st.checkbox("I don't know", key="flowrate_unknown")
        if not st.session_state.get("flowrate_unknown", False):
            text_input_optional("Flowrate (kg/day)", key="flowrate_kgday", placeholder="e.g. 20000")
        else:
            st.session_state["flowrate_kgday"] = ""
            st.caption("Flowrate not available — flowrate-based storage calculator will be disabled.")

        st.markdown(f'**8. Type of pipeline connection?** {dtag()}', unsafe_allow_html=True)
        optional_select("Pipeline connection type", PIPELINE_TYPE.keys(), key="pipeline_type")
        render_view_modify("q8")

        st.markdown(f'**9. Has the hydrogen purchase agreement been signed?** {vtag()}', unsafe_allow_html=True)
        optional_select("H2 purchase agreement signed", H2_PURCHASE_SIGNED.keys(), key="h2_purchase_signed")
        render_view_modify("q9")

        st.markdown(f'**10. Estimate the tons of H₂ likely to be stored?** {dtag()}', unsafe_allow_html=True)
        text_input_optional("Tonnes of H₂ to store", key="h2_qty_pipeline", placeholder="e.g. 10")

        with st.expander("Calculate / View", expanded=False):
            flowrate = parse_float(st.session_state.get("flowrate_kgday"))
            if st.session_state.get("flowrate_unknown", False) or flowrate is None or flowrate == 0:
                st.warning("Enter the flowrate in Q7 to use the calculator.")
            else:
                text_input_optional("Hours of storage", key="hours_storage_pipeline", placeholder="e.g. 4")
                hrs = parse_float(st.session_state.get("hours_storage_pipeline"))
                if hrs is not None:
                    calc_tons = flowrate / (1000 * 24) * hrs
                    st.metric("Calculated H₂ storage need", f"{calc_tons:.4f} tonnes  /  {calc_tons*1000:.1f} kg")
                    st.info(f"💡 You can enter **{calc_tons:.4f} tonnes** in the field above to use this estimate.")

            qty = parse_float(st.session_state.get("h2_qty_pipeline")) or 0.0
            sc = quantity_score(qty)
            st.markdown(f"**Current score for {qty:.1f} t entered:** `{sc:.2f} / 1.0`")

        render_view_modify("q10", label="View/Modify Score")

    elif h2_src == "Purchased through other way":
        st.markdown(f'**7. Has the purchase agreement been signed?** {vtag()}', unsafe_allow_html=True)
        optional_select("Purchase agreement signed", OTHER_PURCHASE_AGR.keys(), key="other_purchase_agr")
        render_view_modify("q9")

        st.markdown(f'**8. Estimate the tons of H₂ likely to be stored?** {dtag()}', unsafe_allow_html=True)
        text_input_optional("Tonnes of H₂ to store", key="h2_qty_other", placeholder="e.g. 10")
        render_view_modify("q10", label="View/Modify Score")

    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">📊 Project Readiness</div>', unsafe_allow_html=True)

    st.markdown(f'**11. Has a contract been signed with technology suppliers?** {vtag()}', unsafe_allow_html=True)
    optional_select("Contract with technology supplier", CONTRACT_SIGNED.keys(), key="contract_signed")
    render_view_modify("q11")

    st.markdown(f'**12. Has the offtaker been found and contract signed?** {vtag()}', unsafe_allow_html=True)
    optional_select("Offtaker contract", OFFTAKER.keys(), key="offtaker")
    render_view_modify("q12")

    st.markdown(f'**13. Has land area been secured?** {vtag()}', unsafe_allow_html=True)
    optional_select("Land secured", LAND_AREA.keys(), key="land_area")
    render_view_modify("q13")

    st.markdown(f'**14. What is the status of the permitting?** {vtag()}', unsafe_allow_html=True)
    optional_select("Permitting status", PERMITS.keys(), key="permits")
    render_view_modify("q14")

    st.markdown(f'**15. What is the current status of the project?** {vtag()}', unsafe_allow_html=True)
    optional_select("Project status", ENG_MATURITY.keys(), key="eng_maturity")
    render_view_modify("q15")

    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">🎯 Strategic Fit</div>', unsafe_allow_html=True)

    st.markdown(f'**16. Is H₂ in their DNA?** {vtag()}', unsafe_allow_html=True)
    optional_select("H2 in their DNA", H2_DNA.keys(), key="h2_dna")
    render_view_modify("q16")

    st.markdown(f'**17. Developer track record?** {vtag()}', unsafe_allow_html=True)
    optional_select("Developer track record", TRACK_RECORD.keys(), key="track_record")
    render_view_modify("q17")

    st.markdown(f'**18. Are the developer and stakeholders open to innovative solutions?** {dtag()}', unsafe_allow_html=True)
    optional_select("Open to innovative solutions", INNOVATION.keys(), key="innovation")
    render_view_modify("q18")

    st.markdown(f'**19. Is there a footprint constraint in the area?** {dtag()}', unsafe_allow_html=True)
    optional_select("Footprint constraint", FOOTPRINT.keys(), key="footprint")
    render_view_modify("q19")

    st.markdown(f'**20. Safety a big deal?** {dtag()}', unsafe_allow_html=True)
    optional_select("Safety importance", SAFETY.keys(), key="safety")
    render_view_modify("q20")

    st.markdown(f'**21. How is the geology in the area?** {dtag()}', unsafe_allow_html=True)
    optional_select("Geology / geological constraints", GEO_CONSTRAINT.keys(), key="geo_constraint")
    render_view_modify("q21")

    st.markdown('</div>', unsafe_allow_html=True)

    b1, b2 = st.columns(2)
    with b1:
        submitted = st.button(
            "💾 Save Project Changes" if st.session_state.get("editing_original_key") else "🚀 Evaluate & Save Project",
            use_container_width=True
        )
    with b2:
        clear_clicked = st.button("🧹 Clear Form", use_container_width=True)
        if clear_clicked:
            st.session_state["pending_reset_form"] = True
            st.session_state["flash_message"] = "Form cleared."
            st.session_state["flash_type"] = "info"
            st.rerun()

# ── Results panel ──────────────────────────────────────────────────────────────

with col_result:
    st.markdown("### 📈 Evaluation Results")

    answers = get_answers()
    scores = compute_scores(answers)

    project_name = st.session_state.get("project_name", "").strip()
    region = st.session_state.get("region", "")
    eval_date = st.session_state.get("eval_date")

    if submitted:
        if not project_name:
            st.warning("Please enter a project name before saving.")
        elif not region:
            st.warning("Please select a project region before saving.")
        else:
            original_key = st.session_state.get("editing_original_key")
            record = build_project_record(answers, scores)
            upsert_project_record(record, original_key=original_key)

            action = "updated" if original_key else "saved"
            st.session_state["flash_message"] = f"✅ Evaluation {action} for **{project_name}**."
            st.session_state["flash_type"] = "success"

            # FIX: defer reset to next rerun before widgets are built
            st.session_state["pending_reset_form"] = True
            st.rerun()

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

    viability_pct = (vv / vm * 100) if vm > 0 else 0
    delphy_pct = (dv / dm * 100) if dm > 0 else 0

    st.markdown(f"""
    <div class="score-card">
      <div class="score-label">✅ Project Viability</div>
      <div><span class="score-value" style="font-size:1.4rem;">{vv:.2f}</span>
           <span class="score-max"> / {vm:.0f}  ({viability_pct:.1f}%)</span></div>
    </div>
    """, unsafe_allow_html=True)
    st.progress(vv / vm if vm > 0 else 0)

    st.markdown(f"""
    <div class="score-card">
      <div class="score-label">🎯 Delphy Chance to Win</div>
      <div><span class="score-value" style="font-size:1.4rem;">{dv:.2f}</span>
           <span class="score-max"> / {dm:.0f}  ({delphy_pct:.1f}%)</span></div>
    </div>
    """, unsafe_allow_html=True)
    st.progress(dv / dm if dm > 0 else 0)

    st.markdown("#### Score Breakdown")
    comps = scores["components"]
    viab_comps = [c for c in comps.values() if c["category"] == "viability"]
    delphy_comps = [c for c in comps.values() if c["category"] == "delphy"]

    with st.expander("📗 Project Viability — Details", expanded=False):
        for c in viab_comps:
            st.markdown(f"**{c['label']}**: `{c['score']:.2f}` / {c['max']:.1f}")

    with st.expander("📘 Delphy Chance to Win — Details", expanded=False):
        for c in delphy_comps:
            st.markdown(f"**{c['label']}**: `{c['score']:.2f}` / {c['max']:.1f}")

    if project_name:
        export_date = eval_date.isoformat() if isinstance(eval_date, date) else ""
        export_data = {
            "project_name": project_name,
            "evaluated_by": st.session_state.get("evaluated_by", ""),
            "region": region,
            "date": export_date,
            "answers": {k: ("" if v is None else str(v)) for k, v in answers.items()},
            "scores": {
                "viability": scores["viability"][0],
                "viability_max": scores["viability"][1],
                "viability_pct": round(viability_pct, 1),
                "delphy": scores["delphy"][0],
                "delphy_max": scores["delphy"][1],
                "delphy_pct": round(delphy_pct, 1),
                "total": scores["total"][0],
                "total_max": scores["total"][1],
                "pct": scores["pct"],
                "rating": rating,
                "h2_quantity_tonnes": get_h2_quantity(),
            }
        }

        st.download_button(
            label="⬇️ Download Current Evaluation (JSON)",
            data=json.dumps(export_data, indent=2),
            file_name=f"{project_name.replace(' ', '_')}_score.json",
            mime="application/json",
            use_container_width=True
        )

        df_export = pd.DataFrame([{
            "Project": project_name,
            "Region": region,
            "Date": export_date,
            "Rating": rating,
            "Viability %": round(viability_pct, 1),
            "Delphy %": round(delphy_pct, 1),
            "H2 Qty (t)": get_h2_quantity(),
            "Total %": scores["pct"],
        }])

        st.download_button(
            label="⬇️ Download Current Evaluation (CSV)",
            data=df_export.to_csv(index=False),
            file_name=f"{project_name.replace(' ', '_')}_score.csv",
            mime="text/csv",
            use_container_width=True
        )

    st.markdown("---")
    render_portfolio_chart()

    saved_df = get_saved_projects_df()
    saved_records = load_saved_projects()

    st.markdown('<div class="manage-box">', unsafe_allow_html=True)
    st.markdown("#### 💾 Saved Projects")

    if not saved_df.empty:
        st.download_button(
            label="⬇️ Download Saved Portfolio (CSV)",
            data=saved_df.to_csv(index=False),
            file_name="saved_project_portfolio.csv",
            mime="text/csv",
            use_container_width=True
        )

        options = ["-- Select project --"] + build_saved_project_options(saved_records)
        selected_option = st.selectbox("Choose saved project", options=options, index=0)

        e1, e2 = st.columns(2)

        with e1:
            if st.button("✏️ Edit Selected Project", use_container_width=True):
                if selected_option != "-- Select project --":
                    record = find_record_by_option(selected_option, saved_records)
                    if record:
                        # FIX: defer loading until next rerun
                        st.session_state["pending_load_record"] = record
                        st.session_state["flash_message"] = f"Loaded saved project for editing: **{record.get('project_name', '')}**."
                        st.session_state["flash_type"] = "info"
                        st.rerun()

        with e2:
            if st.button("🗑️ Delete Selected Project", use_container_width=True):
                if selected_option != "-- Select project --":
                    record = find_record_by_option(selected_option, saved_records)
                    if record:
                        delete_saved_project(record.get("project_name", ""), record.get("region", ""))
                        if st.session_state.get("editing_original_key") == project_key(record.get("project_name", ""), record.get("region", "")):
                            # FIX: defer reset until next rerun
                            st.session_state["pending_reset_form"] = True
                        st.session_state["flash_message"] = f"Deleted saved project: **{record.get('project_name', '')}**."
                        st.session_state["flash_type"] = "success"
                        st.rerun()
    else:
        st.info("👈 Fill in the form and click **Evaluate & Save Project**.")

    st.markdown('</div>', unsafe_allow_html=True)
