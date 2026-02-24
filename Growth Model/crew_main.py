#!/usr/bin/env python3
"""
crew_main.py – Entry point for the Hospital Growth Model CrewAI system.

INITIAL WORKFLOW (default)
--------------------------
  Step 1 – Presentation Agent reads all 7 source files and writes
            PROJECT_PRESENTATION.md.
  Step 2 – QA Agent fact-checks every claim in the presentation against the
            actual source files and writes QA_REVIEW.md.

AVAILABLE WORKFLOWS
-------------------
  Run specific workflows by passing a --workflow argument:

    python crew_main.py                      # default: presentation + QA
    python crew_main.py --workflow docs      # same as default
    python crew_main.py --workflow ui        # UI improvement notes
    python crew_main.py --workflow db        # DB migration plan
    python crew_main.py --workflow backend   # Backend audit

ENVIRONMENT VARIABLES
---------------------
  ANTHROPIC_API_KEY  (required) – your Anthropic API key
  CREWAI_MODEL       (optional) – override the default model
                                  e.g. CREWAI_MODEL=claude-sonnet-4-6

USAGE EXAMPLES
--------------
  # Generate documentation and QA review
  ANTHROPIC_API_KEY=sk-ant-... python crew_main.py

  # Use a faster / cheaper model
  ANTHROPIC_API_KEY=sk-ant-... CREWAI_MODEL=claude-sonnet-4-6 python crew_main.py

  # Run just the DB migration planning workflow
  ANTHROPIC_API_KEY=sk-ant-... python crew_main.py --workflow db
"""

import argparse
import os
import sys
from pathlib import Path

from crewai import Crew, Process

# Local imports (same package directory)
from agents import (
    create_backend_agent,
    create_db_agent,
    create_presentation_agent,
    create_qa_agent,
    create_ui_agent,
)
from tasks import (
    create_backend_audit_task,
    create_db_migration_task,
    create_presentation_task,
    create_qa_review_task,
    create_ui_improvement_task,
)

_HERE = Path(__file__).parent


# ---------------------------------------------------------------------------
# Guard: require ANTHROPIC_API_KEY
# ---------------------------------------------------------------------------

def _check_api_key() -> None:
    if not os.getenv("ANTHROPIC_API_KEY"):
        print(
            "\n[ERROR] ANTHROPIC_API_KEY environment variable is not set.\n"
            "  Export it before running:\n\n"
            "    export ANTHROPIC_API_KEY='sk-ant-...'\n\n"
            "  Or prefix the command:\n\n"
            "    ANTHROPIC_API_KEY='sk-ant-...' python crew_main.py\n",
            file=sys.stderr,
        )
        sys.exit(1)


# ---------------------------------------------------------------------------
# Workflow builders
# ---------------------------------------------------------------------------

def run_docs_workflow() -> str:
    """
    Workflow: Documentation + QA
    ────────────────────────────
    1. Presentation Agent → PROJECT_PRESENTATION.md
    2. QA Agent           → QA_REVIEW.md  (uses presentation as context)

    Output files:
      Growth Model/PROJECT_PRESENTATION.md
      Growth Model/QA_REVIEW.md
    """
    print("\n[Workflow] Documentation + QA Review")
    print("  Output: PROJECT_PRESENTATION.md, QA_REVIEW.md\n")

    presentation_agent = create_presentation_agent()
    qa_agent           = create_qa_agent()

    presentation_task = create_presentation_task(presentation_agent)
    qa_task           = create_qa_review_task(qa_agent, presentation_task)

    crew = Crew(
        agents=[presentation_agent, qa_agent],
        tasks=[presentation_task, qa_task],
        process=Process.sequential,
        verbose=True,
    )
    return crew.kickoff()


def run_ui_workflow() -> str:
    """
    Workflow: UI Improvement Notes
    ──────────────────────────────
    UI Agent reads views.py and app.py and writes UI_IMPROVEMENT_NOTES.md.

    Output files:
      Growth Model/UI_IMPROVEMENT_NOTES.md
    """
    print("\n[Workflow] UI Improvement Notes")
    print("  Output: UI_IMPROVEMENT_NOTES.md\n")

    ui_agent = create_ui_agent()
    ui_task  = create_ui_improvement_task(ui_agent)

    crew = Crew(
        agents=[ui_agent],
        tasks=[ui_task],
        process=Process.sequential,
        verbose=True,
    )
    return crew.kickoff()


