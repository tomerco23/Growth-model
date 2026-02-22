"""
tasks.py – CrewAI task definitions for the Hospital Growth Model project.

Each function returns a crewai.Task bound to the appropriate agent.

Initial workflow tasks (used in crew_main.py):
  1. generate_presentation_task  – Presentation Agent reads all source files
                                   and writes PROJECT_PRESENTATION.md.
  2. qa_review_task              – QA Agent cross-checks the presentation
                                   against the real code and writes QA_REVIEW.md.

Additional tasks are defined here for future crew workflows:
  3. ui_improvement_task         – UI Agent reviews views.py / app.py for bugs
                                   and proposes concrete improvements.
  4. db_migration_plan_task      – DB Agent designs the Excel → database schema.
  5. backend_audit_task          – Backend Agent audits calculations.py for
                                   numerical accuracy and code quality.
"""

from pathlib import Path

from crewai import Task

# Output files land in the same directory as the source code (Growth Model/)
_HERE: Path = Path(__file__).parent
_PRESENTATION_MD = str(_HERE / "PROJECT_PRESENTATION.md")
_QA_REVIEW_MD    = str(_HERE / "QA_REVIEW.md")
_DB_PLAN_MD      = str(_HERE / "DB_MIGRATION_PLAN.md")
_UI_NOTES_MD     = str(_HERE / "UI_IMPROVEMENT_NOTES.md")
_BACKEND_AUDIT_MD = str(_HERE / "BACKEND_AUDIT.md")


# ---------------------------------------------------------------------------
# Task 1 – Generate PROJECT_PRESENTATION.md
# ---------------------------------------------------------------------------

