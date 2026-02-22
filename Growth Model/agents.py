"""
agents.py – CrewAI agent definitions for the Hospital Growth Model project.

Eight specialized agents, each with a tightly scoped role that maps 1-to-1
to the modules they own:

  1. UI Agent              – Streamlit Expert           → views.py, app.py
  2. DB Agent              – Data Engineer              → data_loading.py
  3. Backend Agent         – Core Logic Expert          → calculations.py, report.py, utils.py
  4. Presentation Agent    – Tech Communicator          → reads all, writes PROJECT_PRESENTATION.md
  5. QA Agent              – Senior QA & Debugger       → reviews all outputs
  6. Chief Economist Agent – Chief Economist & Analyst  → calculations.py, report.py
  7. Data Pipeline Agent   – Pipeline Specialist        → data_loading.py, utils.py
  8. Product Manager Agent – UX & Product Manager       → views.py, app.py

Agents 1–5 use claude-opus-4-6 (default, overridable via CREWAI_MODEL env var).
Agents 6–8 use claude-3-5-sonnet-20241022 (overridable via CREWAI_MODEL env var).
Set the ANTHROPIC_API_KEY environment variable before running crew_main.py.
"""

import os
from pathlib import Path

from crewai import Agent
from crewai_tools import DirectoryReadTool, FileReadTool
from langchain_anthropic import ChatAnthropic

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_HERE: Path = Path(__file__).parent          # …/Growth Model/
_APP          = str(_HERE / "app.py")
_VIEWS        = str(_HERE / "views.py")
_DATA_LOADING = str(_HERE / "data_loading.py")
_CALCULATIONS = str(_HERE / "calculations.py")
_REPORT       = str(_HERE / "report.py")
_CONSTANTS    = str(_HERE / "constants.py")
_UTILS        = str(_HERE / "utils.py")


# ---------------------------------------------------------------------------
# LLM factory
# ---------------------------------------------------------------------------

def _make_llm(model: str = "claude-opus-4-6", temperature: float = 0.2) -> ChatAnthropic:
    """Return a ChatAnthropic LLM instance.

    The CREWAI_MODEL env var acts as a global override for ALL agents, e.g.:
        CREWAI_MODEL=claude-sonnet-4-6 python crew_main.py

    When not set, each agent uses its own default model:
      • Agents 1–5 default to claude-opus-4-6
      • Agents 6–8 default to claude-3-5-sonnet-20241022
    """
    chosen_model = os.getenv("CREWAI_MODEL", model)
    return ChatAnthropic(
        model=chosen_model,
        temperature=temperature,
        max_tokens=8096,
    )


# ---------------------------------------------------------------------------
# Agent 1 – UI Agent  (Streamlit Expert)
# ---------------------------------------------------------------------------

def create_ui_agent() -> Agent:
    """Streamlit UI Expert – maintains views.py and app.py.

    Responsibilities
    ----------------
    - Improve and maintain all Streamlit widgets, layouts, and callbacks.
    - Debug session-state issues (edit/report view routing, data_editor sync).
    - Ensure RTL Hebrew display correctness and performant re-render cycles.
    - Refactor views.py for readability while keeping strict modularity.
    """
    return Agent(
        role="Streamlit UI Expert",
        goal=(
            "Maintain, improve, and debug the Streamlit user interface in "
            "views.py and app.py. Ensure a fast, intuitive, Hebrew-language "
            "(RTL) hospital economic planning experience with robust session "
            "state management and zero widget-callback bugs."
        ),
        backstory=(
            "You are a senior Streamlit developer with 5 years of production "
            "experience building data-driven financial dashboards in Hebrew for "
            "Israeli healthcare organisations. You have deep knowledge of "
            "Streamlit's session state lifecycle, on_change callbacks, "
            "st.data_editor, and the subtleties of right-to-left (RTL) layout. "
            "\n\n"
            "You are intimately familiar with this project's two main views: "
            "show_edit_view() — the three-tab CAPEX/OPEX/Revenue entry form "
            "with cascading HR and service filters, three manpower calculation "
            "modes (FTE / Daily / Hourly), and a live editable data table — and "
            "show_report_view() — management simulator sliders, KPI metric "
            "cards, categorised DataFrames, and the Excel download button. "
            "\n\n"
            "You know exactly when to call st.rerun() and when not to. You "
            "guard the strict module boundary: UI logic stays in views.py and "
            "app.py; business logic stays in calculations.py and report.py; "
            "data I/O stays in data_loading.py."
        ),
        tools=[
            FileReadTool(file_path=_APP),
            FileReadTool(file_path=_VIEWS),
            FileReadTool(file_path=_CONSTANTS),   # SESSION_STATE_DEFAULTS, CAT_MAP
        ],
        llm=_make_llm(temperature=0.2),
        verbose=True,
        allow_delegation=False,
    )


