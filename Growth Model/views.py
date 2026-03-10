import copy
import io
import re

import numpy as np
import pandas as pd
import streamlit as st

try:
    import plotly.express as px
    import plotly.graph_objects as go
    _PLOTLY_AVAILABLE = True
except ImportError:
    _PLOTLY_AVAILABLE = False

from calculations import calculate_detailed_rows
from constants import CAT_MAP, Category
from report import create_hybrid_report_sheet, generate_verbal_analysis
from utils import format_number_str


# ---------------------------------------------------------------------------
# History helpers
# ---------------------------------------------------------------------------

def save_history():
    if 'history' not in st.session_state:
        st.session_state.history = []
    st.session_state.history.append(copy.deepcopy(st.session_state.growth_items))


def undo_last_action():
    if st.session_state.get('history'):
        st.session_state.growth_items = st.session_state.history.pop()
        st.session_state['has_unsaved_changes'] = False
        st.toast("הפעולה בוטלה בהצלחה", icon="↩️")
    else:
        st.toast("אין פעולות קודמות לביטול", icon="⚠️")


def _mark_unsaved():
    """Called by st.data_editor on_change. Sets unsaved flag once without causing repeated reruns."""
    if not st.session_state.get('has_unsaved_changes', False):
        st.session_state['has_unsaved_changes'] = True


def flush_editor_to_model():
    """Called by Save button. Syncs editor state → growth_items and clears the unsaved flag."""
    update_model_from_editor()
    st.session_state['has_unsaved_changes'] = False


# ---------------------------------------------------------------------------
# Filter widgets
# ---------------------------------------------------------------------------

def _get_opts(df: pd.DataFrame, col: str) -> list:
    if col not in df.columns:
        return ["הכל"]
    valid = [str(x) for x in df[col].unique() if x is not None and str(x).strip() not in ["-", "None", "nan"]]
    return ["הכל"] + sorted(valid)


def render_service_filters_cascading(df_hier: pd.DataFrame, df_prices: pd.DataFrame) -> list:
    if df_hier is None or df_hier.empty:
        if df_prices is not None and not df_prices.empty:
            return (df_prices['Code'].astype(str) + " - " + df_prices['Name']).tolist()
        return []

    c1, c2, c3, c4, c5 = st.columns(5)
    maarach = c1.selectbox("1. מערך", _get_opts(df_hier, 'Maarach'), key="srv_f1")
    d1 = df_hier if maarach == "הכל" else df_hier[df_hier['Maarach'] == maarach]

    agaf = c2.selectbox("2. אגף", _get_opts(d1, 'Agaf'), key="srv_f2")
    d2 = d1 if agaf == "הכל" else d1[d1['Agaf'] == agaf]

    hativa = c3.selectbox("3. חטיבה", _get_opts(d2, 'Hativa'), key="srv_f3")
    d3 = d2 if hativa == "הכל" else d2[d2['Hativa'] == hativa]

    dept = c4.selectbox("4. מחלקה", _get_opts(d3, 'Machleket Em'), key="srv_f4")
    d4 = d3 if dept == "הכל" else d3[d3['Machleket Em'] == dept]

    unit = c5.selectbox("5. יחידה", _get_opts(d4, 'Yahida'), key="srv_f5")
    d5 = d4 if unit == "הכל" else d4[d4['Yahida'] == unit]

    valid_codes = set(d5['Code'])
    df_filtered_prices = df_prices[df_prices['Code'].isin(valid_codes)]

    options = []
    if not df_filtered_prices.empty:
        options += (df_filtered_prices['Code'].astype(str) + " - " + df_filtered_prices['Name']).tolist()
    missing_codes = valid_codes - set(df_filtered_prices['Code'])
    if missing_codes:
        options += d5[d5['Code'].isin(missing_codes)]['Original_Label'].tolist()

    if not options:
        st.info("ℹ️ אין שירותים התואמים לסינון שנבחר. נסה לשנות את הפילטרים.")

    return sorted(list(set(options)))


def _get_hr_opts(d: pd.DataFrame, col: str) -> list:
    if col not in d.columns:
        return ["הכל"]
    return ["הכל"] + sorted([str(x) for x in d[col].unique() if x != "-"])


def render_hr_filters(df: pd.DataFrame, k: str = "def"):
    mode = st.radio("מקור תפקיד:", ["בחירה מהרשימה", "הזנה ידנית"], horizontal=True, key=f"{k}_mode")

    if mode == "הזנה ידנית":
        job = st.text_input("שם התפקיד", key=f"{k}_manual_job")
        cost = st.number_input(
            "עלות חודשית למעסיק (₪)", min_value=0.0, value=0.0, step=1000.0, format="%.0f", key=f"{k}_manual_cost"
        )
        return [job] if job else [], cost * 12

    if df is None or df.empty:
        return [], 0

    c1, c2, c3 = st.columns(3)
    sys_val = c1.selectbox("1. מערך", _get_hr_opts(df, 'Maarach'), key=f"{k}1")
    d1 = df if sys_val == "הכל" else df[df['Maarach'] == sys_val]

    div_val = c2.selectbox("2. אגף", _get_hr_opts(d1, 'Agaf'), key=f"{k}2")
    d2 = d1 if div_val == "הכל" else d1[d1['Agaf'] == div_val]

    hat_val = c3.selectbox("3. חטיבה", _get_hr_opts(d2, 'Hativa'), key=f"{k}3")
    d3 = d2 if hat_val == "הכל" else d2[d2['Hativa'] == hat_val]

    c4, c5, c6 = st.columns(3)
    dep_val = c4.selectbox("4. מחלקה", _get_hr_opts(d3, 'Machleket Em'), key=f"{k}4")
    d4 = d3 if dep_val == "הכל" else d3[d3['Machleket Em'] == dep_val]

    sec_val = c5.selectbox("5. סקטור", _get_hr_opts(d4, 'Sector'), key=f"{k}5")
    d5 = d4 if sec_val == "הכל" else d4[d4['Sector'] == sec_val]

    job_opts = d5['Job Desc'].unique() if 'Job Desc' in d5.columns else []
    jobs = c6.multiselect("6. תפקיד", job_opts, key=f"{k}6")

    default_cost_annual = 0.0
    if len(jobs) == 1 and 'Annual_Cost' in d5.columns:
        rows = d5[d5['Job Desc'] == jobs[0]]
        if not rows.empty:
            default_cost_annual = float(rows['Annual_Cost'].iloc[0])
            if default_cost_annual > 0:
                st.success(f"✅ שכר אותר בהצלחה מתוך הקובץ: ₪{default_cost_annual / 12:,.0f} לחודש")
            else:
                st.warning("⚠️ לא נמצאו נתוני שכר לתפקיד זה ביחידה המבוקשת. יש להזין עלות ידנית.")

    return jobs, default_cost_annual