def create_presentation_task(agent) -> Task:
    """Assign the Presentation Agent to analyse the full codebase and write
    PROJECT_PRESENTATION.md.

    The task description is highly specific so the agent knows the exact
    formulas, module names, and Hebrew terms it must document.
    """
    return Task(
        description=(
            "You are the Technical Communicator. Your job is to produce a "
            "comprehensive PROJECT_PRESENTATION.md for the Hospital Growth Model "
            "Streamlit application.\n\n"

            "STEP 1 – READ ALL SOURCE FILES before writing a single word:\n"
            "  • app.py\n"
            "  • views.py\n"
            "  • data_loading.py\n"
            "  • calculations.py\n"
            "  • report.py\n"
            "  • constants.py\n"
            "  • utils.py\n\n"

            "STEP 2 – Write PROJECT_PRESENTATION.md covering ALL sections below. "
            "Use exact function names, parameter names, and Hebrew field names "
            "from the code. Do not paraphrase formulas — quote them precisely.\n\n"

            "## Required Sections\n\n"

            "### 1. Executive Summary\n"
            "What the application does in 2–3 plain-language paragraphs for "
            "hospital executives who do not code.\n\n"

            "### 2. Module Architecture\n"
            "A table with columns: Module | Owner Agent | One-line description. "
            "Then a prose description of the data flow from sidebar upload → "
            "load_growth_data() → session_state.growth_items → "
            "calculate_detailed_rows() → show_report_view() → Excel download.\n\n"

            "### 3. Data Inputs\n"
            "Describe both input file types in detail:\n"
            "  a) Internal HR Excel file – explain the three sheets "
            "(DB_HR_Staffing, DB_HR_Costs, DB_Service_count), the Hebrew column "
            "names that get renamed via _rename_hr_columns(), the GROUP_COLS "
            "list, and how FTE and Monthly_Cost/Annual_Cost are derived.\n"
            "  b) External MOH price-list files – explain the parse_moh_file() "
            "logic: encoding detection (UTF-8 / windows-1255), dynamic header "
            "search for 'קוד', 'שירות', 'תעריף', column selection for Code, "
            "Name, and Tariff, and the normalize_code() + clean_currency() "
            "normalisation steps.\n\n"

            "### 4. Economic Model Deep-Dive\n"
            "Explain every calculation in calculations.py with the exact "
            "formula notation used in the code:\n"
            "  a) Revenue items:\n"
            "     • Quantity adjustment: qty_net = qty × (1 – no_show_rate) "
            "× [0.93 if Is_New else 1.0]\n"
            "     • Per-unit net: u_net = u_gross × (1 – HMO_DISCOUNT) "
            "× (1 – VOL_DISCOUNT) × (1 – APPEALS_PROV)\n"
            "     • Per-unit CAP: u_cap = u_gross × CAP_RATE_FACTOR\n"
            "     • Overhead: ovh_cost = tot_net × OVERHEAD_RATE\n"
            "     • Net to pocket: net_pocket = tot_net – ovh_cost\n"
            "     • Private services: skip the discount chain (u_net = u_gross)\n"
            "     • 4-year compound growth: val_y2 = val_base × (1+g_y2), "
            "val_y3 = val_y2 × (1+g_y3), val_y4 = val_y3 × (1+g_y4)\n"
            "  b) Manpower items (three modes):\n"
            "     • FTE (annual): val = –(qty × Unit_Cost_annual)\n"
            "     • Daily shift: single_cost = base_val × weight × shifts × "
            "(1+overhead) × (1+occ_bonus); val = –(single_cost × num_employees)\n"
            "     • Hourly shift: single_cost = hour_cost × hours_per_shift × "
            "shifts × (1+extra_pct); val = –(single_cost × num_employees)\n"
            "     • Session sub-rows: val = –(sess_qty × 12 × sess_cost)\n"
            "  c) Operation items: val = –(qty × Unit_Cost); one-time items "
            "treated as CAPEX.\n"
            "  d) Investment / CAPEX items: val = –(qty × Unit_Cost); "
            "tracked in total_capex.\n"
            "  e) ROI: roi = total_capex ÷ total_prof_base (years); 0 if "
            "total_prof_base ≤ 0.\n"
            "  f) Scenario logic: optimistic = base × (Pct_Opt / 100); "
            "pessimistic = base × (Pct_Pess / 100).\n\n"

            "### 5. User Workflow\n"
            "Step-by-step guide through the application:\n"
            "  1. Sidebar: enter project name (שם הפרויקט); upload internal HR "
            "file (קובץ HR) and optional MOH price-list files (מחירונים).\n"
            "  2. Sidebar: adjust the six global parameters (OVERHEAD_RATE, "
            "HMO_DISCOUNT, VOL_DISCOUNT, APPEALS_PROV, NO_SHOW_RATE, "
            "CAP_RATE_FACTOR).\n"
            "  3. Edit view – CAPEX tab: add one-time investment items.\n"
            "  4. Edit view – OPEX tab – HR sub-tab: add manpower items using "
            "FTE/Daily/Hourly modes with cascading filter (Maarach → Agaf → "
            "Hativa → Machleket Em → Sector → Job Desc).\n"
            "  5. Edit view – OPEX tab – Operations sub-tab: add recurring or "
            "one-time operational costs.\n"
            "  6. Edit view – Revenue tab: add revenue services via the "
            "cascading 5-level hierarchy filter (Maarach → Agaf → Hativa → "
            "Machleket Em → Yahida) and multiselect, or via manual entry.\n"
            "  7. Edit view: review the live editable data table; use the "
            "undo button (↩️) to revert the last change.\n"
            "  8. Click '📄 עבור לתצוגה מקדימה של הדו\"ח' to go to report view.\n"
            "  9. Report view: use the Management Simulator sliders to run "
            "what-if scenarios, review KPI cards, download the Excel report.\n"
            "  10. Save state as JSON; reload from JSON in a future session.\n\n"

            "### 6. Session State Management\n"
            "List every key in SESSION_STATE_DEFAULTS from constants.py, "
            "explain what it stores, and where it is read/written (which "
            "function in which module).\n\n"

            "### 7. Excel Report Structure\n"
            "Describe the two worksheets produced by create_hybrid_report_sheet() "
            "in report.py:\n"
            "  a) 'דוח כלכלי' – summary table (revenue, OPEX, HR, CAPEX, "
            "EBITDA, net profit, ROI, recommendation for both net and CAP "
            "scenarios), revenue detail, manpower detail (FTE and shift modes "
            "in separate sub-tables), operation detail, investment detail.\n"
            "  b) 'מתודולוגיה והנחות' – parameter table and methodology "
            "glossary from generate_methodology().\n\n"

            "### 8. Known Limitations & Recommended Improvements\n"
            "Honest technical assessment covering:\n"
            "  • Dependency on specific Hebrew column names in Excel files.\n"
            "  • No persistent database (all data lost on page refresh unless "
            "saved to JSON).\n"
            "  • Excel-based data loading fragility and the case for SQLite.\n"
            "  • Any other technical debt you identify from the code.\n\n"

            "### 9. Bilingual Glossary\n"
            "Define every Hebrew term used in the UI, code field names, and "
            "Category names. Include: Maarach, Agaf, Hativa, Machleket Em, "
            "Yahida, Sector, FTE, ססיות (sessions), תקורה (overhead), "
            "הנחת קופות (HMO discount), הנחת מחזור (volume discount), "
            "ערעורים (appeals), קאפ (CAP), No-Show, ROI, CAPEX, OPEX, EBITDA, "
            "תרחיש אופטימי/פסימי.\n\n"

            "OUTPUT: Write the complete document as valid GitHub-flavoured "
            "Markdown. Be thorough and precise."
        ),
        expected_output=(
            "A complete, well-structured PROJECT_PRESENTATION.md document "
            "(GitHub-flavoured Markdown) covering all 9 sections listed in the "
            "description, accurately reflecting the actual codebase with exact "
            "function names, formula notation, and parameter names from the code."
        ),
        agent=agent,
        output_file=_PRESENTATION_MD,
    )