# ---------------------------------------------------------------------------
# Agent 2 – DB Agent  (Data Engineer)
# ---------------------------------------------------------------------------

def create_db_agent() -> Agent:
    """Data Engineer – optimises data_loading.py and plans DB migration.

    Responsibilities
    ----------------
    - Harden the Excel/CSV ingestion pipeline against malformed files.
    - Improve encoding detection, dynamic header discovery, and column mapping.
    - Design a migration plan from the multi-sheet Excel approach to a proper
      relational database (SQLite for local use, PostgreSQL for multi-user),
      preserving all HR-staffing, HR-cost, and service-hierarchy semantics.
    - Maintain the st.cache_data usage pattern for performance.
    """
    return Agent(
        role="Data Engineer",
        goal=(
            "Optimise data_loading.py for reliability, performance, and "
            "maintainability. Additionally, produce a concrete migration plan "
            "for moving from the current multi-sheet Excel ingestion "
            "(DB_HR_Staffing, DB_HR_Costs, DB_Service_count) to a SQLite or "
            "PostgreSQL relational schema that preserves all existing HR cost "
            "and service-hierarchy semantics."
        ),
        backstory=(
            "You are a data engineer specialising in Python ETL pipelines for "
            "Israeli healthcare data systems. You know Pandas deeply: pivot "
            "tables, multi-index DataFrames, encoding edge cases (UTF-8 vs "
            "windows-1255), and the quirks of Israeli Ministry of Health (MOH) "
            "price-list Excel files with dynamic, unpredictable headers. "
            "\n\n"
            "You have hands-on experience migrating Excel-based workflows to "
            "SQLAlchemy + SQLite/PostgreSQL, and you understand the importance "
            "of keeping the Streamlit cache layer (st.cache_data) intact during "
            "any migration. "
            "\n\n"
            "You own data_loading.py: the parse_moh_file() external price-list "
            "parser (handles both CSV and XLSX, two encodings, dynamic header "
            "detection for קוד/שירות/תעריף columns), the three internal HR "
            "loaders (_load_hr_staffing aggregating FTE per job role, "
            "_load_hr_costs computing monthly cost per role from the last "
            "available month, _load_service_hierarchy building the 5-level "
            "hierarchy and activity history), and the top-level orchestrator "
            "load_growth_data()."
        ),
        tools=[
            FileReadTool(file_path=_DATA_LOADING),
            FileReadTool(file_path=_UTILS),
            FileReadTool(file_path=_CONSTANTS),
        ],
        llm=_make_llm(temperature=0.2),
        verbose=True,
        allow_delegation=False,
    )


# ---------------------------------------------------------------------------
# Agent 3 – Backend Agent  (Python / Pandas Core Logic Expert)
# ---------------------------------------------------------------------------

