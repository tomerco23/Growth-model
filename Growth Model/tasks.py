"""
tasks.py – CrewAI task definitions for the Hospital Growth Model project.

Each function returns a crewai.Task bound to the appropriate agent.

Initial workflow tasks (used in crew_main.py):
  1. create_presentation_task       – Presentation Agent reads all source files
                                      and writes PROJECT_PRESENTATION.md.
  2. create_qa_review_task          – QA Agent cross-checks the presentation
                                      against the real code and writes QA_REVIEW.md.

Additional tasks for future or standalone crew workflows:
  3. create_ui_improvement_task     – UI Agent reviews views.py / app.py for bugs
                                      and proposes concrete improvements.
  4. create_db_migration_task       – DB Agent designs the Excel → database schema.
  5. create_backend_audit_task      – Backend Agent audits calculations.py for
                                      numerical accuracy and code quality.
  6. create_data_pipeline_opt_task  – Data Pipeline Agent inspects data_loading.py
                                      for vulnerabilities and outputs an
                                      optimisation plan.
  7. create_ux_improvement_plan_task – Product Manager Agent reviews views.py /
                                       app.py and outputs a UI/UX improvement plan
                                       with visualisation proposals.
  8. create_executive_summary_spec_task – Chief Economist Agent reviews
                                          calculations.py and defines a rich,
                                          dynamic executive summary template.
"""

from pathlib import Path

from crewai import Task

# Output files land in the same directory as the source code (Growth Model/)
_HERE: Path = Path(__file__).parent
_PRESENTATION_MD       = str(_HERE / "PROJECT_PRESENTATION.md")
_QA_REVIEW_MD          = str(_HERE / "QA_REVIEW.md")
_DB_PLAN_MD            = str(_HERE / "DB_MIGRATION_PLAN.md")
_UI_NOTES_MD           = str(_HERE / "UI_IMPROVEMENT_NOTES.md")
_BACKEND_AUDIT_MD      = str(_HERE / "BACKEND_AUDIT.md")
_DATA_PIPELINE_OPT_MD  = str(_HERE / "DATA_PIPELINE_OPTIMIZATION.md")
_UX_PLAN_MD            = str(_HERE / "UX_IMPROVEMENT_PLAN.md")
_EXEC_SUMMARY_SPEC_MD  = str(_HERE / "EXECUTIVE_SUMMARY_SPEC.md")


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
            "app=4%, no_show=0%, cap=35%)\n\n"

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


# ---------------------------------------------------------------------------
# Task 6 – Data Pipeline Optimization Plan
# ---------------------------------------------------------------------------