# ---------------------------------------------------------------------------
# Task 2 – QA Review of PROJECT_PRESENTATION.md
# ---------------------------------------------------------------------------

def create_qa_review_task(agent, presentation_task: Task) -> Task:
    """Assign the QA Agent to fact-check the presentation against the source code.

    This task uses the output of create_presentation_task() as context so the
    QA agent can see both the generated document and use its file-reading tools
    to verify claims against the actual source files.
    """
    return Task(
        description=(
            "You are the Senior QA Engineer. Your job is to fact-check the "
            "PROJECT_PRESENTATION.md produced by the Presentation Agent and "
            "produce a structured QA_REVIEW.md.\n\n"

            "STEP 1 – Read the presentation document (provided as context).\n\n"

            "STEP 2 – For EVERY factual claim in the document, cross-reference "
            "it against the actual source files using your file-reading tools. "
            "Verify the following check-list in full:\n\n"

            "FORMULA CHECKS (vs calculations.py):\n"
            "  □ Revenue qty_net formula (no_show, Is_New 0.93 factor)\n"
            "  □ Revenue u_net formula (HMO × vol × appeals discount chain)\n"
            "  □ Revenue u_cap formula (gross × CAP_RATE_FACTOR only)\n"
            "  □ Overhead formula (tot_net × OVERHEAD_RATE)\n"
            "  □ net_pocket formula (tot_net – ovh_cost)\n"
            "  □ Private service handling (u_net = u_gross, u_cap = u_gross)\n"
            "  □ ROI formula (total_capex ÷ total_prof_base; 0 when ≤ 0)\n"
            "  □ 4-year growth chain (compound, not additive)\n"
            "  □ Manpower FTE cost sign (negative value = expense)\n"
            "  □ Session sub-row formula (sess_qty × 12 × sess_cost)\n\n"

            "MODULE RESPONSIBILITY CHECKS:\n"
            "  □ constants.py described as config-only\n"
            "  □ utils.py described as pure-function helpers\n"
            "  □ data_loading.py described as I/O only\n"
            "  □ calculations.py described as maths only (no Streamlit)\n"
            "  □ report.py described as Excel output only (no Streamlit)\n"
            "  □ views.py + app.py described as UI only\n\n"

            "DATA-LOADING CHECKS (vs data_loading.py):\n"
            "  □ Internal sheet names: DB_HR_Staffing, DB_HR_Costs, "
            "DB_Service_count\n"
            "  □ GROUP_COLS list: Maarach, Agaf, Hativa, Machleket Em, "
            "Yahida, Sector, Job Desc\n"
            "  □ Encoding options: utf-8 and windows-1255\n"
            "  □ MOH header keywords: 'קוד', 'שירות', 'תעריף'\n"
            "  □ Monthly_Cost = cost_val / emp_val (last available month)\n"
            "  □ Annual_Cost = Monthly_Cost × 12\n\n"

            "SESSION STATE CHECKS (vs constants.py SESSION_STATE_DEFAULTS):\n"
            "  □ All 8 keys listed: growth_items, history, general_comments, "
            "manpower_form_cost, view_mode, latest_df_flat_mapping, "
            "srv_multi_select, def6\n\n"

            "PARAMETER CHECKS (vs app.py sidebar):\n"
            "  □ Six params: OVERHEAD_RATE, HMO_DISCOUNT, VOL_DISCOUNT, "
            "APPEALS_PROV, NO_SHOW_RATE, CAP_RATE_FACTOR\n"
            "  □ Default values match app.py (ovh=29%, hmo=18.5%, vol=1.9%, "
            "app=4%, no_show=0%, cap=37.5%)\n\n"

            "STEP 3 – Write QA_REVIEW.md with three sections:\n\n"
            "  ## ✅ PASS\n"
            "  List every claim that is verified as accurate. Be specific: "
            "quote the claim and reference the source file + line number.\n\n"
            "  ## ❌ FAIL\n"
            "  List every inaccuracy found. For each failure:\n"
            "    - What the document says\n"
            "    - What the code actually says (with file + line reference)\n"
            "    - The correct statement to replace it\n\n"
            "  ## 💡 SUGGESTIONS\n"
            "  List any improvements to clarity, completeness, or structure "
            "that would make the document more useful, even if not technically "
            "wrong.\n\n"

            "STEP 4 – If there are any FAIL items, append a section:\n\n"
            "  ## 📝 Corrected Sections\n"
            "  Re-write ONLY the affected sections of PROJECT_PRESENTATION.md "
            "with the corrections applied. Label each sub-section with the "
            "original section number."
        ),
        expected_output=(
            "A structured QA_REVIEW.md with clearly labelled PASS, FAIL, and "
            "SUGGESTIONS sections, referencing specific source files and line "
            "numbers for every finding. If corrections were needed, the "
            "Corrected Sections appendix contains the fixed markdown."
        ),
        agent=agent,
        context=[presentation_task],
        output_file=_QA_REVIEW_MD,
    )