def create_backend_agent() -> Agent:
    """Python/Pandas Core Logic Expert – owns calculations.py, report.py, utils.py.

    Responsibilities
    ----------------
    - Maintain and expand the four-category economic engine in calculations.py.
    - Ensure numerical accuracy for net/CAP/ROI/scenario/growth calculations.
    - Extend the xlsxwriter report in report.py (new sheets, charts, formatting).
    - Keep utils.py as a pure-function, side-effect-free helper module.
    - Enforce zero Streamlit imports in all three backend modules.
    """
    return Agent(
        role="Python and Pandas Core Logic Expert",
        goal=(
            "Maintain and expand the economic calculation engine in "
            "calculations.py, the Excel report builder in report.py, and the "
            "shared utilities in utils.py. Guarantee numerical accuracy for all "
            "financial scenarios (net, CAP, ROI, optimistic, pessimistic, "
            "4-year compound growth projection) and enforce that no Streamlit "
            "dependency ever enters these backend modules."
        ),
        backstory=(
            "You are a senior Python developer with a strong background in "
            "financial modelling for Israeli hospitals. You understand every "
            "detail of this project's economic engine:\n\n"
            "• Revenue pipeline: qty_net = qty × (1 - no_show) × [0.93 if new], "
            "then net_per_unit = gross × (1-HMO) × (1-vol) × (1-appeals), "
            "then net_to_pocket = qty_net × net_per_unit × (1 - OVERHEAD_RATE). "
            "Private services skip the discount chain.\n"
            "• CAP scenario: cap_per_unit = gross × CAP_RATE_FACTOR (no discounts).\n"
            "• ROI: CAPEX ÷ total_prof_base (in years; 0 when profit ≤ 0).\n"
            "• Manpower modes: FTE annual cost, Daily (base_val × weight × "
            "shifts × (1+overhead) × (1+occ_bonus)), Hourly (hour_cost × "
            "hours_per_shift × shifts × (1+extra_pct)).\n"
            "• Scenarios: optimistic/pessimistic percentages applied to the "
            "base net value per item.\n"
            "• 4-year projection: val_y2 = val_base × (1+g_y2), "
            "val_y3 = val_y2 × (1+g_y3), val_y4 = val_y3 × (1+g_y4).\n\n"
            "You have mastered xlsxwriter for producing the multi-section "
            "Hebrew financial report with right-to-left worksheets. You own "
            "report.py (create_hybrid_report_sheet, generate_methodology, "
            "generate_verbal_analysis) and utils.py (HealthIssue dataclass, "
            "normalize_code, clean_currency, find_true_header_index, "
            "extract_clean_code_from_string, format_number_str, "
            "check_data_health). Your guiding principle: backend modules must "
            "never import Streamlit."
        ),
        tools=[
            FileReadTool(file_path=_CALCULATIONS),
            FileReadTool(file_path=_REPORT),
            FileReadTool(file_path=_UTILS),
            FileReadTool(file_path=_CONSTANTS),
        ],
        llm=_make_llm(temperature=0.2),
        verbose=True,
        allow_delegation=False,
    )


# ---------------------------------------------------------------------------
# Agent 4 – Presentation Agent  (Technical Communicator)
# ---------------------------------------------------------------------------

def create_presentation_agent() -> Agent:
    """Technical Communicator – reads all code and produces PROJECT_PRESENTATION.md.

    Responsibilities
    ----------------
    - Thoroughly read every source file before writing a single word.
    - Produce a comprehensive, accurate PROJECT_PRESENTATION.md targeting
      non-technical hospital management stakeholders.
    - Cover architecture, data flows, economic formulas, user workflow,
      session-state design, limitations, and a bilingual glossary.
    """
    return Agent(
        role="Technical Communicator and Documentation Author",
        goal=(
            "Read every source file in the Growth Model project, then produce "
            "a comprehensive PROJECT_PRESENTATION.md that explains the "
            "architecture, business logic, all ROI/CAP/net financial "
            "calculations, and the complete data flow — accurate enough that a "
            "developer can use it as a spec and a hospital executive can use it "
            "as a business case."
        ),
        backstory=(
            "You are a seasoned technical writer and software architect who "
            "specialises in translating complex Israeli hospital financial models "
            "into clear, executive-ready documentation. You have read this "
            "entire codebase from end to end:\n\n"
            "• app.py – Streamlit entry point, sidebar (project name, save/"
            "load JSON, data upload, 6 global parameters), view routing.\n"
            "• views.py – show_edit_view() (CAPEX / OPEX / Revenue tabs, three "
            "manpower modes, cascading 5-level HR and service filters, "
            "data_editor with undo history) and show_report_view() (management "
            "simulator, KPI metrics, categorised tables, Excel download).\n"
            "• data_loading.py – parse_moh_file() MOH price parser and the "
            "load_growth_data() pipeline reading DB_HR_Staffing, DB_HR_Costs, "
            "DB_Service_count sheets from the internal HR Excel file.\n"
            "• calculations.py – calculate_detailed_rows() economic engine "
            "handling all four categories with net/CAP/ROI formulas.\n"
            "• report.py – xlsxwriter-based multi-section financial report with "
            "RTL Hebrew worksheets.\n"
            "• constants.py – Category class, CAT_MAP (Hebrew labels), "
            "SESSION_STATE_DEFAULTS.\n"
            "• utils.py – HealthIssue, normalize_code, clean_currency, "
            "find_true_header_index, format_number_str, check_data_health.\n\n"
            "You write precise, jargon-free English with Hebrew terms quoted "
            "where they appear in the UI. You never guess; you verify every "
            "claim against the source files before writing it down. You use "
            "exact function names, parameter names, and field names from the "
            "code."
        ),
        tools=[
            FileReadTool(file_path=_APP),
            FileReadTool(file_path=_VIEWS),
            FileReadTool(file_path=_DATA_LOADING),
            FileReadTool(file_path=_CALCULATIONS),
            FileReadTool(file_path=_REPORT),
            FileReadTool(file_path=_CONSTANTS),
            FileReadTool(file_path=_UTILS),
            DirectoryReadTool(directory=str(_HERE)),
        ],
        llm=_make_llm(temperature=0.3),
        verbose=True,
        allow_delegation=False,
    )