def create_data_pipeline_opt_task(agent) -> Task:
    """Assign the Data Pipeline Agent to inspect data_loading.py for
    vulnerabilities and produce a concrete optimisation plan.

    The task focuses on real-world failure modes specific to Ichilov
    hospital Excel exports (HR staffing, HR costs, service counts, and
    MOH price lists), rather than generic best practices.
    """
    return Task(
        description=(
            "You are the Data Integration & Pipeline Specialist. Your job is "
            "to read data_loading.py thoroughly and produce a concrete "
            "DATA_PIPELINE_OPTIMIZATION.md that a developer can execute "
            "immediately.\n\n"

            "STEP 1 – Read data_loading.py, utils.py, and constants.py "
            "in full before writing anything.\n\n"

            "STEP 2 – Audit every function for the following vulnerability "
            "classes and document EVERY instance you find:\n\n"

            "A. SILENT FAILURES\n"
            "   Situations where the code returns None, an empty DataFrame, "
            "or a zero value without surfacing a clear error message to the "
            "user. For each: quote the exact code lines, explain the failure "
            "mode, and provide a fixed version with a descriptive error/warning "
            "message.\n\n"

            "B. FRAGILE COLUMN DETECTION\n"
            "   Column mappings that rely on exact Hebrew string matches "
            "(e.g. 'קוד שירות', 'תעריף') or positional assumptions that will "
            "break if the hospital re-exports the file with a slightly different "
            "column name or layout. For each: show the current code, explain "
            "the fragility, and propose a fuzzy-match or ranked-candidate "
            "approach with a code snippet.\n\n"

            "C. ENCODING & TYPE SAFETY\n"
            "   Any place where a string-to-numeric conversion could fail or "
            "produce NaN without validation (e.g. clean_currency(), "
            "pd.to_numeric(errors='coerce') calls). For each: note the "
            "potential data loss and propose explicit validation with user-"
            "facing warnings.\n\n"

            "D. DUPLICATE & DATA QUALITY GAPS\n"
            "   The drop_duplicates(subset=['Code']) call in "
            "_load_service_hierarchy() silently discards rows. The "
            "_load_hr_costs() fallback to 0 when no cost data exists gives no "
            "warning. Document every such silent discard or silent default and "
            "propose logging/warning for each.\n\n"

            "E. MISSING COLUMN GUARDS\n"
            "   The GROUP_COLS and EXCLUDE_ID_COLS lists assume specific column "
            "names survive the rename step. Show what happens when a required "
            "column is absent, and propose a validation function that checks "
            "required columns exist before processing begins.\n\n"

            "STEP 3 – Propose a defensive data-loading architecture:\n"
            "   • A validate_hr_file(xls) function that checks required sheet "
            "names and columns before any parsing begins, returning a list of "
            "ValidationError objects rather than crashing.\n"
            "   • A validate_moh_file(df, filename) function for external "
            "price lists.\n"
            "   • Show the function signatures and a stub implementation for "
            "each.\n\n"

            "STEP 4 – Schema preparation for SQL migration:\n"
            "   Define a normalised data schema (table names, column names, "
            "types) that maps directly to the DataFrames currently produced by "
            "load_growth_data(). The schema must preserve all five return "
            "values: df_hr, df_srv_prices, df_srv_hier_map, df_hr_counts, "
            "h_srv. Provide CREATE TABLE DDL for each table.\n\n"

            "OUTPUT FORMAT – DATA_PIPELINE_OPTIMIZATION.md with sections:\n"
            "  1. Executive Summary (2–3 sentences on severity of findings)\n"
            "  2. Vulnerability Audit (one sub-section per class A–E above)\n"
            "  3. Defensive Architecture Proposals (validate_hr_file, "
            "validate_moh_file stubs)\n"
            "  4. SQL Schema for Migration\n"
            "  5. Priority Implementation Order (rank fixes by risk × effort)\n\n"
            "Use fenced code blocks (```python) for every code snippet. "
            "Reference exact line numbers from data_loading.py."
        ),
        expected_output=(
            "A structured DATA_PIPELINE_OPTIMIZATION.md with a vulnerability "
            "audit covering all five failure classes, defensive validation "
            "function stubs, SQL DDL schema, and a prioritised implementation "
            "order. Every finding references the exact source file line number."
        ),
        agent=agent,
        output_file=_DATA_PIPELINE_OPT_MD,
    )


# ---------------------------------------------------------------------------
# Task 7 – UX Improvement Plan
# ---------------------------------------------------------------------------

