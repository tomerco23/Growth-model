import json
from pathlib import Path

import streamlit as st

from constants import SESSION_STATE_DEFAULTS
from data_loading import load_growth_data
from views import show_edit_view, show_report_view

# ---------------------------------------------------------------------------
# CrewAI – optional import (graceful degradation if not installed)
# ---------------------------------------------------------------------------
try:
    from crew_main import WORKFLOW_OUTPUTS, WORKFLOWS, run_crew_workflow
    _CREW_AVAILABLE = True
except ImportError:
    _CREW_AVAILABLE = False

st.set_page_config(page_title="מודל צמיחה", layout="wide", page_icon="🏥")


def _init_session_state():
    for key, default_val in SESSION_STATE_DEFAULTS.items():
        if key not in st.session_state:
            # Use a copy for mutable defaults so instances don't share state
            st.session_state[key] = default_val.copy() if isinstance(default_val, (list, dict)) else default_val


def main():
    _init_session_state()

    with st.sidebar:
        p_name = st.text_input("שם הפרויקט", "מכון הלב החדש")

        with st.expander("💾 שמירה וטעינה"):
            # ── שמירה עם בורר תיקייה מקומי ──────────────────────────────
            if st.button("💾 שמור פרויקט...", use_container_width=True):
                try:
                    import tkinter as tk
                    from tkinter import filedialog
                    _root = tk.Tk()
                    _root.withdraw()
                    _root.wm_attributes('-topmost', True)
                    _save_path = filedialog.asksaveasfilename(
                        defaultextension=".json",
                        filetypes=[("קבצי JSON", "*.json"), ("כל הקבצים", "*.*")],
                        initialfile="מודל_צמיחה.json",
                        title="שמור פרויקט",
                    )
                    _root.destroy()
                    if _save_path:
                        with open(_save_path, "w", encoding="utf-8") as _f:
                            json.dump(
                                {
                                    "items": st.session_state.growth_items,
                                    "comments": st.session_state.general_comments,
                                },
                                _f,
                                ensure_ascii=False,
                                default=str,
                                indent=2,
                            )
                        st.success(f"✅ נשמר:\n`{_save_path}`")
                except Exception as _e:
                    st.error(f"❌ שגיאה בשמירה: {_e}")

            # ── טעינה ────────────────────────────────────────────────────
            upl = st.file_uploader("📂 טען", type=['json'])
            if upl:
                try:
                    d = json.load(upl)
                    st.session_state.growth_items = d.get("items", [])
                    st.session_state.general_comments = d.get("comments", "")
                    st.success("✅ נטען בהצלחה!")
                except (json.JSONDecodeError, Exception) as _e:
                    st.error(f"❌ הקובץ פגום ולא ניתן לטעינה: {_e}")

            # ── איפוס עם אישור ───────────────────────────────────────────
            if st.button("🗑️ איפוס", use_container_width=True):
                st.session_state['_confirm_reset'] = True

            if st.session_state.get('_confirm_reset'):
                st.warning("⚠️ פעולה זו תמחק את כל הנתונים. האם להמשיך?")
                _c1, _c2 = st.columns(2)
                if _c1.button("כן, אפס", type="primary", use_container_width=True):
                    st.session_state.growth_items = []
                    st.session_state['_confirm_reset'] = False
                    st.rerun()
                if _c2.button("ביטול", use_container_width=True):
                    st.session_state['_confirm_reset'] = False
                    st.rerun()

        with st.expander("📂 נתונים", expanded=True):
            f_in = st.file_uploader("קובץ HR", type=['xlsx'])
            f_ex = st.file_uploader("מחירונים", type=['xlsx', 'csv'], accept_multiple_files=True)
            if st.button("🧹 רענן"):
                st.cache_data.clear()
                st.rerun()

        with st.expander("🤖 ניתוח AI (CrewAI)"):
            if not _CREW_AVAILABLE:
                st.info(
                    "חבילת crewai אינה מותקנת.\n\n"
                    "להתקנה:\n"
                    "`pip install crewai crewai-tools langchain-anthropic`"
                )
            else:
                _WORKFLOW_LABELS = {
                    "docs":    "📄 תיעוד + QA",
                    "ui":      "🎨 שיפורי UI",
                    "db":      "🗄️ תכנית DB",
                    "backend": "⚙️ ביקורת Backend",
                }
                # ── קבצים שנוצרו בריצות קודמות ──────────────────────────
                _here = Path(__file__).parent
                _existing = [
                    fname
                    for wf_files in WORKFLOW_OUTPUTS.values()
                    for fname in wf_files
                    if (_here / fname).exists()
                ]
                if _existing:
                    st.caption("📂 קבצים שנוצרו:")
                    for _fname in _existing:
                        _fpath = _here / _fname
                        st.download_button(
                            f"📥 {_fname}",
                            _fpath.read_text(encoding="utf-8"),
                            _fname,
                            key=f"crew_dl_{_fname}",
                        )
                    st.divider()

                # ── הרצת workflow חדש ─────────────────────────────────────
                crew_key = st.text_input(
                    "🔑 Anthropic API Key",
                    type="password",
                    key="crew_api_key",
                )
                crew_wf = st.selectbox(
                    "בחר workflow",
                    list(WORKFLOWS.keys()),
                    format_func=lambda w: _WORKFLOW_LABELS.get(w, w),
                    key="crew_wf",
                )
                st.caption(
                    {
                        "docs":    "מייצר PROJECT_PRESENTATION.md + QA_REVIEW.md",
                        "ui":      "מייצר UI_IMPROVEMENT_NOTES.md",
                        "db":      "מייצר DB_MIGRATION_PLAN.md",
                        "backend": "מייצר BACKEND_AUDIT.md",
                    }.get(crew_wf, "")
                )
                if st.button("▶️ הפעל ניתוח", key="crew_run", use_container_width=True):
                    if not crew_key:
                        st.error("נדרש API Key להפעלה.")
                    else:
                        with st.spinner("מנתח... (עלול לקחת מספר דקות)"):
                            try:
                                run_crew_workflow(crew_wf, crew_key)
                                st.success("הניתוח הושלם בהצלחה!")
                                st.rerun()
                            except Exception as _e:
                                st.error(f"שגיאה בהרצת CrewAI: {_e}")

        with st.expander("⚙️ פרמטרים"):
            ovh = st.number_input("תקורה", value=29.0) / 100
            hmo = st.number_input("הנחת קופות", value=18.5) / 100
            vol = st.number_input("הנחת מחזור", value=1.9) / 100
            app = st.number_input("ערעורים", value=4.0) / 100
            cap = st.number_input("קאפ", value=37.5) / 100
            no_show = st.number_input("No-Show", value=0.0) / 100
            params = {
                "OVERHEAD_RATE": ovh,
                "HMO_DISCOUNT": hmo,
                "VOL_DISCOUNT": vol,
                "APPEALS_PROV": app,
                "NO_SHOW_RATE": no_show,
                "CAP_RATE_FACTOR": cap,
            }

    if not f_in:
        st.info("אנא טען קובץ פנימי (HR) כדי להתחיל.")
        st.stop()

    df_hr, df_srv_prices, df_srv_hier, h_hr, h_srv, k_hr, k_srv, msgs = load_growth_data(
        f_in, f_ex or []
    )

    if df_hr is None:
        st.error(msgs[0])
        st.stop()

    # ── K+L: הצג msgs + סיכום טעינה בסרגל הצד ─────────────────────────────
    with st.sidebar:
        with st.expander("📋 סיכום טעינה", expanded=False):
            for _msg in msgs:
                if "✅" in _msg:
                    st.success(_msg)
                elif "⚠️" in _msg:
                    st.warning(_msg)
                elif "❌" in _msg:
                    st.error(_msg)
                else:
                    st.info(_msg)
            # L – ספירת רשומות
            _srv_count = len(df_srv_prices) if df_srv_prices is not None else 0
            _hr_count  = len(df_hr)         if df_hr        is not None else 0
            _hier_count = len(df_srv_hier)  if df_srv_hier  is not None else 0
            st.caption(
                f"👥 תקנים: **{_hr_count:,}** | "
                f"📋 שירותים: **{_srv_count:,}** | "
                f"🗂️ היררכיה: **{_hier_count:,}**"
            )

    if st.session_state.view_mode == 'edit':
        show_edit_view(df_hr, df_srv_hier, df_srv_prices, h_hr, h_srv, k_hr, k_srv, params)
    else:
        show_report_view(p_name, params)


if __name__ == "__main__":
    main()