# ---------------------------------------------------------------------------
# Task 3 – UI Improvement Notes  (future use)
# ---------------------------------------------------------------------------

def create_ui_improvement_task(agent) -> Task:
    """Assign the UI Agent to review views.py and app.py for bugs and improvements.

    Suitable for a dedicated UI-focused crew run (not included in the initial
    workflow but ready to use).
    """
    return Task(
        description=(
            "You are the Streamlit UI Expert. Read views.py and app.py "
            "thoroughly.\n\n"
            "Identify and document:\n"
            "  1. Any session-state bugs (e.g. keys not initialised before use, "
            "mutable defaults shared across sessions).\n"
            "  2. Any widget-callback issues (e.g. st.rerun() called "
            "unnecessarily, on_change handlers that cause double computation).\n"
            "  3. Performance opportunities (e.g. calculations called on every "
            "rerun that could be cached or deferred).\n"
            "  4. RTL/Hebrew display issues.\n"
            "  5. Concrete, code-level improvement suggestions (include the "
            "proposed code snippet for each).\n\n"
            "Enforce module boundaries: do not suggest moving business logic "
            "into views.py or UI logic into calculations.py.\n\n"
            "Output a structured UI_IMPROVEMENT_NOTES.md."
        ),
        expected_output=(
            "A structured UI_IMPROVEMENT_NOTES.md listing bugs, performance "
            "issues, RTL issues, and concrete improvement suggestions with "
            "code snippets, all respecting the project's strict modularity."
        ),
        agent=agent,
        output_file=_UI_NOTES_MD,
    )


# ---------------------------------------------------------------------------
# Task 4 – DB Migration Plan  (future use)
# ---------------------------------------------------------------------------