def create_ux_improvement_plan_task(agent) -> Task:
    """Assign the Product Manager Agent to review views.py and app.py and
    produce a concrete UX improvement plan with visualisation proposals.

    The focus is on the hospital executive user: non-technical, time-pressured,
    needs clear visual 'so what' signals to make a capital investment decision.
    """
    return Task(
        description=(
            "You are the Streamlit UX & Product Manager. Your job is to read "
            "views.py and app.py thoroughly and produce a concrete "
            "UX_IMPROVEMENT_PLAN.md that a Streamlit developer can implement "
            "sprint by sprint.\n\n"

            "STEP 1 – Read views.py, app.py, constants.py, and calculations.py "
            "in full. Understanding calculations.py is essential so you know "
            "exactly which data columns are available to visualise "
            "(df_flat columns: 'סה\"כ נטו לכיס', 'תרחיש אופטימי', "
            "'תרחיש פסימי', 'סה\"כ אחרי קאפ', 'Category_Heb', 'שם שירות', "
            "Net_Y2, Net_Y3, Net_Y4, etc.).\n\n"

            "STEP 2 – Analyse the current UX and document friction points "
            "across the complete user journey:\n\n"

            "  A. FIRST-TIME USER ONBOARDING\n"
            "  What happens when a user opens the app with no files uploaded? "
            "Is there guidance? What's missing? Propose a welcome banner or "
            "onboarding checklist with a code snippet.\n\n"

            "  B. SIDEBAR INFORMATION ARCHITECTURE\n"
            "  The sidebar currently contains: project name input, save/load "
            "expander, data upload expander, and parameters expander. Assess "
            "the hierarchy. Is the parameter section visible enough? Are the "
            "default values (ovh=29%, hmo=18.5%, vol=1.9%, app=4%, "
            "no_show=0%, cap=35%) explained anywhere? Propose improvements "
            "with tooltips (st.help) or st.info callouts.\n\n"

            "  C. EDIT VIEW – PERSISTENT MODEL SUMMARY\n"
            "  While adding items across the three tabs (CAPEX / OPEX / Revenue) "
            "the user has no running total visible. Propose a compact, always-"
            "visible summary bar (e.g. st.columns with revenue total, cost "
            "total, and current profit estimate) that updates live. Show where "
            "in show_edit_view() this would be inserted.\n\n"

            "  D. REPORT VIEW – DATA VISUALISATIONS\n"
            "  The current report view shows three raw st.dataframe() calls "
            "with no charts. Define the following four charts with full "
            "implementation guidance (library choice, data preparation from "
            "df_flat, Streamlit call):\n\n"
            "  D1. Revenue Waterfall Chart\n"
            "      Show the progression: Gross Revenue → after HMO discount → "
            "after Volume discount → after Appeals provision → after Overhead "
            "= Net to Pocket. Use plotly.graph_objects.Waterfall. Provide the "
            "exact data extraction code from df_flat.\n\n"
            "  D2. Scenario Comparison Bar Chart\n"
            "      For each item (or category), show three bars: base, "
            "optimistic, pessimistic net value. Use st.bar_chart or "
            "plotly.express.bar. Show how to pivot df_flat to get the right "
            "shape.\n\n"
            "  D3. 4-Year Projection Line Chart\n"
            "      A multi-line chart showing Net_Y1 (= 'סה\"כ נטו לכיס'), "
            "Net_Y2, Net_Y3, Net_Y4 for revenue items. Use plotly.express.line. "
            "Show the melt/pivot required.\n\n"
            "  D4. Sensitivity Tornado Chart (No-Show & Discount Risk)\n"
            "      Show how total net profit changes as No-Show rate varies "
            "from 0% to 20% and as HMO discount varies from 10% to 30%. "
            "This is a horizontal bar chart. Describe the calculation logic "
            "(re-running calculate_detailed_rows() with varied params) and "
            "whether it should live in a new function in calculations.py or "
            "be computed inline in views.py. Enforce module boundary "
            "recommendation.\n\n"

            "  E. MANAGEMENT SIMULATOR IMPROVEMENTS\n"
            "  The current simulator uses sliders but the KPI metric cards "
            "above don't update in response to slider movement without a full "
            "rerun. Propose a UX pattern that makes the connection between "
            "sliders and KPIs visually obvious (e.g. live delta display, "
            "colour change, or a dedicated simulator results panel).\n\n"

            "  F. MOBILE / TABLET COMPATIBILITY\n"
            "  Hospital executives often view dashboards on tablets. Note any "
            "layout issues (e.g. 5-column cascading filter on a tablet screen) "
            "and propose responsive alternatives.\n\n"

            "STEP 3 – Prioritise all proposals into a sprint plan:\n"
            "  Sprint 1 (high impact, low effort): ...\n"
            "  Sprint 2 (high impact, medium effort): ...\n"
            "  Sprint 3 (medium impact, higher effort): ...\n\n"

            "OUTPUT FORMAT – UX_IMPROVEMENT_PLAN.md with:\n"
            "  1. Executive UX Summary\n"
            "  2. User Journey Friction Points (A–F above)\n"
            "  3. Visualisation Specs (D1–D4) with implementation code\n"
            "  4. Sprint Plan\n"
            "  5. Module Boundary Notes (confirm no business logic moves to views.py)\n\n"
            "Use fenced code blocks (```python) for every code snippet."
        ),
        expected_output=(
            "A structured UX_IMPROVEMENT_PLAN.md covering friction-point "
            "analysis, four fully-specified data visualisation implementations "
            "(waterfall, scenario bar, 4-year projection, tornado chart), a "
            "sprint-based priority plan, and explicit module boundary "
            "confirmation for each proposal."
        ),
        agent=agent,
        output_file=_UX_PLAN_MD,
    )