def run_db_workflow() -> str:
    """
    Workflow: DB Migration Plan
    ───────────────────────────
    DB Agent reads data_loading.py and writes DB_MIGRATION_PLAN.md with
    a full SQLite schema and migration guide.

    Output files:
      Growth Model/DB_MIGRATION_PLAN.md
    """
    print("\n[Workflow] DB Migration Plan")
    print("  Output: DB_MIGRATION_PLAN.md\n")

    db_agent = create_db_agent()
    db_task  = create_db_migration_task(db_agent)

    crew = Crew(
        agents=[db_agent],
        tasks=[db_task],
        process=Process.sequential,
        verbose=True,
    )
    return crew.kickoff()


def run_backend_workflow() -> str:
    """
    Workflow: Backend Audit
    ───────────────────────
    Backend Agent audits calculations.py, report.py, and utils.py for
    numerical accuracy, Pandas quality, and edge cases.

    Output files:
      Growth Model/BACKEND_AUDIT.md
    """
    print("\n[Workflow] Backend Audit")
    print("  Output: BACKEND_AUDIT.md\n")

    backend_agent = create_backend_agent()
    backend_task  = create_backend_audit_task(backend_agent)

    crew = Crew(
        agents=[backend_agent],
        tasks=[backend_task],
        process=Process.sequential,
        verbose=True,
    )
    return crew.kickoff()


# ---------------------------------------------------------------------------
# Workflow registry
# ---------------------------------------------------------------------------

WORKFLOWS = {
    "docs":    run_docs_workflow,
    "ui":      run_ui_workflow,
    "db":      run_db_workflow,
    "backend": run_backend_workflow,
}

WORKFLOW_OUTPUTS = {
    "docs":    ["PROJECT_PRESENTATION.md", "QA_REVIEW.md"],
    "ui":      ["UI_IMPROVEMENT_NOTES.md"],
    "db":      ["DB_MIGRATION_PLAN.md"],
    "backend": ["BACKEND_AUDIT.md"],
}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Hospital Growth Model – CrewAI multi-agent system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Available workflows:\n"
            "  docs    – Generate PROJECT_PRESENTATION.md + QA_REVIEW.md "
            "(default)\n"
            "  ui      – Generate UI_IMPROVEMENT_NOTES.md\n"
            "  db      – Generate DB_MIGRATION_PLAN.md\n"
            "  backend – Generate BACKEND_AUDIT.md\n"
        ),
    )
    parser.add_argument(
        "--workflow",
        choices=list(WORKFLOWS.keys()),
        default="docs",
        help="Which workflow to run (default: docs)",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    _check_api_key()
    args = _parse_args()

    model = os.getenv("CREWAI_MODEL", "claude-opus-4-6")
    print("=" * 65)
    print("  Hospital Growth Model – CrewAI Multi-Agent System")
    print("=" * 65)
    print(f"  Workflow : {args.workflow}")
    print(f"  LLM model: {model}")
    print(f"  Outputs  : {_HERE}")
    print("=" * 65)

    run_fn = WORKFLOWS[args.workflow]
    result = run_fn()

    output_files = WORKFLOW_OUTPUTS[args.workflow]
    print("\n" + "=" * 65)
    print(f"  Workflow '{args.workflow}' complete.")
    print("  Generated files:")
    for fname in output_files:
        fpath = _HERE / fname
        size  = f"{fpath.stat().st_size:,} bytes" if fpath.exists() else "not found"
        print(f"    • {fname}  ({size})")
    print("=" * 65)

    # Print final crew output to stdout for easy inspection
    if result:
        print("\n--- Final crew output ---\n")
        print(str(result))


# ---------------------------------------------------------------------------
# Programmatic API (used by app.py / Streamlit)
# ---------------------------------------------------------------------------

def run_crew_workflow(workflow_name: str, api_key: str) -> tuple[str, list]:
    """Run a workflow programmatically (e.g. called from Streamlit).

    Sets ANTHROPIC_API_KEY, executes the named workflow, and returns
    (result_str, list_of_generated_Paths).

    Args:
        workflow_name: One of the keys in WORKFLOWS ("docs", "ui", "db", "backend").
        api_key:       Anthropic API key to use for this run.

    Returns:
        Tuple of (crew result as string, list of Path objects for output files).
    """
    if workflow_name not in WORKFLOWS:
        raise ValueError(
            f"Unknown workflow '{workflow_name}'. Valid options: {list(WORKFLOWS)}"
        )
    os.environ["ANTHROPIC_API_KEY"] = api_key
    result = WORKFLOWS[workflow_name]()
    paths = [
        _HERE / fname
        for fname in WORKFLOW_OUTPUTS[workflow_name]
        if (_HERE / fname).exists()
    ]
    return str(result), paths


if __name__ == "__main__":
    main()