def create_db_migration_task(agent) -> Task:
    """Assign the DB Agent to design the Excel → relational DB migration plan.

    Suitable for a dedicated data-engineering crew run.
    """
    return Task(
        description=(
            "You are the Data Engineer. Read data_loading.py, utils.py, and "
            "constants.py thoroughly.\n\n"
            "Design a complete DB_MIGRATION_PLAN.md covering:\n"
            "  1. Current State – summarise the three Excel sheets "
            "(DB_HR_Staffing, DB_HR_Costs, DB_Service_count) and the MOH "
            "price-list format as the existing data sources.\n"
            "  2. Proposed Relational Schema – define SQLite tables (with "
            "CREATE TABLE DDL) to replace each sheet:\n"
            "     • hr_roles (Maarach, Agaf, Hativa, Machleket_Em, Yahida, "
            "Sector, Job_Desc, Monthly_Cost, Annual_Cost, Existing_FTE)\n"
            "     • service_hierarchy (Code, Original_Label, Maarach, Agaf, "
            "Hativa, Machleket_Em, Yahida)\n"
            "     • moh_tariffs (Code, Name, Tariff, source_file, loaded_at)\n"
            "     • service_activity (Original_Label, date, value)\n"
            "  3. Migration Script Outline – Python pseudocode for a one-time "
            "migration from the existing Excel files to the SQLite DB.\n"
            "  4. Updated data_loading.py Interface – show how "
            "load_growth_data() signature and internals would change to query "
            "SQLite instead of reading Excel, while preserving the same return "
            "signature for the rest of the app.\n"
            "  5. Streamlit Cache Compatibility – explain how st.cache_data "
            "would be adapted (e.g. cache the DB connection or query results).\n"
            "  6. PostgreSQL Upgrade Path – brief notes on what changes when "
            "moving from SQLite to PostgreSQL for multi-user deployment.\n"
            "  7. Rollback Plan – how to revert to Excel-based loading if "
            "needed.\n\n"
            "Output a structured DB_MIGRATION_PLAN.md."
        ),
        expected_output=(
            "A structured DB_MIGRATION_PLAN.md with SQL DDL, migration script "
            "outline, updated data_loading.py interface, cache strategy, and "
            "PostgreSQL upgrade path."
        ),
        agent=agent,
        output_file=_DB_PLAN_MD,
    )


# ---------------------------------------------------------------------------
# Task 5 – Backend Audit  (future use)
# ---------------------------------------------------------------------------

def create_backend_audit_task(agent) -> Task:
    """Assign the Backend Agent to audit calculations.py for accuracy and quality.

    Suitable for a dedicated backend-quality crew run.
    """
    return Task(
        description=(
            "You are the Python and Pandas Core Logic Expert. Read "
            "calculations.py, report.py, utils.py, and constants.py "
            "thoroughly.\n\n"
            "Produce a BACKEND_AUDIT.md covering:\n"
            "  1. Formula Verification – verify all financial formulas in "
            "calculate_detailed_rows() by tracing the code line by line. "
            "Confirm or correct the net/CAP/ROI/scenario/growth formulas.\n"
            "  2. Edge Case Analysis – identify inputs that could cause "
            "division by zero, NaN propagation, or incorrect results "
            "(e.g. qty=0, Unit_Revenue=None, Pct_Opt=0).\n"
            "  3. Pandas Quality Review – flag any chained indexing, "
            "unnecessary copy() calls, inefficient row-by-row iteration that "
            "could be vectorised, or missing fillna() guards.\n"
            "  4. Report Integrity Check – verify that every value written to "
            "the Excel report in report.py is sourced from df_flat columns "
            "that are correctly populated by calculate_detailed_rows().\n"
            "  5. Utils Review – check that all functions in utils.py are "
            "pure (no side effects, no I/O, no Streamlit), and suggest any "
            "missing input-validation guards.\n"
            "  6. Improvement Recommendations – concrete, code-level "
            "suggestions with proposed code snippets.\n\n"
            "Output a structured BACKEND_AUDIT.md."
        ),
        expected_output=(
            "A structured BACKEND_AUDIT.md with formula verification results, "
            "edge-case analysis, Pandas quality findings, report integrity "
            "check, utils review, and improvement recommendations with code "
            "snippets."
        ),
        agent=agent,
        output_file=_BACKEND_AUDIT_MD,
    )