# ---------------------------------------------------------------------------
# Task 8 – Executive Summary Specification
# ---------------------------------------------------------------------------

def create_executive_summary_spec_task(agent) -> Task:
    """Assign the Chief Economist Agent to review calculations.py and
    generate_verbal_analysis() in report.py, then define a richer, dynamic
    executive summary spec.

    The current generate_verbal_analysis() produces a 3-line text.
    This task defines a detailed spec for replacing it with a multi-paragraph,
    data-driven narrative that adapts to the full range of model outputs.
    """
    return Task(
        description=(
            "You are the Chief Economist & Business Analyst. Your job is to "
            "read calculations.py and report.py thoroughly, then produce "
            "EXECUTIVE_SUMMARY_SPEC.md — a complete specification for how the "
            "executive summary text in this model should be dynamically "
            "generated based on ROI, scenario outcomes, and risk factors.\n\n"

            "STEP 1 – Read calculations.py in full to understand every output "
            "of calculate_detailed_rows(): total_capex, total_opex, total_rev, "
            "total_prof_base, total_prof_opt, total_prof_pess, roi, and the "
            "full df_flat DataFrame with all its columns.\n\n"

            "STEP 2 – Read report.py and locate generate_verbal_analysis(). "
            "Understand its current inputs (profit_base, profit_pess, capex, "
            "revenue, roi) and its current three-line output logic:\n"
            "  • profit_pess > 0  → '✅ הפרויקט איתן כלכלית'\n"
            "  • profit_base > 0  → '⚠️ הפרויקט רווחי בתרחיש הבסיס'\n"
            "  • else             → '🛑 הפרויקט אינו כדאי כלכלית'\n\n"

            "STEP 3 – Design the EXECUTIVE_SUMMARY_SPEC.md. This is a spec "
            "document (not an implementation), but it must include enough "
            "detail that a developer can implement it without ambiguity. "
            "Cover ALL of the following:\n\n"

            "3A. VIABILITY CLASSIFICATION\n"
            "    Define a richer 5-level classification (not just 3) based on "
            "the combination of ROI, profit_base, profit_pess, and the ratio "
            "of optimistic to pessimistic profit. Specify the exact threshold "
            "values and the corresponding status label, colour indicator, and "
            "one-sentence verdict for each level. Ground your thresholds in "
            "realistic Israeli hospital investment benchmarks.\n\n"

            "3B. ROI NARRATIVE\n"
            "    Define a conditional narrative for the ROI figure:\n"
            "    • ROI < 3 years: 'Exceptional return...'\n"
            "    • ROI 3–5 years: 'Strong return...'\n"
            "    • ROI 5–7 years: 'Acceptable return...'\n"
            "    • ROI 7–12 years: 'Extended payback period...'\n"
            "    • ROI > 12 years or no profit: 'Investment not recovered...'\n"
            "    Write the exact Hebrew and English text template for each "
            "bracket, including the variable placeholders (e.g. {roi:.1f}).\n\n"

            "3C. SENSITIVITY RISK SECTION\n"
            "    Define how to compute and narrate sensitivity to three risk "
            "drivers directly from the model's existing outputs:\n"
            "    • No-Show risk: compare profit_base vs profit_pess to estimate "
            "the model's sensitivity. If (profit_base - profit_pess) / "
            "profit_base > 30%, flag as HIGH sensitivity.\n"
            "    • Revenue concentration risk: if the top revenue item "
            "contributes > 60% of total_rev (computable from df_flat), flag as "
            "HIGH concentration risk.\n"
            "    • CAPEX coverage: ratio of total_capex to total_rev; if > 50%, "
            "flag as HIGH upfront burden.\n"
            "    For each risk flag, define the exact text to include in the "
            "summary (both a ⚠️ warning and the supporting numbers).\n\n"

            "3D. SCENARIO COMPARISON PARAGRAPH\n"
            "    Define a template paragraph that compares net and CAP "
            "scenarios. The CAP profit is not a direct output of "
            "calculate_detailed_rows() — explain what data from df_flat would "
            "be needed to compute it (hint: sum 'סה\"כ אחרי קאפ' for Revenue "
            "rows, then subtract OPEX and HR costs) and specify the formula.\n\n"

            "3E. YEAR-BY-YEAR GROWTH OUTLOOK\n"
            "    Net_Y2, Net_Y3, Net_Y4 are available per revenue row in "
            "df_flat. Define how to aggregate them to a project-level 4-year "
            "total-profit projection, and write a one-sentence template that "
            "summarises the compound growth outlook (e.g. 'Over 4 years, total "
            "projected net income is ₪{total_4yr:,.0f}, representing a "
            "{growth_pct:.0f}% uplift on Year 1.').\n\n"

            "3F. RECOMMENDATION STATEMENT\n"
            "    Define the final recommendation sentence. It must reference "
            "the pessimistic scenario explicitly (as the conservative bound), "
            "the ROI, and the viability classification. Provide both a Hebrew "
            "and an English version of the template.\n\n"

            "3G. UPDATED generate_verbal_analysis() SIGNATURE\n"
            "    Propose an updated Python function signature for "
            "generate_verbal_analysis() that accepts all the additional inputs "
            "needed for the richer summary (df_flat, total_prof_opt, "
            "CAP-revenue total, etc.). Do NOT write the full implementation — "
            "just the signature, a docstring, and the return type. The "
            "implementation is left to the Backend Agent.\n\n"

            "OUTPUT FORMAT – EXECUTIVE_SUMMARY_SPEC.md with:\n"
            "  1. Overview & Motivation (why the current 3-line summary falls short)\n"
            "  2. Viability Classification Table (5 levels with thresholds)\n"
            "  3. ROI Narrative Templates (5 brackets, bilingual)\n"
            "  4. Sensitivity Risk Section Spec\n"
            "  5. Scenario Comparison Paragraph Template\n"
            "  6. 4-Year Growth Outlook Template\n"
            "  7. Final Recommendation Statement (bilingual template)\n"
            "  8. Updated generate_verbal_analysis() Signature\n"
            "  9. Implementation Notes for the Backend Agent\n\n"
            "Be precise. Every template must include exact variable placeholder "
            "names that match the actual outputs of calculate_detailed_rows()."
        ),
        expected_output=(
            "A structured EXECUTIVE_SUMMARY_SPEC.md with a 5-level viability "
            "classification table, bilingual narrative templates for all ROI "
            "brackets, sensitivity risk formulas and text templates, scenario "
            "comparison and growth-outlook templates, and an updated "
            "generate_verbal_analysis() function signature with docstring — "
            "all grounded in the actual variable names from calculations.py."
        ),
        agent=agent,
        output_file=_EXEC_SUMMARY_SPEC_MD,
    )