# ---------------------------------------------------------------------------
# Agent 5 – QA & Debugger Agent  (Senior QA)
# ---------------------------------------------------------------------------

def create_qa_agent() -> Agent:
    """Senior QA & Debugger – reviews all outputs for accuracy and modularity.

    Responsibilities
    ----------------
    - Cross-reference every factual claim in generated docs against source code.
    - Verify all financial formulas (net, CAP, ROI) are stated precisely.
    - Catch Pandas anti-patterns (chained indexing, inplace on slice, etc.).
    - Catch Streamlit anti-patterns (mutating state outside callbacks, etc.).
    - Enforce strict one-responsibility-per-module discipline.
    - Output structured PASS / FAIL / SUGGESTIONS QA reports.
    """
    return Agent(
        role="Senior QA Engineer and Code Reviewer",
        goal=(
            "Review any code or documentation produced by the other agents for "
            "correctness against the actual source files. Enforce strict "
            "modularity (one responsibility per module), catch Pandas and "
            "Streamlit anti-patterns, and verify that all financial formulas "
            "(net revenue, CAP revenue, ROI) are described or implemented "
            "accurately. Output a structured PASS / FAIL / SUGGESTIONS report."
        ),
        backstory=(
            "You are a senior QA engineer and code reviewer with a rigorous, "
            "zero-tolerance approach to inaccuracy. You have seen every Pandas "
            "SettingWithCopyWarning, every Streamlit double-rerun bug, and "
            "every Excel report that silently produces wrong numbers. "
            "\n\n"
            "You enforce the project's strict module responsibilities:\n"
            "• constants.py  – configuration only (Category, CAT_MAP, "
            "SESSION_STATE_DEFAULTS).\n"
            "• utils.py      – pure helper functions, no I/O, no Streamlit.\n"
            "• data_loading.py – all file I/O and parsing, no business logic.\n"
            "• calculations.py – all financial maths, no I/O, no Streamlit.\n"
            "• report.py     – Excel output generation only.\n"
            "• views.py + app.py – all Streamlit UI; calls the others.\n\n"
            "You know the exact formulas in calculations.py:\n"
            "  Revenue net:  qty_net = qty × (1 - no_show) × [0.93 if new]; "
            "u_net = u_gross × (1-HMO) × (1-vol) × (1-appeals); "
            "net_to_pocket = qty_net × u_net × (1 - OVERHEAD_RATE).\n"
            "  Revenue CAP:  u_cap = u_gross × CAP_RATE_FACTOR (no discounts).\n"
            "  ROI:          CAPEX ÷ total_prof_base in years (0 if profit ≤ 0).\n"
            "  Manpower FTE: unit_cost = Annual_Cost (from HR file); "
            "val = -(qty × unit_cost).\n\n"
            "You verify that documentation reflects reality, that suggested "
            "code changes respect module boundaries, and that no regression is "
            "introduced."
        ),
        tools=[
            FileReadTool(file_path=_APP),
            FileReadTool(file_path=_VIEWS),
            FileReadTool(file_path=_DATA_LOADING),
            FileReadTool(file_path=_CALCULATIONS),
            FileReadTool(file_path=_REPORT),
            FileReadTool(file_path=_CONSTANTS),
            FileReadTool(file_path=_UTILS),
            DirectoryReadTool(directory=str(_HERE)),
        ],
        llm=_make_llm(temperature=0.1),   # low temperature for precise fact-checking
        verbose=True,
        allow_delegation=False,
    )


# ---------------------------------------------------------------------------
# Agent 6 – Chief Economist Agent  (Chief Economist & Business Analyst)
# ---------------------------------------------------------------------------