# ---------------------------------------------------------------------------
# Item adders (callbacks)
# ---------------------------------------------------------------------------

def add_hr_item(df_hr: pd.DataFrame):
    roles = st.session_state.get('def6', [])
    if not roles:
        return
    save_history()

    fte = st.session_state.get('hr_fte', 1.0)
    user_cost_monthly = st.session_state.get('manpower_form_input', 0.0)
    sess = st.session_state.get('hr_sess', 0.0)
    s_pr = st.session_state.get('hr_sess_price', 0.0)
    p_opt = st.session_state.get('hr_opt', 100)
    p_pess = st.session_state.get('hr_pess', 100)

    for job_name in roles:
        final_cost_annual = user_cost_monthly * 12
        if df_hr is not None and not df_hr.empty:
            match_row = df_hr[df_hr['Job Desc'] == job_name]
            if not match_row.empty and 'Annual_Cost' in match_row.columns and len(roles) > 1:
                try:
                    final_cost_annual = float(match_row['Annual_Cost'].iloc[0])
                except (ValueError, TypeError):
                    pass

        st.session_state.growth_items.append({
            "Category": Category.MANPOWER,
            "Name": job_name,
            "Quantity": fte,
            "Unit_Cost": final_cost_annual,
            "Sessions": sess,
            "Sess_Price": s_pr,
            "Pct_Opt": p_opt,
            "Pct_Pess": p_pess,
            "Calc_Mode": "FTE",
        })

    st.session_state['def6'] = []
    st.toast(f"נוספו {len(roles)} משרות", icon="✅")


def add_srv_item(df_srv_prices: pd.DataFrame, params: dict):
    is_manual = st.session_state.get('srv_source_radio') == "הזנה ידנית"

    if is_manual:
        name = st.session_state.get('srv_man_name')
        price = st.session_state.get('srv_man_price', 0.0)
        if not name:
            st.toast("נא להזין שם שירות", icon="⚠️")
            return
        services_to_add = [(name, price)]
    else:
        services = st.session_state.get('srv_multi_select', [])
        if not services:
            return
        services_to_add = []
        for s in services:
            final_u_price = 0.0
            code_part = s.split(' - ')[0]
            if df_srv_prices is not None and not df_srv_prices.empty:
                match = df_srv_prices[df_srv_prices['Code'].astype(str) == str(code_part)]
                if not match.empty:
                    final_u_price = float(match['Tariff'].values[0])
            services_to_add.append((s, final_u_price))

    if not services_to_add:
        return

    save_history()
    priv = st.session_state.get('srv_priv', False)
    new_s = st.session_state.get('srv_new', False)
    p_opt = st.session_state.get('srv_opt', 100)
    p_pess = st.session_state.get('srv_pess', 80)
    sess_vol = st.session_state.get('srv_sess_vol', 0)
    sess_cost_val = st.session_state.get('srv_sess_cost', 0)
    g_y2 = st.session_state.get('srv_g2', 0.0)
    g_y3 = st.session_state.get('srv_g3', 0.0)
    g_y4 = st.session_state.get('srv_g4', 0.0)
    manual_no_show = None
    manual_discount = None
    if st.session_state.get('srv_override', False):
        manual_no_show = st.session_state.get('srv_ns', params['NO_SHOW_RATE'] * 100)
        manual_discount = st.session_state.get('srv_disc', 0.0)

    for s_name, s_price in services_to_add:
        st.session_state.growth_items.append({
            "Category": Category.REVENUE,
            "Name": s_name,
            "Quantity": st.session_state.get('srv_vol', 0.0),
            "Unit_Revenue": s_price,
            "Is_Private": priv,
            "Is_New": new_s,
            "Pct_Opt": p_opt,
            "Pct_Pess": p_pess,
            "Manual_No_Show": manual_no_show,
            "Manual_Discount_Pct": manual_discount,
            "Rev_Sess_Vol": sess_vol,
            "Rev_Sess_Cost": sess_cost_val,
            "Is_Monthly_Qty": False,
            "Growth_Y2": g_y2,
            "Growth_Y3": g_y3,
            "Growth_Y4": g_y4,
        })

    st.session_state['srv_multi_select'] = []
    st.session_state['srv_man_name'] = ""
    st.session_state['srv_man_price'] = 0.0
    st.toast(f"נוספו {len(services_to_add)} שירותים", icon="✅")


# ---------------------------------------------------------------------------
# Data-editor sync
# ---------------------------------------------------------------------------

def update_model_from_editor():
    state = st.session_state.get("data_editor_edit_mode", {})
    if not state:
        return

    df_map = st.session_state.get('latest_df_flat_mapping', {})
    edited = state.get("edited_rows", {})
    deleted = state.get("deleted_rows", [])

    if edited or deleted:
        save_history()

    for row_idx_str, changes in edited.items():
        row_idx = int(row_idx_str)
        if row_idx not in df_map:
            continue
        real_item_idx = df_map[row_idx]
        if not (0 <= real_item_idx < len(st.session_state.growth_items)):
            continue

        item = st.session_state.growth_items[real_item_idx]
        is_manpower = item['Category'] == Category.MANPOWER

        for col, new_val in changes.items():
            if col == "Delete":
                continue
            safe_val = new_val if new_val is not None else 0.0
            if col == "שם שירות":
                item['Name'] = str(safe_val)
            elif col == "כמות שירותים רגילים":
                item['Quantity'] = safe_val
            elif col == "Pct_Opt_Raw":
                item['Pct_Opt'] = safe_val
            elif col == "Pct_Pess_Raw":
                item['Pct_Pess'] = safe_val
            elif col == "Lifespan":
                item['Lifespan'] = safe_val
            elif col == "תעריף יחידה ברוטו":
                item['Unit_Revenue'] = safe_val
            elif col == "עלות לשירות":
                item['Unit_Cost'] = safe_val * 12 if is_manpower else safe_val
            elif col == "כמות שירותי ססיה":
                item['Sessions'] = safe_val / 12 if is_manpower else None
                if not is_manpower:
                    item['Rev_Sess_Vol'] = safe_val
            elif col == "עלות ססיה":
                if is_manpower:
                    item['Sess_Price'] = safe_val
                else:
                    item['Rev_Sess_Cost'] = safe_val

    rows_to_delete = [int(r) for r in deleted]
    for row_idx_str, changes in edited.items():
        if changes.get("Delete") is True:
            rows_to_delete.append(int(row_idx_str))

    if rows_to_delete:
        indices_to_remove = sorted(
            list(set(df_map[r] for r in rows_to_delete if r in df_map)),
            reverse=True,
        )
        for idx in indices_to_remove:
            if 0 <= idx < len(st.session_state.growth_items):
                del st.session_state.growth_items[idx]
        if indices_to_remove:
            st.toast(f"נמחקו {len(indices_to_remove)} שורות", icon="🗑️")


