import json

import streamlit as st

from constants import SESSION_STATE_DEFAULTS
from data_loading import load_growth_data
from views import show_edit_view, show_report_view

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
            st.download_button(
                "💾 שמור",
                json.dumps(
                    {"items": st.session_state.growth_items, "comments": st.session_state.general_comments},
                    default=str,
                ),
                "save.json",
            )
            upl = st.file_uploader("📂 טען", type=['json'])
            if upl:
                d = json.load(upl)
                st.session_state.growth_items = d.get("items", [])
                st.session_state.general_comments = d.get("comments", "")
                st.success("נטען!")
            if st.button("🗑️ איפוס"):
                st.session_state.growth_items = []
                st.rerun()

        with st.expander("📂 נתונים", expanded=True):
            f_in = st.file_uploader("קובץ HR", type=['xlsx'])
            f_ex = st.file_uploader("מחירונים", type=['xlsx', 'csv'], accept_multiple_files=True)
            if st.button("🧹 רענן"):
                st.cache_data.clear()
                st.rerun()

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

    if st.session_state.view_mode == 'edit':
        show_edit_view(df_hr, df_srv_hier, df_srv_prices, h_hr, h_srv, k_hr, k_srv, params)
    else:
        show_report_view(p_name, params)


if __name__ == "__main__":
    main()