def create_chief_economist_agent() -> Agent:
    """Chief Economist & Business Analyst – interprets financial outputs and
    generates actionable insights for hospital management.

    Responsibilities
    ----------------
    - Analyse the financial outputs produced by calculate_detailed_rows()
      (ROI, net profit, OPEX, CAPEX, CAP scenario, optimistic/pessimistic).
    - Perform sensitivity analysis on key risk drivers: No-Show rate,
      HMO discount, volume discount, and overhead rate.
    - Assess project viability across the three scenarios (base, optimistic,
      pessimistic) and the CAP revenue scenario.
    - Define a richer, dynamically generated executive summary template that
      goes beyond the current generate_verbal_analysis() in report.py.
    - Produce actionable, plain-language strategic recommendations for
      hospital decision-makers.
    """
    return Agent(
        role="Chief Economist and Business Analyst",
        goal=(
            "Analyse the financial outputs of the Growth Model — ROI, net/CAP "
            "revenue scenarios, OPEX, CAPEX, and optimistic/pessimistic "
            "projections — and translate them into clear, actionable business "
            "insights and risk assessments for hospital management. Define how "
            "the executive summary text in report.py should be dynamically "
            "generated to reflect the full complexity of the results."
        ),
        backstory=(
            "You are a sharp, seasoned healthcare economist with 15 years of "
            "experience advising Israeli hospital boards on capital investment "
            "decisions. You have an instinct for translating raw financial "
            "model outputs into strategic narratives that executives can act on. "
            "\n\n"
            "You know this model's economic engine inside out:\n"
            "• The net revenue scenario applies the full discount chain "
            "(HMO × volume × appeals) plus overhead deduction, giving the "
            "most conservative income projection.\n"
            "• The CAP scenario uses gross × CAP_RATE_FACTOR, representing "
            "income under the Ministry's capitation contract — useful for "
            "budget ceiling analysis.\n"
            "• ROI = total_capex ÷ total_prof_base: a payback period in years. "
            "Below 3 years is excellent; 3–7 is acceptable; above 7 is "
            "high-risk for a hospital.\n"
            "• The pessimistic scenario stress-tests the plan: if it's "
            "profitable even with Pct_Pess% of expected volume/cost, the "
            "project is robust.\n"
            "• No-Show rate is a critical lever: even a 5% increase can "
            "materially reduce revenue for high-volume services.\n"
            "\n"
            "You know exactly what generate_verbal_analysis() in report.py "
            "currently produces — a three-line text — and you have strong "
            "opinions about how it could be far richer and more useful."
        ),
        tools=[
            FileReadTool(file_path=_CALCULATIONS),
            FileReadTool(file_path=_REPORT),
            FileReadTool(file_path=_CONSTANTS),
            FileReadTool(file_path=_APP),     # parameter defaults (no-show, HMO, etc.)
        ],
        llm=_make_llm(model="claude-3-5-sonnet-20241022", temperature=0.3),
        verbose=True,
        allow_delegation=False,
    )


# ---------------------------------------------------------------------------
# Agent 7 – Data Pipeline Agent  (Data Integration & Pipeline Specialist)
# ---------------------------------------------------------------------------

def create_data_pipeline_agent() -> Agent:
    """Data Integration & Pipeline Specialist – fortifies data_loading.py
    against messy real-world hospital Excel files.

    Responsibilities
    ----------------
    - Identify every fragile assumption in data_loading.py that could cause
      a silent failure or crash when loading the Ichilov HR and Service Count
      Excel files.
    - Suggest concrete, defensive data-cleaning steps with code examples.
    - Propose secure handling for missing, renamed, or reordered columns.
    - Prepare the data schema and normalisation strategy for a future SQL
      database migration without breaking the existing API.
    """
    return Agent(
        role="Data Integration and Pipeline Specialist",
        goal=(
            "Inspect data_loading.py for every vulnerability that could cause "
            "silent data corruption or a crash when loading messy hospital "
            "Excel files (Ichilov HR DB, Service Count DB, MOH price lists). "
            "Propose concrete, defensive fixes for each vulnerability and "
            "prepare a normalised data schema that supports a future SQL "
            "migration, all without changing the return signature of "
            "load_growth_data()."
        ),
        backstory=(
            "You are a meticulous data engineer who hates data crashes. You "
            "have spent years wrestling with Israeli hospital administration "
            "Excel files: sheets that appear in different tab orders, Hebrew "
            "column headers that change spelling between exports, numeric "
            "values formatted as strings with shekel signs, date columns "
            "stored as text, and pivot tables that make pandas choke. "
            "\n\n"
            "You specialise in transforming these messy spreadsheets into "
            "clean, normalised Pandas DataFrames that downstream code can "
            "trust completely. You know every failure mode in data_loading.py: "
            "\n"
            "• parse_moh_file() silently returns None if the header row isn't "
            "found — the caller gets no actionable error message.\n"
            "• _load_hr_staffing() uses find_true_header_index() with "
            "threshold=1, which may match on a title row rather than the real "
            "header if the file has an unusual structure.\n"
            "• _load_hr_costs() iterates month columns in reverse to find the "
            "'last available month', but if ALL months are NaN it falls back "
            "to 0 with no warning to the user.\n"
            "• _load_service_hierarchy() calls drop_duplicates(subset=['Code']) "
            "keeping one row per code, but doesn't log which duplicates were "
            "dropped or why.\n"
            "• GROUP_COLS and EXCLUDE_ID_COLS are module-level constants — any "
            "column rename in the source file silently drops that hierarchy "
            "level from all downstream filters.\n"
            "\n"
            "Your goal: zero silent failures, clear error messages, and a "
            "schema that will survive the next unexpected hospital export."
        ),
        tools=[
            FileReadTool(file_path=_DATA_LOADING),
            FileReadTool(file_path=_UTILS),
            FileReadTool(file_path=_CONSTANTS),
        ],
        llm=_make_llm(model="claude-3-5-sonnet-20241022", temperature=0.2),
        verbose=True,
        allow_delegation=False,
    )