# ---------------------------------------------------------------------------
# Edit view
# ---------------------------------------------------------------------------

def show_edit_view(df_hr, df_srv_hier, df_srv_prices, h_hr, h_srv, k_hr, k_srv, params,
                   df_emp_counts=None):

    t1, t2, t3 = st.tabs(["🏗️ השקעה (CAPEX)", "💼 הוצאות תפעול (OPEX)", "💰 הכנסות (Revenue)"])

    with t1:
        st.subheader("הוספת השקעת הקמה וציוד")
        c1, c2, c3 = st.columns([3, 1, 1])
        desc = c1.text_input("תיאור ההשקעה", "שיפוץ")
        cost = c2.number_input("עלות (₪)", 0, 100_000_000, 500_000, 10_000, format="%d")
        qty = c3.number_input("כמות", 1, 100, 1)
        c4, c5, c6 = st.columns(3)
        p_opt = c4.number_input("תרחיש אופטימי (% מהעלות)", 0, 200, 100)
        p_pess = c5.number_input("תרחיש פסימי (% מהעלות)", 0, 200, 100)
        life = c6.number_input("שנות חיים (פחת)", 1, 50, 10)
        if st.button("➕ הוסף השקעה"):
            save_history()
            st.session_state.growth_items.append({
                "Category": Category.INVESTMENT, "Name": desc, "Quantity": qty,
                "Unit_Cost": cost, "Pct_Opt": p_opt, "Pct_Pess": p_pess,
                "Is_One_Time": True, "Lifespan": life,
            })
            st.success("נוסף!")

    with t2:
        st.subheader("הוספת הוצאות תפעול שוטפות")
        sub_t1, sub_t2 = st.tabs(["מצבת כוח אדם (HR)", "תפעול ואחזקה"])

        with sub_t1:
            calc_mode = st.radio(
                "בחר מודל חישוב עלות:",
                ["משרה שנתית (FTE)", "תורנות יומית (ערך יום)", "תורנות שעתית (לפי שעה)"],
                horizontal=True,
            )
            if calc_mode == "משרה שנתית (FTE)":
                roles, default_cost_hr = render_hr_filters(df_hr)
                current_selection_str = ",".join(roles) if roles else ""
                if 'last_selected_role' not in st.session_state:
                    st.session_state.last_selected_role = ""
                if len(roles) == 1 and current_selection_str != st.session_state.last_selected_role:
                    st.session_state.manpower_form_cost = float(default_cost_hr) / 12
                    st.session_state.last_selected_role = current_selection_str

                if roles:
                    if len(roles) == 1:
                        st.info(f"עלות שנתית למשרה (מחושבת): ₪{format_number_str(default_cost_hr)}")
                    else:
                        st.info(f"נבחרו {len(roles)} תפקידים. העלות תילקח לכל תפקיד בנפרד מקובץ הנתונים.")

                    c1, c2 = st.columns(2)
                    c1.number_input("תקנים (FTE) - לכל תפקיד שנבחר", 0.0, 50.0, 1.0, 0.1, key="hr_fte")
                    c2.number_input(
                        "עלות חודשית למעביד (ניתן לעריכה)",
                        value=float(st.session_state.manpower_form_cost),
                        format="%.0f",
                        key='manpower_form_input',
                        on_change=lambda: st.session_state.update({'manpower_form_cost': st.session_state.manpower_form_input}),
                    )
                    c2.number_input("ססיות בחודש", 0.0, 200.0, 0.0, key="hr_sess")
                    c2.number_input("מחיר ססיה", 0.0, 10000.0, 1000.0, format="%.0f", key="hr_sess_price")
                    c3, c4 = st.columns(2)
                    c3.number_input("תרחיש אופטימי (שכר %)", 0, 200, 100, key="hr_opt")
                    c4.number_input("תרחיש פסימי (שכר %)", 0, 200, 100, key="hr_pess")
                    st.button("➕ הוסף משרה/ות", on_click=add_hr_item, args=(df_hr,))

            elif calc_mode == "תורנות יומית (ערך יום)":
                st.caption("חישוב לפי: ערך יום * משקל * משמרות * (1 + העמסה) * (1 + מקדם תעסוקתי)")
                c1, c2, c3 = st.columns(3)
                name = c1.text_input("שם התורנות/תפקיד", "תורנות רופא מומחה")
                base_val = c2.number_input("ערך יום בסיס (₪)", value=470.0, step=10.0, format="%.0f")
                weight = c3.number_input("משקל התורנות (ערכי יום)", value=1.0, step=0.1)
                c4, c5, c6 = st.columns(3)
                qty_shifts = c4.number_input("כמות משמרות שנתית (לעובד)", value=100, step=1)
                overhead = c5.number_input("אחוז העמסת מעביד (%)", value=0.0, step=1.0) / 100.0
                occ_bonus = c6.number_input("מקדם תעסוקתי/בונוס (%)", value=0.0, step=1.0) / 100.0
                c7, _ = st.columns(2)
                num_employees = c7.number_input("מספר עובדים (כפילות)", value=1, min_value=1, step=1)
                single_cost = base_val * weight * qty_shifts * (1 + overhead) * (1 + occ_bonus)
                total_calc = single_cost * num_employees
                st.info(f"💰 עלות לעובד יחיד: **₪{format_number_str(single_cost)}** | סה\"כ ({num_employees} עובדים): **₪{format_number_str(total_calc)}**")
                if st.button("➕ הוסף תורנות יומית"):
                    save_history()
                    st.session_state.growth_items.append({
                        "Category": Category.MANPOWER, "Name": f"{name} (מודל יומי)",
                        "Quantity": float(num_employees), "Unit_Cost": single_cost,
                        "Sessions": 0, "Sess_Price": 0, "Pct_Opt": 100, "Pct_Pess": 100,
                        "Calc_Mode": "Daily", "Base_Value": base_val, "Weight": weight,
                        "Qty_Shifts_Per_Emp": qty_shifts, "Overhead": overhead, "Occ_Bonus": occ_bonus,
                    })
                    st.success("נוסף בהצלחה!")

            elif calc_mode == "תורנות שעתית (לפי שעה)":
                st.caption("חישוב לפי: עלות שעה * שעות * משמרות * (1 + תוספת)")
                c1, c2, c3 = st.columns(3)
                name = c1.text_input("שם המשמרת/תפקיד", "אחות ערב")
                hour_cost = c2.number_input("עלות מעביד לשעה (₪)", value=100.0, step=1.0, format="%.0f")
                hours_per_shift = c3.number_input("שעות במשמרת", value=8.0, step=0.5)
                c4, c5 = st.columns(2)
                qty_shifts = c4.number_input("כמות משמרות שנתית (לעובד)", value=100, step=1)
                extra_pct = c5.number_input("תוספת מיוחדת (%)", value=0.0, step=1.0) / 100.0
                c6, _ = st.columns(2)
                num_employees = c6.number_input("מספר עובדים (כפילות)", value=1, min_value=1, step=1, key="hr_hourly_qty")
                single_cost = hour_cost * hours_per_shift * qty_shifts * (1 + extra_pct)
                total_calc = single_cost * num_employees
                st.info(f"💰 עלות לעובד יחיד: **₪{format_number_str(single_cost)}** | סה\"כ ({num_employees} עובדים): **₪{format_number_str(total_calc)}**")
                if st.button("➕ הוסף משמרות שעתיות"):
                    save_history()
                    st.session_state.growth_items.append({
                        "Category": Category.MANPOWER, "Name": f"{name} (מודל שעתי)",
                        "Quantity": float(num_employees), "Unit_Cost": single_cost,
                        "Sessions": 0, "Sess_Price": 0, "Pct_Opt": 100, "Pct_Pess": 100,
                        "Calc_Mode": "Hourly", "Hour_Cost": hour_cost,
                        "Hours_Per_Shift": hours_per_shift, "Qty_Shifts_Per_Emp": qty_shifts,
                        "Occ_Bonus": extra_pct,
                    })
                    st.success("נוסף בהצלחה!")

        with sub_t2:
            type_op = st.radio("סוג הוצאה:", ["שוטף (שנתי)", "חד-פעמי (הקמה)"], horizontal=True)
            c1, c2, c3 = st.columns([3, 1, 1])
            op_desc = c1.text_input("תיאור", "אחזקה שנתית")
            op_cost = c2.number_input("עלות (₪)", 0, 10_000_000, 50_000)
            qty_op = c3.number_input("כמות/יחידות", 1, 100, 1, key="q_op")
            c3_b, c4_b = st.columns(2)
            p_opt = c3_b.number_input("תרחיש אופטימי (תפעול %)", 0, 200, 100, key="op_o")
            p_pess = c4_b.number_input("תרחיש פסימי (תפעול %)", 0, 200, 100, key="op_p")
            if st.button("➕ הוסף הוצאה"):
                save_history()
                st.session_state.growth_items.append({
                    "Category": Category.OPERATION, "Name": op_desc,
                    "Quantity": qty_op, "Unit_Cost": op_cost,
                    "Pct_Opt": p_opt, "Pct_Pess": p_pess,
                    "Is_One_Time": (type_op == "חד-פעמי (הקמה)"),
                })
                st.success("נוסף!")

    with t3:
        st.subheader("הוספת הכנסות משירותים")
        srv_source = st.radio("מקור השירות:", ["בחירה מהרשימה", "הזנה ידנית"], horizontal=True, key="srv_source_radio")

        if srv_source == "בחירה מהרשימה":
            srv_opts = render_service_filters_cascading(df_srv_hier, df_srv_prices)
            selected_services_list = st.multiselect(
                "בחר שירות (ניתן לבחור מרובים)", srv_opts,
                placeholder="התחל להקליד...", key="srv_multi_select",
            )
            if selected_services_list and len(selected_services_list) == 1:
                code = selected_services_list[0].split(' - ')[0]
                match = df_srv_prices[df_srv_prices['Code'].astype(str) == str(code)]
                if not match.empty:
                    st.info(f"💰 **תעריף ברוטו ליחידה:** ₪{format_number_str(float(match['Tariff'].values[0]))}")
        else:
            c_man1, c_man2 = st.columns([3, 1])
            c_man1.text_input("שם השירות", key="srv_man_name")
            c_man2.number_input("תעריף ליחידה (₪)", min_value=0.0, value=0.0, step=10.0, format="%.0f", key="srv_man_price")

        st.divider()
        c1, c2 = st.columns(2)
        c1.number_input("כמות שנתית (זימונים) - לכל שירות שנבחר", 0.0, 1_000_000.0, 1000.0, key="srv_vol")
        c2.checkbox("פרטי?", key="srv_priv")
        c2.checkbox("חדש?", key="srv_new")
        c3, c4 = st.columns(2)
        c3.number_input("תרחיש אופטימי (ביקוש %)", 0, 200, 100, key="srv_opt")
        c4.number_input("תרחיש פסימי (ביקוש %)", 0, 200, 80, key="srv_pess")
        st.markdown("**הגדרת ססיות לשירות (אופציונלי - למידע בלבד):**")
        c_sess_v, c_sess_p = st.columns(2)
        c_sess_v.number_input("כמות ססיות נדרשת לשירות זה (שנתי)", 0, 10000, 0, key="srv_sess_vol")
        c_sess_p.number_input("עלות ססיה", 0, 10000, 0, format="%.0f", key="srv_sess_cost")
        st.markdown("**תחזית צמיחה (לעומת שנה קודמת):**")
        col_g2, col_g3, col_g4 = st.columns(3)
        col_g2.number_input("שנה 2 (לעומת שנה 1) %", value=0.0, step=1.0, key="srv_g2")
        col_g3.number_input("שנה 3 (לעומת שנה 2) %", value=0.0, step=1.0, key="srv_g3")
        col_g4.number_input("שנה 4 (לעומת שנה 3) %", value=0.0, step=1.0, key="srv_g4")
        override_defaults = st.checkbox("הגדרת הנחות/No-Show מותאמת אישית", key="srv_override")
        if override_defaults:
            col_ns, col_disc = st.columns(2)
            col_ns.number_input("אחוז No-Show (%)", min_value=-100.0, max_value=100.0, value=params['NO_SHOW_RATE'] * 100, step=1.0, key="srv_ns")
            combined_discount = (1 - ((1 - params['HMO_DISCOUNT']) * (1 - params['VOL_DISCOUNT']) * (1 - params['APPEALS_PROV']) * (1 - params['NO_SHOW_RATE']))) * 100
            col_disc.number_input("אחוז הנחות כולל (%)", min_value=-100.0, max_value=100.0, value=combined_discount, step=1.0, key="srv_disc")
        st.button("➕ הוסף הכנסה/ות", on_click=add_srv_item, args=(df_srv_prices, params))

        st.divider()
        with st.expander("🔬 כלי חיזוי תפוקה שולית – בחר שירות ועובד"):
            show_marginal_productivity_tool(h_srv, df_emp_counts)

    if st.session_state.growth_items:
        with st.spinner("מחשב..."):
            df_flat, capex, opex, rev, profit_b, profit_opt, profit_pess, roi = calculate_detailed_rows(
                st.session_state.growth_items, params
            )
        st.markdown("### 🛠️ עריכה ומחיקה")

        editable_df = df_flat[df_flat['Row_Type'] == 'Main'].copy()
        if 'Delete' not in editable_df.columns:
            editable_df.insert(0, 'Delete', False)

        manpower_mask = editable_df['Category_Heb'] == CAT_MAP[Category.MANPOWER]
        editable_df.loc[manpower_mask, 'עלות לשירות'] = editable_df.loc[manpower_mask, 'עלות לשירות'] / 12
        editable_df.reset_index(drop=True, inplace=True)
        st.session_state['latest_df_flat_mapping'] = dict(zip(editable_df.index, editable_df['Item_Index']))

        cols_order = [
            'Delete', 'Item_Index', 'Category_Heb', 'שם שירות',
            'כמות שירותים רגילים', 'עלות לשירות', 'כמות שירותי ססיה',
            'עלות ססיה', 'תעריף יחידה ברוטו', 'Pct_Opt_Raw', 'Pct_Pess_Raw',
        ]
        if 'Lifespan' in df_flat.columns:
            cols_order.append('Lifespan')

        with st.form("edit_delete_form", clear_on_submit=False):
            st.data_editor(
                editable_df[cols_order],
                column_config={
                    "Delete": st.column_config.CheckboxColumn("מחק?"),
                    "Item_Index": st.column_config.Column(disabled=True, width=None),
                    "Category_Heb": st.column_config.Column("קטגוריה", disabled=True),
                    "שם שירות": st.column_config.TextColumn("שם הפריט", width="large"),
                    "כמות שירותים רגילים": st.column_config.NumberColumn("כמות / FTE", format="%.2f"),
                    "עלות לשירות": st.column_config.NumberColumn("עלות יחידה (₪)", format="%.0f"),
                    "כמות שירותי ססיה": st.column_config.NumberColumn("כמות ססיה (שנתי)", format="%.0f"),
                    "עלות ססיה": st.column_config.NumberColumn("עלות ססיה (₪)", format="%.0f"),
                    "תעריף יחידה ברוטו": st.column_config.NumberColumn("תעריף ברוטו (₪)", format="%.0f"),
                    "Pct_Opt_Raw": st.column_config.NumberColumn("אופטימי %", format="%d%%"),
                    "Pct_Pess_Raw": st.column_config.NumberColumn("פסימי %", format="%d%%"),
                    "Lifespan": st.column_config.NumberColumn("שנות חיים", format="%d"),
                },
                hide_index=True,
                use_container_width=True,
                key="data_editor_edit_mode",
                num_rows="fixed",
                height=600,
            )
            if st.form_submit_button("💾 שמור שינויים  (Enter ↵)", type="primary", use_container_width=True):
                flush_editor_to_model()

        if st.button("↩️ ביטול פעולה אחרונה", use_container_width=True):
            undo_last_action()

    st.divider()
    if st.button("📄 עבור לתצוגה מקדימה של הדו\"ח", type="primary", use_container_width=True):
        _editor_state = st.session_state.get("data_editor_edit_mode", {})
        if _editor_state.get("edited_rows") or _editor_state.get("deleted_rows"):
            flush_editor_to_model()
        st.session_state.view_mode = 'report'
        st.rerun()


