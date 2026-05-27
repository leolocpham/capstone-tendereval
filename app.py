"""
TenderEval AI — Main Streamlit Application
Capstone Copper | Pinto Valley Operation
"""

import json
import os
import sys
from pathlib import Path

import streamlit as st

# Ensure utils/ is importable when running from the project root
sys.path.insert(0, str(Path(__file__).parent))

# ---------------------------------------------------------------------------
# Page config (must be first Streamlit call)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="TenderEval AI",
    page_icon="⛏️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Brand CSS
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    /* Capstone brand colours */
    :root {
        --navy: #052B48;
        --orange: #D05F27;
    }
    [data-testid="stSidebar"] {
        background-color: var(--navy);
    }
    [data-testid="stSidebar"] * {
        color: #FFFFFF !important;
    }
    [data-testid="stSidebar"] .stRadio label {
        color: #FFFFFF !important;
        font-family: Arial, sans-serif;
    }
    h1, h2, h3 { font-family: Arial, sans-serif; color: var(--navy); }
    .stButton > button {
        background-color: var(--orange);
        color: white;
        border: none;
        font-family: Arial, sans-serif;
        font-weight: bold;
    }
    .stButton > button:hover { background-color: #b34d1f; }
    .swot-S { background-color: #00B050; color: white; padding: 2px 8px; border-radius: 4px; font-weight: bold; }
    .swot-O { background-color: #FFFF00; color: black; padding: 2px 8px; border-radius: 4px; font-weight: bold; }
    .swot-N { background-color: #BFBFBF; color: black; padding: 2px 8px; border-radius: 4px; font-weight: bold; }
    .swot-T { background-color: #FFC000; color: black; padding: 2px 8px; border-radius: 4px; font-weight: bold; }
    .swot-W { background-color: #FF0000; color: white; padding: 2px 8px; border-radius: 4px; font-weight: bold; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Load default criteria once
# ---------------------------------------------------------------------------
CRITERIA_PATH = Path(__file__).parent / "data" / "default_criteria.json"


@st.cache_data
def load_default_criteria() -> dict:
    with open(CRITERIA_PATH, "r") as f:
        return json.load(f)


DEFAULT_CRITERIA = load_default_criteria()

# ---------------------------------------------------------------------------
# Saves directory + progress save/load helpers
# ---------------------------------------------------------------------------
SAVES_DIR = Path(__file__).parent / "saves"
SAVES_DIR.mkdir(exist_ok=True)


def save_progress() -> str:
    """Persist current session to saves/ and return the filename."""
    from datetime import datetime

    name = ev().get("eval_name", "session") or "session"
    safe = "".join(c if c.isalnum() or c in "._- " else "_" for c in name).strip().replace(" ", "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{safe}_{timestamp}.json"
    with open(SAVES_DIR / filename, "w") as fh:
        json.dump(ev(), fh, indent=2, default=str)
    return filename


def list_saves() -> list:
    """Return [(display_name, Path), …] for the 20 most-recent saves."""
    files = sorted(SAVES_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    return [(p.stem, p) for p in files[:20]]


# ---------------------------------------------------------------------------
# Session state initialisation
# ---------------------------------------------------------------------------
if "eval" not in st.session_state:
    st.session_state["eval"] = {
        "eval_name": "",
        "equipment_type": "",
        "tender_number": "",
        "bidders": [],
        "criteria": {},
        "scores": {},
        "tco": {},
        "tco_results": {},
        "api_key": "",
        "tender_doc_summary": "",
        "key_requirements": [],
        "last_saved": "",
    }

if "page" not in st.session_state:
    st.session_state["page"] = "⚙️ Setup"


def ev() -> dict:
    return st.session_state["eval"]


# ---------------------------------------------------------------------------
# Sidebar navigation
# ---------------------------------------------------------------------------
PAGES = [
    "⚙️ Setup",
    "📋 Evaluation Info",
    "📄 Tender Document",
    "✅ Review Criteria",
    "👥 Bidder Documents",
    "🔍 Score Review",
    "💰 TCO Analysis",
    "🏆 Results & Ranking",
    "📤 Export",
]

with st.sidebar:
    st.markdown(
        "<h2 style='color:white; font-family:Arial; margin-bottom:4px;'>⛏️ TenderEval AI</h2>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='color:#D05F27; font-size:12px; font-family:Arial; margin-top:0;'>"
        "Capstone Copper — Pinto Valley</p>",
        unsafe_allow_html=True,
    )
    st.divider()
    selected_page = st.radio("Navigation", PAGES, index=PAGES.index(st.session_state["page"]),
                             label_visibility="collapsed")
    st.session_state["page"] = selected_page

    # Quick status in sidebar
    st.divider()
    e = ev()
    if e["eval_name"]:
        st.markdown(f"**Eval:** {e['eval_name']}", unsafe_allow_html=False)
    if e["equipment_type"]:
        st.markdown(f"**Equipment:** {e['equipment_type']}")
    if e["bidders"]:
        st.markdown(f"**Bidders:** {', '.join(e['bidders'])}")
    api_ok = bool(e.get("api_key"))
    st.markdown(f"**API Key:** {'✅ Set' if api_ok else '❌ Not set'}")

    # ---- Progress save / load ----
    st.divider()
    if st.button("💾 Save Progress", key="sidebar_save"):
        fname = save_progress()
        ev()["last_saved"] = fname
        st.success("Saved!")
    if ev().get("last_saved"):
        st.caption(f"Last: {ev()['last_saved']}")

    saves = list_saves()
    if saves:
        with st.expander("📂 Load Saved Session"):
            for display_name, save_path in saves:
                label = display_name[:35] + ("…" if len(display_name) > 35 else "")
                if st.button(label, key=f"load_{display_name}"):
                    try:
                        with open(save_path) as fh:
                            loaded = json.load(fh)
                        st.session_state["eval"] = loaded
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Load failed: {exc}")

page = st.session_state["page"]

# ===========================================================================
# PAGE: ⚙️ Setup
# ===========================================================================
if page == "⚙️ Setup":
    st.title("⚙️ Setup — API Key")
    st.markdown(
        "Enter your **Anthropic API key** to enable AI-powered document extraction and scoring. "
        "Your key is stored only in this session and never saved to disk."
    )

    api_input = st.text_input(
        "Anthropic API Key",
        value=ev().get("api_key", ""),
        type="password",
        placeholder="sk-ant-...",
    )
    if st.button("Save API Key"):
        ev()["api_key"] = api_input.strip()
        st.success("API key saved for this session.")

    st.divider()
    st.markdown("### About TenderEval AI")
    st.markdown(
        """
TenderEval AI automates the evaluation of equipment tender submissions using the Anthropic Claude API.

**Workflow:**
1. Enter evaluation details and bidder names
2. Upload the tender document — AI extracts and customises the criteria
3. Upload each bidder's proposal — AI populates SWOT scores
4. Review and override AI scores as needed
5. Enter TCO financial inputs
6. View the ranked results dashboard
7. Export Excel evaluation matrix + PowerPoint ranking deck
        """
    )

# ===========================================================================
# PAGE: 📋 Evaluation Info
# ===========================================================================
elif page == "📋 Evaluation Info":
    st.title("📋 Evaluation Information")

    col1, col2 = st.columns(2)
    with col1:
        eval_name = st.text_input("Evaluation Name", value=ev().get("eval_name", ""),
                                  placeholder="e.g. PV-2024 Ultra-Class Truck Eval")
        equipment_type = st.selectbox(
            "Equipment Type",
            ["Haul Truck", "Hydraulic Excavator", "Dozer", "Drill", "Motor Grader",
             "Wheel Loader", "Water Cart", "Auxiliary / Plant", "Other"],
            index=max(0, ["Haul Truck", "Hydraulic Excavator", "Dozer", "Drill",
                          "Motor Grader", "Wheel Loader", "Water Cart",
                          "Auxiliary / Plant", "Other"].index(ev().get("equipment_type", "Haul Truck"))
                      if ev().get("equipment_type") in ["Haul Truck", "Hydraulic Excavator",
                                                        "Dozer", "Drill", "Motor Grader",
                                                        "Wheel Loader", "Water Cart",
                                                        "Auxiliary / Plant", "Other"] else 0),
        )
        if equipment_type == "Other":
            equipment_type = st.text_input("Specify equipment type:", value="")

    with col2:
        tender_number = st.text_input("Tender / RFQ Number", value=ev().get("tender_number", ""),
                                      placeholder="e.g. PV-2024-0042")
        bidder_input = st.text_area(
            "Bidder Names (one per line)",
            value="\n".join(ev().get("bidders", [])),
            placeholder="Caterpillar\nKomatsu\nLiebherr",
            height=120,
        )

    if st.button("💾 Save Evaluation Info"):
        bidders = [b.strip() for b in bidder_input.strip().splitlines() if b.strip()]
        if not eval_name:
            st.error("Please enter an evaluation name.")
        elif not bidders:
            st.error("Please enter at least one bidder name.")
        else:
            ev()["eval_name"] = eval_name
            ev()["equipment_type"] = equipment_type
            ev()["tender_number"] = tender_number
            ev()["bidders"] = bidders
            # Initialise score/tco dicts for any new bidders
            for b in bidders:
                if b not in ev()["scores"]:
                    ev()["scores"][b] = {}
                if b not in ev()["tco"]:
                    ev()["tco"][b] = {}
                if b not in ev()["tco_results"]:
                    ev()["tco_results"][b] = {}
            fname = save_progress()
            ev()["last_saved"] = fname
            st.success(f"Saved: {eval_name} | {equipment_type} | {len(bidders)} bidder(s) | Progress saved.")

# ===========================================================================
# PAGE: 📄 Tender Document
# ===========================================================================
elif page == "📄 Tender Document":
    st.title("📄 Tender Document")
    st.markdown(
        "Upload the tender / RFQ document. Claude will read it and customise the evaluation "
        "criteria to match the specific requirements."
    )

    if not ev().get("api_key"):
        st.warning("⚠️ Please set your API key on the Setup page first.")
    if not ev().get("eval_name"):
        st.warning("⚠️ Please fill in Evaluation Info first.")

    uploaded_files = st.file_uploader(
        "Upload Tender Document(s) (PDF, DOCX, XLSX, TXT) — select multiple files if needed",
        type=["pdf", "docx", "xlsx", "xls", "txt"],
        accept_multiple_files=True,
    )

    if uploaded_files and ev().get("api_key") and ev().get("eval_name"):
        for uf in uploaded_files:
            st.info(f"📎 {uf.name} ({uf.size / 1024:.0f} KB)")

        if st.button("🤖 Extract & Customise Criteria with AI"):
            from utils.ai_extractor import extract_text, extract_criteria_from_tender

            combined_text = ""
            # Distribute the 60 k-char Claude budget evenly across all files
            # so every document contributes proportionally, not just the first.
            per_file_limit = 60_000 // len(uploaded_files)
            with st.spinner("Extracting document text…"):
                for uf in uploaded_files:
                    part = extract_text(uf.read(), uf.name)
                    if part and not part.startswith("["):
                        combined_text += f"\n\n--- {uf.name} ---\n\n{part[:per_file_limit]}"
                    else:
                        st.warning(f"⚠️ Could not extract text from {uf.name}: {part}")

            if not combined_text.strip():
                st.error("Could not extract text from any uploaded file.")
            else:
                ev()["tender_doc_summary"] = combined_text[:2000]
                with st.spinner("Claude is customising the criteria for this tender…"):
                    custom_criteria = extract_criteria_from_tender(
                        api_key=ev()["api_key"],
                        doc_text=combined_text,
                        equipment_type=ev().get("equipment_type", ""),
                        eval_name=ev().get("eval_name", ""),
                        default_criteria=DEFAULT_CRITERIA,
                    )
                ev()["criteria"] = custom_criteria
                fname = save_progress()
                ev()["last_saved"] = fname
                st.success(
                    f"✅ Criteria customised from {len(uploaded_files)} file(s)! "
                    f"Part 1: {len(custom_criteria.get('part1', []))} | "
                    f"Part 2 sections: {len(custom_criteria.get('part2', []))} | "
                    f"Part 3 sections: {len(custom_criteria.get('part3', []))} | "
                    f"Progress saved."
                )

    # Option to skip / use defaults
    st.divider()
    with st.expander("Skip tender upload — use default criteria"):
        if st.button("Load Default Criteria"):
            import copy
            ev()["criteria"] = copy.deepcopy(DEFAULT_CRITERIA)
            st.success("Default criteria loaded. You can edit them on the Review Criteria page.")

    # Show excerpt
    if ev().get("tender_doc_summary"):
        with st.expander("Tender document excerpt"):
            st.text(ev()["tender_doc_summary"])

# ===========================================================================
# PAGE: ✅ Review Criteria
# ===========================================================================
elif page == "✅ Review Criteria":
    st.title("✅ Review & Edit Criteria")

    if not ev().get("criteria"):
        st.warning("No criteria loaded yet. Upload a tender document or load defaults first.")
        st.stop()

    criteria = ev()["criteria"]

    tab1, tab2, tab3 = st.tabs(["Part 1 — Compliance", "Part 2 — Technical", "Part 3 — Commercial"])

    with tab1:
        st.markdown("### Part 1 — Proposal Compliance (Pass/Fail Gate)")
        st.markdown("Score: `1` = Complies | `0.5` = Partial | `0` = Does not comply. Gate threshold > 0.5")
        for i, c in enumerate(criteria.get("part1", [])):
            with st.expander(f"{c['id']} — {c['name']}", expanded=False):
                c["name"] = st.text_input("Name", value=c["name"], key=f"p1_name_{i}")
                c["description"] = st.text_area("Description", value=c.get("description", ""),
                                                 key=f"p1_desc_{i}", height=80)
                c["weight"] = st.slider("Weight", 0.0, 0.3, float(c.get("weight", 0.1)),
                                        step=0.01, key=f"p1_w_{i}")
                c["tender_reference"] = st.text_input(
                    "Tender Reference", value=c.get("tender_reference", ""),
                    key=f"p1_ref_{i}")

    with tab2:
        st.markdown("### Part 2 — Qualitative Technical (SWOT)")
        for sec in criteria.get("part2", []):
            with st.expander(f"§{sec['section_id']} — {sec['section_name']}", expanded=False):
                sec["weight"] = st.slider(
                    "Section weight", 0.1, 3.0, float(sec.get("weight", 1.0)),
                    step=0.1, key=f"p2_sec_w_{sec['section_id']}")
                for j, sub in enumerate(sec.get("sub_criteria", [])):
                    st.markdown(f"**{sub['id']}**")
                    sub["name"] = st.text_input("Name", value=sub["name"],
                                                key=f"p2_sub_n_{sub['id']}")
                    sub["description"] = st.text_area(
                        "Description", value=sub.get("description", ""),
                        key=f"p2_sub_d_{sub['id']}", height=60)

    with tab3:
        st.markdown("### Part 3 — Qualitative Commercial (SWOT)")
        for sec in criteria.get("part3", []):
            with st.expander(f"§{sec['section_id']} — {sec['section_name']}", expanded=False):
                sec["weight"] = st.slider(
                    "Section weight", 0.1, 3.0, float(sec.get("weight", 1.0)),
                    step=0.1, key=f"p3_sec_w_{sec['section_id']}")
                for sub in sec.get("sub_criteria", []):
                    st.markdown(f"**{sub['id']}**")
                    sub["name"] = st.text_input("Name", value=sub["name"],
                                                key=f"p3_sub_n_{sub['id']}")
                    sub["description"] = st.text_area(
                        "Description", value=sub.get("description", ""),
                        key=f"p3_sub_d_{sub['id']}", height=60)

    if st.button("💾 Save Criteria Changes"):
        st.success("Criteria saved.")

# ===========================================================================
# PAGE: 👥 Bidder Documents
# ===========================================================================
elif page == "👥 Bidder Documents":
    st.title("👥 Bidder Documents")
    st.markdown(
        "Upload each bidder's proposal document. Claude will read it and extract SWOT scores "
        "for all evaluation criteria."
    )

    if not ev().get("api_key"):
        st.warning("⚠️ API key required — go to Setup.")
    if not ev().get("bidders"):
        st.warning("⚠️ Add bidders on the Evaluation Info page first.")
    if not ev().get("criteria"):
        st.warning("⚠️ Load criteria first (Tender Document or Review Criteria page).")

    bidders = ev().get("bidders", [])

    for bidder in bidders:
        with st.expander(f"📄 {bidder}", expanded=True):
            col1, col2 = st.columns([2, 1])
            with col1:
                uploaded_list = st.file_uploader(
                    f"Upload {bidder} proposal (select multiple files if needed)",
                    type=["pdf", "docx", "xlsx", "xls", "txt"],
                    key=f"upload_{bidder}",
                    accept_multiple_files=True,
                )
            with col2:
                existing_model = ev()["scores"].get(bidder, {}).get("model_identified", "")
                if existing_model:
                    st.success(f"✅ Scored: {existing_model}")
                else:
                    st.info("Not yet processed")

            if uploaded_list and ev().get("api_key") and ev().get("criteria"):
                if st.button(f"🤖 Extract scores for {bidder}", key=f"extract_{bidder}"):
                    from utils.ai_extractor import extract_text, extract_scores_from_bidder_doc

                    combined_text = ""
                    # Distribute the 70 k-char Claude budget evenly across all files
                    # so every document contributes proportionally, not just the first.
                    per_file_limit = 70_000 // len(uploaded_list)
                    with st.spinner(f"Extracting text from {bidder} proposal…"):
                        for uf in uploaded_list:
                            part = extract_text(uf.read(), uf.name)
                            if part and not part.startswith("["):
                                combined_text += f"\n\n--- {uf.name} ---\n\n{part[:per_file_limit]}"
                            else:
                                st.warning(f"⚠️ Could not extract text from {uf.name}")

                    if not combined_text.strip():
                        st.error("Extraction failed: no text could be read from the uploaded file(s).")
                    else:
                        with st.spinner(f"Claude is scoring {bidder}…"):
                            result = extract_scores_from_bidder_doc(
                                api_key=ev()["api_key"],
                                doc_text=combined_text,
                                bidder_name=bidder,
                                equipment_type=ev().get("equipment_type", ""),
                                eval_name=ev().get("eval_name", ""),
                                criteria=ev()["criteria"],
                            )
                        ev()["scores"][bidder] = result
                        fname = save_progress()
                        ev()["last_saved"] = fname
                        st.success(
                            f"✅ {bidder} scored from {len(uploaded_list)} file(s)! "
                            f"Model: {result.get('model_identified', 'Unknown')} | "
                            f"TQs: {len(result.get('tq_list', []))} | "
                            f"Progress saved."
                        )
                        if result.get("tq_list"):
                            st.markdown("**Technical Queries (TQs) raised by AI:**")
                            for tq in result["tq_list"]:
                                st.markdown(f"- {tq}")

# ===========================================================================
# PAGE: 🔍 Score Review
# ===========================================================================
elif page == "🔍 Score Review":
    st.title("🔍 Score Review & Override")

    if not ev().get("bidders"):
        st.warning("No bidders defined.")
        st.stop()
    if not ev().get("criteria"):
        st.warning("No criteria loaded.")
        st.stop()

    criteria = ev()["criteria"]
    bidder_tabs = st.tabs(ev()["bidders"])

    for tab_obj, bidder in zip(bidder_tabs, ev()["bidders"]):
        with tab_obj:
            b_scores = ev()["scores"].get(bidder, {})
            model = b_scores.get("model_identified", "Unknown")
            st.markdown(f"**Model identified:** {model}")

            inner_tabs = st.tabs(["Part 1 — Compliance", "Part 2 — Technical", "Part 3 — Commercial",
                                  "Summary"])

            # ---- Part 1 review ----
            with inner_tabs[0]:
                st.markdown("Score: `1` = PASS | `0.5` = PARTIAL | `0` = FAIL")
                p1_scores = b_scores.get("part1_scores", {})
                for c in criteria.get("part1", []):
                    entry = p1_scores.get(c["id"], {"score": 0.5, "rationale": "", "tq_needed": False})
                    col1, col2, col3 = st.columns([2, 1, 3])
                    with col1:
                        st.markdown(f"**{c['id']}** {c['name']}")
                    with col2:
                        new_score = st.selectbox(
                            "Score", [1.0, 0.5, 0.0],
                            index=[1.0, 0.5, 0.0].index(float(entry.get("score", 0.5))),
                            key=f"p1_score_{bidder}_{c['id']}",
                            format_func=lambda x: {1.0: "1 — PASS", 0.5: "0.5 — PARTIAL",
                                                    0.0: "0 — FAIL"}[x],
                        )
                        entry["score"] = new_score
                    with col3:
                        new_rat = st.text_input("Rationale", value=entry.get("rationale", ""),
                                                key=f"p1_rat_{bidder}_{c['id']}")
                        entry["rationale"] = new_rat
                    p1_scores[c["id"]] = entry
                b_scores["part1_scores"] = p1_scores

            # ---- Part 2 review ----
            with inner_tabs[1]:
                p2_scores = b_scores.get("part2_scores", {})
                SWOT_OPTIONS = ["S", "O", "N", "T", "W"]
                SWOT_LABELS = {
                    "S": "S — Strength (+1)",
                    "O": "O — Opportunity (+0.5)",
                    "N": "N — Neutral (0)",
                    "T": "T — Threat (−0.5)",
                    "W": "W — Weakness (−1)",
                }
                for sec in criteria.get("part2", []):
                    st.markdown(f"#### §{sec['section_id']} — {sec['section_name']} (weight {sec.get('weight',1):.1f}×)")
                    for sub in sec.get("sub_criteria", []):
                        entry = p2_scores.get(sub["id"], {"rating": "N", "rationale": "", "tq_needed": False})
                        col1, col2, col3 = st.columns([2, 1, 3])
                        with col1:
                            st.markdown(f"**{sub['id']}** {sub['name']}")
                        with col2:
                            current_rating = entry.get("rating", "N").upper()
                            if current_rating not in SWOT_OPTIONS:
                                current_rating = "N"
                            new_rating = st.selectbox(
                                "Rating",
                                SWOT_OPTIONS,
                                index=SWOT_OPTIONS.index(current_rating),
                                key=f"p2_r_{bidder}_{sub['id']}",
                                format_func=lambda x: SWOT_LABELS[x],
                            )
                            entry["rating"] = new_rating
                        with col3:
                            new_rat = st.text_input("Rationale", value=entry.get("rationale", ""),
                                                    key=f"p2_rat_{bidder}_{sub['id']}")
                            entry["rationale"] = new_rat
                        p2_scores[sub["id"]] = entry
                b_scores["part2_scores"] = p2_scores

            # ---- Part 3 review ----
            with inner_tabs[2]:
                p3_scores = b_scores.get("part3_scores", {})
                for sec in criteria.get("part3", []):
                    st.markdown(f"#### §{sec['section_id']} — {sec['section_name']} (weight {sec.get('weight',1):.1f}×)")
                    for sub in sec.get("sub_criteria", []):
                        entry = p3_scores.get(sub["id"], {"rating": "N", "rationale": "", "tq_needed": False})
                        col1, col2, col3 = st.columns([2, 1, 3])
                        with col1:
                            st.markdown(f"**{sub['id']}** {sub['name']}")
                        with col2:
                            current_rating = entry.get("rating", "N").upper()
                            if current_rating not in SWOT_OPTIONS:
                                current_rating = "N"
                            new_rating = st.selectbox(
                                "Rating",
                                SWOT_OPTIONS,
                                index=SWOT_OPTIONS.index(current_rating),
                                key=f"p3_r_{bidder}_{sub['id']}",
                                format_func=lambda x: SWOT_LABELS[x],
                            )
                            entry["rating"] = new_rating
                        with col3:
                            new_rat = st.text_input("Rationale", value=entry.get("rationale", ""),
                                                    key=f"p3_rat_{bidder}_{sub['id']}")
                            entry["rationale"] = new_rat
                        p3_scores[sub["id"]] = entry
                b_scores["part3_scores"] = p3_scores

            # ---- Summary tab ----
            with inner_tabs[3]:
                from utils.tco import calculate_part1_score, calculate_part_score, part1_pass

                p1_sc = calculate_part1_score(b_scores.get("part1_scores", {}),
                                              criteria.get("part1", []))
                p2_sc = calculate_part_score(b_scores.get("part2_scores", {}),
                                             criteria.get("part2", []))
                p3_sc = calculate_part_score(b_scores.get("part3_scores", {}),
                                             criteria.get("part3", []))

                mc1, mc2, mc3, mc4 = st.columns(4)
                mc1.metric("Part 1 Score", f"{p1_sc:.1%}")
                mc2.metric("Part 1 Gate", "✅ PASS" if part1_pass(p1_sc) else "❌ FAIL")
                mc3.metric("Tech SWOT (P2)", f"{p2_sc:+.2f}")
                mc4.metric("Comm SWOT (P3)", f"{p3_sc:+.2f}")

                strengths = b_scores.get("key_strengths", [])
                risks = b_scores.get("key_risks", [])
                tq_list = b_scores.get("tq_list", [])

                if strengths or risks or tq_list:
                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        st.markdown("**Key Strengths**")
                        for s in strengths:
                            st.markdown(f"✅ {s}")
                    with col_b:
                        st.markdown("**Key Risks**")
                        for r in risks:
                            st.markdown(f"⚠️ {r}")
                    with col_c:
                        st.markdown("**TQ List**")
                        for tq in tq_list:
                            st.markdown(f"❓ {tq}")

            ev()["scores"][bidder] = b_scores

# ===========================================================================
# PAGE: 💰 TCO Analysis
# ===========================================================================
elif page == "💰 TCO Analysis":
    st.title("💰 TCO Analysis")
    st.markdown(
        "Enter financial inputs per bidder. NPV is calculated at the default 8% discount rate."
    )

    if not ev().get("bidders"):
        st.warning("No bidders defined.")
        st.stop()

    discount_rate = st.slider("Discount Rate", 0.04, 0.15, 0.08, 0.01,
                               format="%.0f%%",
                               help="Used for NPV calculation across all bidders")

    from utils.tco import calculate_tco

    bidder_tabs = st.tabs(ev()["bidders"])
    for tab_obj, bidder in zip(bidder_tabs, ev()["bidders"]):
        with tab_obj:
            tco_in = ev()["tco"].get(bidder, {})

            st.markdown("#### CAPEX")
            c1, c2, c3, c4 = st.columns(4)
            rtw = c1.number_input("RTW Cost (AUD)", value=float(tco_in.get("rtw_cost", 0)),
                                   min_value=0.0, step=10000.0, format="%.0f",
                                   key=f"rtw_{bidder}")
            cm_capex = c2.number_input("Change Mgmt CAPEX (AUD)",
                                        value=float(tco_in.get("change_mgmt_capex", 0)),
                                        min_value=0.0, step=1000.0, format="%.0f",
                                        key=f"cmcapex_{bidder}")
            training = c3.number_input("Training (AUD)", value=float(tco_in.get("training", 0)),
                                        min_value=0.0, step=1000.0, format="%.0f",
                                        key=f"train_{bidder}")
            seed = c4.number_input("Seed Components (AUD)", value=float(tco_in.get("seed_components", 0)),
                                    min_value=0.0, step=1000.0, format="%.0f",
                                    key=f"seed_{bidder}")

            total_life_hours = st.number_input(
                "Total Life Hours (hrs)", value=float(tco_in.get("total_life_hours", 60000)),
                min_value=1000.0, step=1000.0, format="%.0f", key=f"lh_{bidder}"
            )

            st.markdown("#### OPEX by Year")
            existing_opex = tco_in.get("opex_years", [{"operating": 0, "maintenance": 0, "indirect": 0}])
            n_years = st.number_input("Number of years", min_value=1, max_value=20,
                                       value=max(len(existing_opex), 1),
                                       key=f"nyrs_{bidder}")
            n_years = int(n_years)

            # Extend or trim
            while len(existing_opex) < n_years:
                existing_opex.append({"operating": 0, "maintenance": 0, "indirect": 0})
            existing_opex = existing_opex[:n_years]

            opex_years_updated = []
            for yr in range(n_years):
                yr_data = existing_opex[yr]
                st.markdown(f"**Year {yr + 1}**")
                oc1, oc2, oc3 = st.columns(3)
                op = oc1.number_input("Operating (AUD)", value=float(yr_data.get("operating", 0)),
                                       min_value=0.0, step=10000.0, format="%.0f",
                                       key=f"op_{bidder}_{yr}")
                mnt = oc2.number_input("Maintenance (AUD)", value=float(yr_data.get("maintenance", 0)),
                                        min_value=0.0, step=10000.0, format="%.0f",
                                        key=f"mnt_{bidder}_{yr}")
                ind = oc3.number_input("Indirect (AUD)", value=float(yr_data.get("indirect", 0)),
                                        min_value=0.0, step=5000.0, format="%.0f",
                                        key=f"ind_{bidder}_{yr}")
                opex_years_updated.append({"operating": op, "maintenance": mnt, "indirect": ind})

            tco_in_updated = {
                "rtw_cost": rtw,
                "change_mgmt_capex": cm_capex,
                "training": training,
                "seed_components": seed,
                "total_life_hours": total_life_hours,
                "opex_years": opex_years_updated,
            }
            ev()["tco"][bidder] = tco_in_updated

            if st.button(f"Calculate TCO for {bidder}", key=f"calctco_{bidder}"):
                result = calculate_tco(tco_in_updated, discount_rate=discount_rate)
                ev()["tco_results"][bidder] = result
                st.success(
                    f"Total TCO: ${result['total_tco']:,.0f}  |  "
                    f"NPV: ${result['npv']:,.0f}  |  "
                    f"Cost/hr: ${result['cost_per_hour']:,.2f}"
                )

    st.divider()
    if st.button("🔄 Calculate ALL Bidder TCOs"):
        from utils.tco import calculate_tco
        for bidder in ev()["bidders"]:
            tco_data = ev()["tco"].get(bidder, {})
            if tco_data:
                ev()["tco_results"][bidder] = calculate_tco(tco_data, discount_rate=discount_rate)
        st.success("All TCO calculations updated.")

# ===========================================================================
# PAGE: 🏆 Results & Ranking
# ===========================================================================
elif page == "🏆 Results & Ranking":
    st.title("🏆 Results & Ranking")

    if not ev().get("bidders"):
        st.warning("No bidders defined.")
        st.stop()
    if not ev().get("criteria"):
        st.warning("No criteria loaded.")
        st.stop()

    from utils.tco import (
        build_scorecard,
        calculate_part1_score,
        calculate_part_score,
        calculate_section_score,
        part1_pass,
    )

    criteria = ev()["criteria"]
    bidders = ev()["bidders"]
    scores = ev()["scores"]
    tco_results = ev()["tco_results"]

    # Build scorecards
    scorecards = []
    for b in bidders:
        sc = build_scorecard(b, scores.get(b, {}), criteria, tco_results.get(b, {}))
        scorecards.append(sc)

    scorecards.sort(key=lambda x: (
        not x["part1_pass"],
        -x["combined_qualitative"],
        x.get("tco", float("inf")),
    ))

    # --- Top-level metrics ---
    st.markdown("### Overall Ranking")
    cols = st.columns(len(bidders))
    for rank_idx, (col, sc) in enumerate(zip(cols, scorecards), 1):
        with col:
            medal = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"][rank_idx - 1] if rank_idx <= 5 else str(rank_idx)
            st.markdown(f"### {medal} {sc['bidder']}")
            model = scores.get(sc["bidder"], {}).get("model_identified", "")
            if model:
                st.caption(model)
            st.metric("Part 1", f"{sc['part1_score']:.1%}",
                       delta="PASS" if sc["part1_pass"] else "FAIL",
                       delta_color="normal" if sc["part1_pass"] else "inverse")
            st.metric("Tech SWOT", f"{sc['part2_score']:+.2f}")
            st.metric("Comm SWOT", f"{sc['part3_score']:+.2f}")
            st.metric("Combined SWOT", f"{sc['combined_qualitative']:+.2f}")
            tco_v = sc.get("tco", 0)
            st.metric("Total TCO", f"${tco_v:,.0f}" if tco_v else "—")
            st.metric("$/hr", f"${sc.get('cost_per_hour', 0):,.2f}" if sc.get("cost_per_hour") else "—")

    st.divider()

    # --- Section-by-section comparison ---
    st.markdown("### Part 2 — Technical SWOT by Section")
    import pandas as pd

    p2_rows = []
    for sec in criteria.get("part2", []):
        row = {"Section": f"§{sec['section_id']} {sec['section_name']}",
               "Weight": f"{sec.get('weight', 1):.1f}×"}
        for b in bidders:
            raw = calculate_section_score(
                sec["section_id"],
                scores.get(b, {}).get("part2_scores", {}),
                criteria.get("part2", []),
            )
            row[b] = f"{raw * sec.get('weight', 1):+.2f}"
        p2_rows.append(row)
    st.dataframe(pd.DataFrame(p2_rows), use_container_width=True, hide_index=True)

    st.markdown("### Part 3 — Commercial SWOT by Section")
    p3_rows = []
    for sec in criteria.get("part3", []):
        row = {"Section": f"§{sec['section_id']} {sec['section_name']}",
               "Weight": f"{sec.get('weight', 1):.1f}×"}
        for b in bidders:
            raw = calculate_section_score(
                sec["section_id"],
                scores.get(b, {}).get("part3_scores", {}),
                criteria.get("part3", []),
            )
            row[b] = f"{raw * sec.get('weight', 1):+.2f}"
        p3_rows.append(row)
    st.dataframe(pd.DataFrame(p3_rows), use_container_width=True, hide_index=True)

    st.markdown("### TCO Comparison")
    tco_summary_rows = []
    for metric_label, key in [
        ("Total CAPEX", "total_capex"),
        ("Total OPEX", "total_opex"),
        ("Total TCO", "total_tco"),
        ("NPV @ 8%", "npv"),
        ("Cost per Hour", "cost_per_hour"),
    ]:
        row = {"Metric": metric_label}
        for b in bidders:
            val = tco_results.get(b, {}).get(key, 0)
            row[b] = f"${val:,.0f}" if "Hour" not in metric_label else f"${val:,.2f}"
        tco_summary_rows.append(row)
    st.dataframe(pd.DataFrame(tco_summary_rows), use_container_width=True, hide_index=True)

# ===========================================================================
# PAGE: 📤 Export
# ===========================================================================
elif page == "📤 Export":
    st.title("📤 Export")
    st.markdown("Generate and download the evaluation outputs.")

    if not ev().get("bidders") or not ev().get("criteria"):
        st.warning("Complete evaluation setup before exporting.")
        st.stop()

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 📊 Excel Evaluation Matrix")
        st.markdown(
            "Includes: Comparison Summary | Per-bidder Assessment (Rev0.1 layout) | TCO Analysis"
        )
        if st.button("🔨 Generate Excel"):
            with st.spinner("Building Excel workbook…"):
                from utils.excel_exporter import generate_assessment_matrix
                xlsx_bytes = generate_assessment_matrix(ev())
            fname = f"{ev().get('eval_name', 'TenderEval')}_Assessment_Matrix.xlsx"
            fname = fname.replace(" ", "_")
            st.download_button(
                label="⬇️ Download Excel",
                data=xlsx_bytes,
                file_name=fname,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

    with col2:
        st.markdown("### 📑 PowerPoint Ranking Deck")
        st.markdown(
            "Includes: Cover | Overview | Part 1 Compliance | Technical SWOT per section | "
            "Commercial SWOT | TCO | Overall Ranking | Recommendation"
        )
        if st.button("🔨 Generate PowerPoint"):
            with st.spinner("Building PowerPoint deck…"):
                from utils.pptx_generator import generate_ranking_deck
                pptx_bytes = generate_ranking_deck(ev())
            fname = f"{ev().get('eval_name', 'TenderEval')}_Ranking_Deck.pptx"
            fname = fname.replace(" ", "_")
            st.download_button(
                label="⬇️ Download PowerPoint",
                data=pptx_bytes,
                file_name=fname,
                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            )

    # -----------------------------------------------------------------------
    # Evaluator Collaboration Sheet
    # -----------------------------------------------------------------------
    st.divider()
    st.markdown("### 👥 Evaluator Collaboration Sheet")
    st.markdown(
        "Export a fillable Excel workbook — one sheet per bidder. "
        "Send it to your evaluators to score. When complete, re-upload it here to import their scores."
    )

    colA, colB = st.columns(2)

    with colA:
        st.markdown("**Step 1 — Export**")
        if st.button("🔨 Generate Evaluator Sheet"):
            with st.spinner("Building evaluator workbook…"):
                from utils.eval_sheet import generate_evaluator_sheet
                eval_xlsx = generate_evaluator_sheet(ev())
            fname_eval = f"{ev().get('eval_name', 'TenderEval')}_Evaluator_Sheet.xlsx".replace(" ", "_")
            st.download_button(
                label="⬇️ Download Evaluator Sheet",
                data=eval_xlsx,
                file_name=fname_eval,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            st.caption("Share this file with evaluators. Each bidder has its own sheet.")

    with colB:
        st.markdown("**Step 2 — Import completed sheet**")
        uploaded_eval_sheet = st.file_uploader(
            "Upload completed Evaluator Sheet (.xlsx)",
            type=["xlsx"],
            key="eval_sheet_upload",
        )
        if uploaded_eval_sheet:
            from utils.eval_sheet import list_sheet_bidders, parse_evaluator_sheet

            sheet_bytes = uploaded_eval_sheet.read()
            found_sheets = list_sheet_bidders(sheet_bytes)
            st.caption(f"Sheets found in file: {', '.join(found_sheets)}")

            import_bidders = [b for b in ev().get("bidders", []) if b in found_sheets or
                              any(b.lower() in s.lower() or s.lower() in b.lower() for s in found_sheets)]

            if not import_bidders:
                st.warning("No matching bidder sheets found. Check that sheet names match your bidder names.")
            else:
                selected = st.multiselect(
                    "Select bidders to import scores for",
                    options=import_bidders,
                    default=import_bidders,
                )
                if st.button("📥 Import Selected Scores") and selected:
                    imported = []
                    for bidder in selected:
                        parsed = parse_evaluator_sheet(sheet_bytes, bidder, ev()["criteria"])
                        if parsed:
                            existing = ev()["scores"].get(bidder, {})
                            # Merge: imported scores overlay existing, preserve AI metadata
                            for part_key in ("part1_scores", "part2_scores", "part3_scores"):
                                if parsed.get(part_key):
                                    existing.setdefault(part_key, {}).update(parsed[part_key])
                            ev()["scores"][bidder] = existing
                            imported.append(bidder)
                    if imported:
                        fname_saved = save_progress()
                        ev()["last_saved"] = fname_saved
                        st.success(
                            f"✅ Scores imported for: {', '.join(imported)} | Progress saved."
                        )
                    else:
                        st.error("No scores could be parsed. Check the file format.")

    st.divider()
    st.markdown("### 💾 Save / Load Evaluation Session (JSON)")
    export_col, import_col = st.columns(2)

    with export_col:
        if st.button("Export Session JSON"):
            import json as _json
            session_json = _json.dumps(ev(), indent=2, default=str)
            st.download_button(
                "⬇️ Download Session JSON",
                data=session_json,
                file_name=f"{ev().get('eval_name', 'session')}.json",
                mime="application/json",
            )

    with import_col:
        uploaded_session = st.file_uploader("Load Session JSON", type=["json"],
                                             key="session_upload")
        if uploaded_session:
            import json as _json
            try:
                loaded = _json.loads(uploaded_session.read())
                if st.button("Apply Loaded Session"):
                    st.session_state["eval"] = loaded
                    st.success("Session loaded. Navigate to any page to review.")
            except Exception as e:
                st.error(f"Could not parse JSON: {e}")