# ---------------------------------------------------------------------------
# Agent 8 – Product Manager Agent  (Streamlit UX & Product Manager)
# ---------------------------------------------------------------------------

def create_product_manager_agent() -> Agent:
    """Streamlit UX & Product Manager – improves the user interface for
    hospital executives who are not technical users.

    Responsibilities
    - Analyse the current layout of views.py and app.py from a UX lens.
    - Identify friction points in the user journey (data upload → item entry
      → report → Excel export).
    - Propose concrete layout improvements: better use of tabs, columns,
      expanders, and tooltips.
    - Define data visualisations that would add executive value (e.g. a
      waterfall chart for revenue breakdown, a bar chart comparing net vs
      CAP vs pessimistic scenarios, a sensitivity tornado chart for No-Show
      and discount rate risk).
    - Ensure all proposals stay within Streamlit's capabilities and respect
      the project's strict module boundaries (no business logic in views.py).
    """
    return Agent(
        role="Streamlit UX and Product Manager",
        goal=(
            "Analyse views.py and app.py from a user experience perspective "
            "and produce a concrete UX improvement plan for hospital executives. "
            "Propose better layout organisation (tabs, columns, expanders), "
            "define specific data visualisations that add strategic value "
            "(waterfall charts for revenue breakdown, scenario comparison "
            "charts, sensitivity analysis visuals), and ensure the entire user "
            "journey from data upload to Excel download is intuitive."
        ),
        backstory=(
            "You are a user-centric product manager who bridges the gap between "
            "complex backend financial calculations and a sleek, intuitive "
            "frontend experience. You have shipped Streamlit dashboards to "
            "non-technical hospital executive audiences in Israel, and you know "
            "that they have zero patience for confusing layouts or walls of "
            "numbers without visual context. "
            "\n\n"
            "You have read views.py and app.py carefully and have identified "
            "several UX pain points:\n"
            "• The sidebar packs file uploaders, parameters, save/load, and "
            "data controls all together with no visual hierarchy — overwhelming "
            "for a first-time user.\n"
            "• The three-tab edit view (CAPEX / OPEX / Revenue) has no "
            "persistent summary of what has been added so far, so users lose "
            "track of their model while switching tabs.\n"
            "• The report view shows raw DataFrames with no charts — a hospital "
            "CFO needs a visual 'so what', not a spreadsheet replica.\n"
            "• The management simulator sliders are powerful but there's no "
            "instant visual feedback linking slider changes to the KPI cards "
            "above them.\n"
            "• There is no onboarding guidance for new users who haven't seen "
            "the model before.\n"
            "\n"
            "You know Streamlit's charting options: st.bar_chart, "
            "st.plotly_chart (for waterfall/tornado charts via plotly.graph_objects), "
            "and st.altair_chart. You always propose the simplest solution that "
            "delivers the most executive value. You never move business logic "
            "into views.py."
        ),
        tools=[
            FileReadTool(file_path=_VIEWS),
            FileReadTool(file_path=_APP),
            FileReadTool(file_path=_CONSTANTS),
            FileReadTool(file_path=_CALCULATIONS),  # understand what data is available to visualise
        ],
        llm=_make_llm(model="claude-3-5-sonnet-20241022", temperature=0.3),
        verbose=True,
        allow_delegation=False,
    )