# ---------------------------------------------------------------------------
# Marginal-productivity forecast tool
# ---------------------------------------------------------------------------

def show_marginal_productivity_tool(h_srv: pd.DataFrame, df_emp_counts: pd.DataFrame):
    """
    כלי חיזוי תפוקה שולית אינטראקטיבי.

    המשתמש בוחר שירות (מונה) + סוג עובד (מכנה).
    המערכת מחשבת תפוקה שולית היסטורית וחיזוי לגיוס.
    """
    if h_srv is None or h_srv.empty or df_emp_counts is None or df_emp_counts.empty:
        st.info("⚠️ נדרשים נתוני DB_Service_count ו-DB_HR_Costs בקובץ HR כדי להפעיל כלי זה.")
        return

    st.markdown(
        "בחר **שירות** (מונה) ו**סוג עובד** (מכנה) – "
        "המערכת תחשב תפוקה שולית היסטורית ותחזית לגיוס עובדים."
    )

    col_a, col_b = st.columns(2)

    # ── שלב 1: בחירת שירות ────────────────────────────────────────────────
    with col_a:
        st.markdown("**שלב 1 – שירות**")
        svc_labels = sorted(
            h_srv['Original_Label'].dropna().astype(str).unique().tolist()
        )
        if not svc_labels:
            st.warning("לא נמצאו שירותים ב-DB_Service_count.")
            return
        sel_svc = st.selectbox(
            "שירות", svc_labels,
            key="mp_tool_service", label_visibility="collapsed",
        )

    # ── שלב 2: בחירת סוג עובד ─────────────────────────────────────────────
    with col_b:
        st.markdown("**שלב 2 – סוג עובד**")
        if 'Job Desc' not in df_emp_counts.columns:
            st.warning("לא נמצאה עמודת 'Job Desc' בנתוני העובדים.")
            return
        job_opts = sorted(
            df_emp_counts['Job Desc'].dropna().astype(str).unique().tolist()
        )
        sel_job = st.selectbox(
            "סוג עובד", job_opts,
            key="mp_tool_job", label_visibility="collapsed",
        )

    if not sel_svc or not sel_job:
        return

    # ── חישוב היסטורי ─────────────────────────────────────────────────────
    # מונה: סך שירותים לשירות הנבחר (כל החודשים)
    srv_rows = h_srv[h_srv['Original_Label'] == sel_svc]
    total_services = float(
        pd.to_numeric(srv_rows['Value'], errors='coerce').fillna(0).sum()
    )

    # מכנה: סך חודשי-עובד לסוג העובד שנבחר
    emp_rows = df_emp_counts[df_emp_counts['Job Desc'] == sel_job]
    total_emp_months = float(emp_rows['Total_Employee_Months'].sum()) if not emp_rows.empty else 0.0
    avg_monthly_emp  = float(emp_rows['Avg_Monthly_Employees'].sum()) if not emp_rows.empty else 0.0
    months_count     = int(emp_rows['Months_Count'].iloc[0])          if not emp_rows.empty else 0

    productivity = round(total_services / total_emp_months, 4) if total_emp_months > 0 else 0.0

    # ── הצגת נתונים היסטוריים ─────────────────────────────────────────────
    st.divider()
    st.markdown("**📊 נתונים היסטוריים:**")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric(
        "שירותים שניתנו (כל התקופה)",
        f"{total_services:,.0f}",
    )
    m2.metric(
        "חודשי-עובד (סוג זה)",
        f"{total_emp_months:,.1f}",
        help=f"ממוצע {avg_monthly_emp:,.1f} עובד/ים × {months_count} חודשים",
    )
    m3.metric(
        "ממוצע עובדים/חודש",
        f"{avg_monthly_emp:,.1f}",
    )
    m4.metric(
        "תפוקה שולית",
        f"{productivity:,.2f}",
        help="שירותים לחודשי-עובד = שירותים ÷ (עובדים × חודשים)",
    )

    # ── חיזוי ─────────────────────────────────────────────────────────────
    st.markdown("**🔮 חיזוי: כמה שירותים יתרמו עובדים נוספים?**")
    fc1, fc2 = st.columns(2)
    n_emp = fc1.number_input(
        "מספר עובדים לגיוס",
        min_value=0.1, max_value=500.0, value=1.0, step=0.5,
        format="%.1f", key="mp_tool_n_emp",
    )
    m_months_fc = fc2.number_input(
        "מספר חודשי פעילות",
        min_value=1, max_value=120, value=12, step=1,
        key="mp_tool_months",
    )

    if productivity > 0:
        forecast_services = n_emp * m_months_fc * productivity
        st.success(
            f"📈 **תחזית:**  "
            f"{n_emp:,.1f} עובד/ים × {m_months_fc} חודשים "
            f"× {productivity:,.2f} שירותים/חודשי-עובד "
            f"= **{forecast_services:,.0f} שירותים נוספים**"
        )
    else:
        st.warning(
            "⚠️ לא ניתן לחשב תחזית – "
            "לא נמצאו חודשי-עובד לסוג שנבחר בנתוני DB_HR_Costs."
        )


