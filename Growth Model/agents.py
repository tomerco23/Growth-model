"""
agents.py – CrewAI agent definitions for the Hospital Growth Model project.

Five specialized agents, each with a tightly scoped role that maps 1-to-1
to the modules they own:

  1. UI Agent           – Streamlit Expert      → views.py, app.py
  2. DB Agent           – Data Engineer         → data_loading.py
  3. Backend Agent      – Core Logic Expert     → calculations.py, report.py, utils.py
  4. Presentation Agent – Tech Communicator     → reads all, writes PROJECT_PRESENTATION.md
  5. QA Agent           – Senior QA & Debugger  → reviews all outputs

All agents use Claude via langchain-anthropic.
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

    Override the model by setting the CREWAI_MODEL env var, e.g.:
        CREWAI_MODEL=claude-sonnet-4-6 python crew_main.py
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