# ---------------------------------------------------------------------------
# Report view
# ---------------------------------------------------------------------------

def show_report_view(  # noqa: C901
    p_name: str,
    params: dict,
    h_srv: pd.DataFrame = None,
    df_emp_counts: pd.DataFrame = None,
):
    st.header(f"📊 דו\"ח מסכם: {p_name}")

    if not st.session_state.growth_items:
        st.warning("אין נתונים להצגה.")
        st.button("✏️ חזור לעריכה", on_click=lambda: st.session_state.update({'view_mode': 'edit'}))
        return

    # ── סימולטור מנהלים (ללא שינוי) ────────────────────────────────────────
    with st.expander("🎛️ סימולטור מנהלים", expanded=True):
        st.info("שינוי הערכים כאן משפיע רק על התצוגה.")
        tabs_sim = st.tabs(["💰 הכנסות", "👨‍⚕️ כוח אדם", "🏗️ השקעות"])

        with tabs_sim[0]:
            for i, item in enumerate(st.session_state.growth_items):
                if item['Category'] == Category.REVENUE:
                    st.session_state.growth_items[i]['Quantity'] = st.slider(
                        f"{item['Name']}", 0, int(item['Quantity'] * 2) + 100,
                        int(item['Quantity']), 10, key=f"s_r_{i}",
                    )
        with tabs_sim[1]:
            for i, item in enumerate(st.session_state.growth_items):
                if item['Category'] == Category.MANPOWER:
                    st.session_state.growth_items[i]['Quantity'] = st.slider(
                        f"{item['Name']}", 0.0, 20.0, float(item['Quantity']), 0.1, key=f"s_m_{i}",
                    )
        with tabs_sim[2]:
            for i, item in enumerate(st.session_state.growth_items):
                if item['Category'] == Category.INVESTMENT:
                    st.session_state.growth_items[i]['Unit_Cost'] = st.slider(
                        f"{item['Name']}", 0, int(item['Unit_Cost'] * 2) + 1000,
                        int(item['Unit_Cost']), 1000, key=f"s_i_{i}",
                    )

    # ── חישוב ───────────────────────────────────────────────────────────────
    df_flat, capex, opex, rev, profit_b, profit_opt, profit_pess, roi = calculate_detailed_rows(
        st.session_state.growth_items, params
    )

    # נגזרות לתרחיש קאפ
    df_rev_all  = df_flat[(df_flat['קטגוריה'] == Category.REVENUE) & (df_flat['Row_Type'] == 'Main')]
    df_op_only  = df_flat[(df_flat['קטגוריה'] == Category.OPERATION) & (df_flat['סוג'] != 'השקעה חד-פעמית') & (df_flat['Row_Type'] != 'SessionInfo')]
    df_hr_only  = df_flat[df_flat['קטגוריה'] == Category.MANPOWER]
    total_rev_cap  = df_rev_all['סה"כ אחרי קאפ'].sum()
    total_op_exp   = abs(df_op_only['סה"כ נטו לכיס'].sum())
    total_hr_exp   = abs(df_hr_only['סה"כ נטו לכיס'].sum())
    op_profit_cap  = total_rev_cap - total_op_exp - total_hr_exp
    roi_cap        = (capex / op_profit_cap) if op_profit_cap > 0 else 0
    gross_total    = df_rev_all['סה"כ ברוטו'].sum()

    # ── A+G: Hero Banner + ניתוח מילולי ────────────────────────────────────
    verbal = generate_verbal_analysis(profit_b, profit_opt, profit_pess, capex, opex, rev, roi, df_flat)
    if profit_pess > 0:
        st.success(verbal)
    elif profit_b > 0:
        st.warning(verbal)
    else:
        st.error(verbal)

    # ── B: 4 KPI Cards ──────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    col1.metric(
        "הכנסות נטו לכיס",
        f"₪{format_number_str(rev)}",
        delta=f"ברוטו ₪{format_number_str(gross_total)}",
        delta_color="off",
    )
    col2.metric(
        "רווח תפעולי",
        f"₪{format_number_str(profit_b)}",
        delta=f"פסימי ₪{format_number_str(profit_pess)}",
        delta_color="normal" if profit_pess >= 0 else "inverse",
    )
    col3.metric(
        "רווח כולל (בניכוי השקעה)",
        f"₪{format_number_str(profit_b - capex)}",
        delta=f"CAPEX ₪{format_number_str(capex)}",
        delta_color="off",
    )
    _roi_delta = "מצוין (< 3 שנים)" if 0 < roi < 3 else ("גבוה" if roi >= 3 else None)
    col4.metric(
        "ROI",
        f"{roi:.1f} שנים" if roi > 0 else "—",
        delta=_roi_delta,
        delta_color="normal" if 0 < roi < 3 else ("inverse" if roi >= 3 else "off"),
    )

    st.divider()

    # ── C+D: גרפים – השוואת תרחישים + תחזית רב-שנתית ─────────────────────
    if _PLOTLY_AVAILABLE:
        chart_l, chart_r = st.columns(2)

        with chart_l:
            # C – Scenario comparison bar
            fig_sc = go.Figure(data=[
                go.Bar(name='פסימי',   x=['רווח תפעולי'], y=[profit_pess], marker_color='#e74c3c'),
                go.Bar(name='בסיס',    x=['רווח תפעולי'], y=[profit_b],    marker_color='#3498db'),
                go.Bar(name='אופטימי', x=['רווח תפעולי'], y=[profit_opt],  marker_color='#2ecc71'),
            ])
            fig_sc.add_hline(y=0, line_dash="dash", line_color="black",
                             annotation_text="נקודת איזון", annotation_position="top right")
            fig_sc.update_layout(
                title="השוואת תרחישים", barmode='group', height=340,
                yaxis_title="₪", xaxis_title="",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )
            st.plotly_chart(fig_sc, use_container_width=True)

        with chart_r:
            # D – Multi-year projection
            df_non_info = df_flat[df_flat['Row_Type'] != 'SessionInfo']
            _y1 = profit_b
            _y2 = df_non_info['Net_Y2'].sum()
            _y3 = df_non_info['Net_Y3'].sum()
            _y4 = df_non_info['Net_Y4'].sum()
            df_years = pd.DataFrame({
                'שנה': ['שנה 1', 'שנה 2', 'שנה 3', 'שנה 4'],
                'רווח תפעולי': [_y1, _y2, _y3, _y4],
            })
            fig_yr = px.line(
                df_years, x='שנה', y='רווח תפעולי',
                title='תחזית רב-שנתית', markers=True, height=340,
            )
            fig_yr.add_hline(y=0, line_dash="dash", line_color="red",
                             annotation_text="נקודת איזון", annotation_position="top right")
            fig_yr.update_traces(line_color='#3498db', marker_size=10)
            fig_yr.update_layout(yaxis_title="₪")
            st.plotly_chart(fig_yr, use_container_width=True)
    else:
        st.info("💡 התקן `plotly` כדי לראות גרפים: `pip install plotly`")

    st.divider()

    # ── H: פירוט הכנסות – "כל הדרך" ────────────────────────────────────────
    if not df_rev_all.empty:
        st.subheader("💰 פירוט הכנסות")

        _rev_col_map = {
            'שם שירות':                  'שירות',
            'כמות שירותים רגילים':       'כמות',
            'תעריף יחידה ברוטו':         'תעריף ברוטו',
            'תעריף יחידה אחרי הנחות':    'תעריף נטו',
            'תעריף יחידה תחת cap':       'תעריף קאפ',
            'סה"כ ברוטו':               'סה"כ ברוטו',
            'סה"כ אחרי הנחות':          'סה"כ נטו',
            'סה"כ אחרי קאפ':            'סה"כ קאפ',
            'עלות תקורה':               'תקורה',
            'סה"כ נטו לכיס':            'נטו לכיס',
            'תרחיש אופטימי':            'אופטימי',
            'תרחיש פסימי':              'פסימי',
        }
        _rev_cols_exist = [c for c in _rev_col_map if c in df_rev_all.columns]
        rev_display = df_rev_all[_rev_cols_exist].rename(columns=_rev_col_map)

        _curr_fmt = "₪%,.0f"
        _col_cfg = {
            'כמות':              st.column_config.NumberColumn(format="%.2f"),
            'תעריף ברוטו':       st.column_config.NumberColumn(format=_curr_fmt),
            'תעריף נטו':         st.column_config.NumberColumn(format=_curr_fmt),
            'תעריף קאפ':         st.column_config.NumberColumn(format=_curr_fmt),
            'סה"כ ברוטו':        st.column_config.NumberColumn(format=_curr_fmt),
            'סה"כ נטו':          st.column_config.NumberColumn(format=_curr_fmt),
            'סה"כ קאפ':          st.column_config.NumberColumn(format=_curr_fmt),
            'תקורה':             st.column_config.NumberColumn(format=_curr_fmt),
            'נטו לכיס':          st.column_config.NumberColumn(format=_curr_fmt),
            'אופטימי':           st.column_config.NumberColumn(format=_curr_fmt),
            'פסימי':             st.column_config.NumberColumn(format=_curr_fmt),
        }
        st.dataframe(rev_display, use_container_width=True, hide_index=True,
                     column_config={k: v for k, v in _col_cfg.items() if k in rev_display.columns})

        # E – Revenue bar chart (ברוטו vs נטו)
        if _PLOTLY_AVAILABLE and len(df_rev_all) > 0:
            _bar_df = df_rev_all[['שם שירות', 'סה"כ ברוטו', 'סה"כ נטו לכיס']].copy()
            _bar_df = _bar_df.sort_values('סה"כ נטו לכיס', ascending=True)
            fig_rev = go.Figure()
            fig_rev.add_trace(go.Bar(
                name='ברוטו', y=_bar_df['שם שירות'], x=_bar_df['סה"כ ברוטו'],
                orientation='h', marker_color='#5dade2',
            ))
            fig_rev.add_trace(go.Bar(
                name='נטו לכיס', y=_bar_df['שם שירות'], x=_bar_df['סה"כ נטו לכיס'],
                orientation='h', marker_color='#1a8a3c',
            ))
            fig_rev.update_layout(
                title='הכנסות: ברוטו vs נטו לכיס', barmode='group',
                height=max(280, len(df_rev_all) * 55),
                xaxis_title='₪', yaxis_title='',
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
            )
            st.plotly_chart(fig_rev, use_container_width=True)

    # ── H2: NET vs CAP – השוואת תרחיש נטו מול קאפ ─────────────────────────
    st.subheader("📊 נטו מול קאפ")
    h2_l, h2_r = st.columns(2)
    with h2_l:
        st.markdown("**תרחיש נטו (סטנדרט)**")
        h2_l.metric("רווח תפעולי", f"₪{format_number_str(profit_b)}")
        h2_l.metric("ROI", f"{roi:.1f} שנים" if roi > 0 else "—")
        _rec_net = "✅ מומלץ" if profit_pess > 0 else ("⚠️ מותנה" if profit_b > 0 else "🛑 לא מומלץ")
        h2_l.info(f"המלצה: **{_rec_net}**")
    with h2_r:
        st.markdown("**תרחיש קאפ (תקרה)**")
        h2_r.metric("רווח תפעולי", f"₪{format_number_str(op_profit_cap)}")
        h2_r.metric("ROI", f"{roi_cap:.1f} שנים" if roi_cap > 0 else "—")
        _rec_cap = "✅ מומלץ" if (op_profit_cap - capex) > 0 else "🛑 לא מומלץ"
        h2_r.info(f"המלצה: **{_rec_cap}**")

    st.divider()

    # ── F+הוצאות: דונאט + טבלה ──────────────────────────────────────────────
    df_exp = df_flat[
        df_flat['קטגוריה'].isin([Category.MANPOWER, Category.OPERATION]) &
        (df_flat['סוג'] != 'השקעה חד-פעמית')
    ]
    if not df_exp.empty:
        st.subheader("📉 פירוט הוצאות")
        exp_l, exp_r = st.columns([1, 2])
        with exp_l:
            if _PLOTLY_AVAILABLE:
                _exp_grp = df_exp.groupby('Category_Heb')['סה"כ נטו לכיס'].sum().abs()
                fig_donut = px.pie(
                    values=_exp_grp.values, names=_exp_grp.index,
                    title='פירוט הוצאות', hole=0.42, height=300,
                )
                fig_donut.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig_donut, use_container_width=True)
        with exp_r:
            _exp_cols = ['Category_Heb', 'שם שירות', 'כמות שירותים רגילים',
                         'עלות לשירות', 'סה"כ נטו לכיס', 'תרחיש אופטימי', 'תרחיש פסימי']
            _exp_cols_exist = [c for c in _exp_cols if c in df_exp.columns]
            st.dataframe(df_exp[_exp_cols_exist], use_container_width=True, hide_index=True)

    # ── השקעות ─────────────────────────────────────────────────────────────
    df_inv = df_flat[df_flat['סוג'] == 'השקעה חד-פעמית']
    if not df_inv.empty:
        st.subheader("🏗️ השקעות (CAPEX)")
        _inv_cols = ['שם שירות', 'כמות שירותים רגילים', 'עלות לשירות', 'Lifespan', 'סה"כ נטו לכיס']
        _inv_cols_exist = [c for c in _inv_cols if c in df_inv.columns]
        st.dataframe(df_inv[_inv_cols_exist], use_container_width=True, hide_index=True)

    # ── הערות + ייצוא Excel ─────────────────────────────────────────────────
    st.divider()
    c1, c2 = st.columns([2, 1])
    with c1:
        st.text_area("הערות הכלכלן:", key='general_comments')

    with c2:
        clean_filename = re.sub(r'[\\/*?:"<>|]', "", p_name).strip() or "Project_Report"
        df_safe = df_flat.copy().fillna(0).replace([np.inf, -np.inf], 0)
        excel_data = None
        try:
            buf = io.BytesIO()
            writer = pd.ExcelWriter(buf, engine='xlsxwriter')
            create_hybrid_report_sheet(
                writer, df_safe, p_name, capex, opex, rev, profit_b, profit_pess, roi,
                "✅ מומלץ" if profit_pess > 0 else "🛑 לא מומלץ",
                st.session_state.general_comments, params,
            )
            writer.close()
            buf.seek(0)
            excel_data = buf.getvalue()
        except PermissionError:
            st.error("❌ הקובץ פתוח ב-Excel. סגור אותו ונסה שוב.")
        except Exception as e:
            st.error(f"❌ שגיאת ייצוא ({type(e).__name__}): {e}")

        if excel_data:
            st.download_button(
                label="📥 הורד דוח לאקסל",
                data=excel_data,
                file_name=f"Growth_{clean_filename}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
                use_container_width=True,
                key="btn_download_final",
            )
        else:
            st.warning("⚠️ לא ניתן ליצור את הקובץ.")

        st.button(
            "✏️ חזור לעריכה",
            use_container_width=True,
            on_click=lambda: st.session_state.update({'view_mode': 'edit'}),
        )
