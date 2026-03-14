import pandas as pd

from utils import format_number_str


# ---------------------------------------------------------------------------
# Methodology table
# ---------------------------------------------------------------------------

def generate_methodology() -> pd.DataFrame:
    data = [
        ("כמות שירותים נחזית", "הערכה שנתית של היקף הפעילות (זימונים)."),
        ("תקנים (FTE)", "משרה מלאה (Full Time Equivalent). 1.0 = משרה מלאה, 0.5 = חצי משרה."),
        ("חישוב הכנסה נטו", "הנוסחה: מחיר מחירון (ברוטו) × (1 − (הנחת מחזור + הפרשה לערעורים))."),
        ("חישוב הכנסה קאפ (CAP)", "הנוסחה: מחיר מחירון (ברוטו) * מקדם קאפ (תעריף שולי). ללא הנחות נוספות."),
        ("ניצולת (Utilization)", "מדד רגישות המייצג את היקף המימוש בפועל לעומת התכנון."),
        ("No Show", "שיעור המטופלים שקבעו תור אך לא הגיעו."),
        ("מקור הנתונים", "נתוני שכר מקובץ HR פנימי. תעריפים ממחירון משרד הבריאות."),
        ("תרחיש קאפ (CAP)", "הכנסה צפויה במקרה של חריגה מתקרת התקציב."),
        ("המלצה", "נגזרת מהתרחיש הפסימי: אם הפרויקט מרוויח גם בתרחיש זה, הוא מומלץ."),
        ("עלות תקורה", "העמסת הוצאות עקיפות על הנטו."),
        ("ROI", "שנים להחזר ההשקעה."),
    ]
    return pd.DataFrame(data, columns=["מונח", "הסבר מפורט"])


def generate_verbal_analysis(profit_base, _profit_opt_unused, profit_pess, capex, _opex_neg, revenue, roi, _df_flat) -> str:
    if profit_pess > 0:
        status = "✅ הפרויקט איתן כלכלית (רווחי גם בתרחיש פסימי)."
    elif profit_base > 0:
        status = "⚠️ הפרויקט רווחי בתרחיש הבסיס אך רגיש לשינויים."
    else:
        status = "🛑 הפרויקט אינו כדאי כלכלית."

    roi_line = f"זמן החזר ההשקעה (ROI) המוערך הוא {roi:.1f} שנים." if roi > 0 else ""
    return (
        f"{status}\n\n"
        f"הרווח התפעולי הצפוי (בסיס) הוא ₪{profit_base:,.0f} לשנה.\n"
        f"ההשקעה הראשונית הנדרשת עומדת על ₪{capex:,.0f}.\n"
        + roi_line
    )


# ---------------------------------------------------------------------------
# Excel report builder
# ---------------------------------------------------------------------------

def _add_formats(wb) -> dict:
    return {
        'title_main': wb.add_format({'bold': True, 'font_size': 18, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#366092', 'font_color': 'white'}),
        'title_sec': wb.add_format({'bold': True, 'font_size': 14, 'align': 'right', 'valign': 'vcenter', 'bg_color': '#DCE6F1', 'top': 2}),
        'header': wb.add_format({'bold': True, 'bg_color': '#B8CCE4', 'border': 1, 'align': 'center', 'valign': 'vcenter', 'text_wrap': True}),
        'normal': wb.add_format({'border': 1, 'align': 'left', 'valign': 'vcenter'}),
        'curr': wb.add_format({'num_format': '#,##0', 'border': 1, 'align': 'center', 'valign': 'vcenter'}),
        'pct': wb.add_format({'num_format': '0%', 'border': 1, 'align': 'center', 'valign': 'vcenter'}),
        'curr_bold': wb.add_format({'num_format': '#,##0', 'border': 1, 'align': 'center', 'valign': 'vcenter', 'bold': True, 'bg_color': '#F2F2F2'}),
        'normal_bold': wb.add_format({'border': 1, 'align': 'left', 'valign': 'vcenter', 'bold': True, 'bg_color': '#F2F2F2'}),
        'sum_label': wb.add_format({'border': 1, 'align': 'right', 'valign': 'vcenter'}),
        'sum_val': wb.add_format({'num_format': '#,##0', 'border': 1, 'align': 'center', 'valign': 'vcenter'}),
        'sum_rev_label': wb.add_format({'border': 1, 'align': 'right', 'valign': 'vcenter', 'bottom': 2, 'bold': True}),
        'sum_rev_val': wb.add_format({'num_format': '#,##0', 'border': 1, 'align': 'center', 'valign': 'vcenter', 'bottom': 2, 'bold': True}),
        'sum_inv_label': wb.add_format({'border': 1, 'align': 'right', 'valign': 'vcenter', 'bottom': 6, 'bold': True}),
        'sum_inv_val': wb.add_format({'num_format': '#,##0', 'border': 1, 'align': 'center', 'valign': 'vcenter', 'bottom': 6, 'bold': True}),
        'sum_profit_val': wb.add_format({'num_format': '#,##0', 'border': 1, 'align': 'center', 'valign': 'vcenter', 'bold': True, 'bg_color': '#EBF1DE'}),
        'text_box': wb.add_format({'border': 1, 'align': 'right', 'valign': 'top', 'text_wrap': True, 'bg_color': '#FFFFCC'}),
        'assumption_box': wb.add_format({'border': 2, 'align': 'right', 'valign': 'vcenter', 'text_wrap': True, 'bg_color': '#FFF2CC', 'bold': False}),
        'assumption_title': wb.add_format({'border': 2, 'align': 'right', 'valign': 'vcenter', 'bg_color': '#FFE699', 'bold': True}),
        'formula_cell': wb.add_format({'border': 1, 'align': 'right', 'valign': 'vcenter', 'italic': True, 'font_color': '#444444', 'font_size': 9, 'text_wrap': True, 'bg_color': '#F9F9F9'}),
        'mgmt_header': wb.add_format({'bold': True, 'bg_color': '#2E75B6', 'font_color': 'white', 'border': 1, 'align': 'center', 'valign': 'vcenter', 'text_wrap': True}),
        'mgmt_title_main': wb.add_format({'bold': True, 'font_size': 18, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#1F4E79', 'font_color': 'white'}),
        'mgmt_title_sec': wb.add_format({'bold': True, 'font_size': 13, 'align': 'right', 'valign': 'vcenter', 'bg_color': '#BDD7EE', 'top': 2}),
        'mgmt_profit_val': wb.add_format({'num_format': '#,##0', 'border': 1, 'align': 'center', 'valign': 'vcenter', 'bold': True, 'bg_color': '#E2EFDA', 'font_size': 11}),
        'mgmt_profit_label': wb.add_format({'border': 1, 'align': 'right', 'valign': 'vcenter', 'bold': True, 'bg_color': '#E2EFDA', 'font_size': 11}),
        'mgmt_curr': wb.add_format({'num_format': '#,##0', 'border': 1, 'align': 'center', 'valign': 'vcenter'}),
        'mgmt_normal': wb.add_format({'border': 1, 'align': 'right', 'valign': 'vcenter'}),
        'mgmt_normal_bold': wb.add_format({'border': 1, 'align': 'right', 'valign': 'vcenter', 'bold': True, 'bg_color': '#F2F2F2'}),
        'mgmt_curr_bold': wb.add_format({'num_format': '#,##0', 'border': 1, 'align': 'center', 'valign': 'vcenter', 'bold': True, 'bg_color': '#F2F2F2'}),
        'mgmt_sum_label': wb.add_format({'border': 1, 'align': 'right', 'valign': 'vcenter'}),
        'mgmt_sum_val': wb.add_format({'num_format': '#,##0', 'border': 1, 'align': 'center', 'valign': 'vcenter'}),
        'assump_pct': wb.add_format({'num_format': '0.0%', 'border': 2, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#FFF2CC', 'bold': True}),
        'assump_pct_ref': wb.add_format({'num_format': '0.0%', 'border': 1, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#FFF2CC'}),
    }


def create_management_report_sheet(wb, fmt, df_flat, p_name, capex, opex, rev, prof_b, prof_p, roi, rec, comments, params, include_cap=True):
    """Management report: fixed assumption cells, all revenue cells use Excel formulas.
    CAP is always baked into the net tariff using additive combined discounts.
    include_cap kept for API compatibility but ignored internally."""
    ws = wb.add_worksheet('דוח מנהלים')
    ws.right_to_left()

    # ---- Extract params -------------------------------------------------
    vol       = params.get('VOL_DISCOUNT', 0)
    appeals   = params.get('APPEALS_PROV', 0)
    no_show_g = params.get('NO_SHOW_RATE', 0)
    overhead  = params.get('OVERHEAD_RATE', 0)
    cap_f     = params.get('CAP_RATE_FACTOR', 0)

    # ---- Assumption cell positions (cols E-F, rows 2-6) -----------------
    # VOL → $F$3, APP → $F$4, NS → $F$5, OVH → $F$6, CAP → $F$7
    VOL_ROW, APP_ROW          = 2, 3
    NS_ROW,  OVH_ROW, CAP_ROW = 4, 5, 6
    AL, AC = 4, 5   # assumption label col (E=4), value col (F=5)
    vol_ref = '$F$3'
    app_ref = '$F$4'
    ns_ref  = '$F$5'
    ovh_ref = '$F$6'
    cap_ref = '$F$7'

    # ---- Revenue table column indices (0-based, A–F; no CAP column) -----
    CN, CQ, CG = 0, 1, 2   # name, effective qty, gross tariff
    CNT        = 3           # net tariff (all-in: vol+appeals+overhead+cap)
    CGT, CNTK  = 4, 5       # total gross, total net

    # ---- Fixed summary row indices (0-based) ----------------------------
    SUMM_HEADER = 1
    SUMM_REV    = 2   # Excel row 3
    SUMM_HR     = 3   # Excel row 4
    SUMM_OPS    = 4   # Excel row 5
    SUMM_CAPEX  = 5   # Excel row 6
    SUMM_EBITDA = 6   # Excel row 7
    SUMM_PROFIT = 7   # Excel row 8
    SUMM_ROI    = 8   # Excel row 9
    SUMM_REC    = 9   # Excel row 10

    # ---- Placeholders for total cell addresses -------------------------
    rev_net_cell  = None
    mp_total_cell = op_total_cell = inv_total_cell = None
    s_net_t = 0.0
    s_mp    = 0.0
    s_op    = 0.0
    si      = 0.0

    # ---- Row 0: Title ---------------------------------------------------
    ws.set_row(0, 30)
    ws.merge_range(0, 0, 0, 5, f'דוח מנהלים: {p_name}', fmt['mgmt_title_main'])

    # ---- Assumptions header (row 1) + cells (rows 2-6) at cols E-F -----
    ws.merge_range(1, AL, 1, 5,
                   'הנחות החישוב  –  ניתן לשנות ערכים בעמודה F ולראות השפעה על הנוסחאות',
                   fmt['assumption_title'])
    for ar, label, val in [
        (VOL_ROW, 'הנחת מחזור',     vol),
        (APP_ROW, 'הפרשה לערעורים', appeals),
        (NS_ROW,  'אי-הגעה',        no_show_g),
        (OVH_ROW, 'תקורה',          overhead),
        (CAP_ROW, 'מקדם קאפ',       cap_f),
    ]:
        ws.write(ar, AL, label, fmt['assumption_box'])
        ws.write(ar, AC, val,   fmt['assump_pct'])

    # ---- Detail sections (written first to capture total row positions) -
    row = 11  # start below summary/assumption area

    # ---- Revenue detail -------------------------------------------------
    df_rev_rows = df_flat[df_flat['קטגוריה'] == 'Revenue']
    if not df_rev_rows.empty:
        ws.merge_range(row, 0, row, 5,
                       'פירוט הכנסות – לחץ על כל תא כדי לראות את נוסחת החישוב',
                       fmt['mgmt_title_sec'])
        row += 1
        for i, h in enumerate([
            'שם השירות', 'כמות אפקטיבית', 'תעריף ברוטו (₪)',
            'תעריף נטו (₪)', 'סה"כ ברוטו (₪)', 'סה"כ נטו (₪)',
        ]):
            ws.write(row, i, h, fmt['mgmt_header'])
        ws.set_row(row, 28)
        row += 1
        data_start_excel = row + 1
        for _, r in df_rev_rows.iterrows():
            er           = row + 1
            u_gross_val  = r['תעריף יחידה ברוטו']
            net_tar_orig = r['תעריף יחידה אחרי הנחות']
            gross_t      = r['סה"כ ברוטו']
            # Effective quantity: no-show already applied in gross_t
            qty_eff = (gross_t / u_gross_val) if u_gross_val > 0 else (
                r['כמות שירותים רגילים'] * (1 - no_show_g)
            )
            # Detect private service (no discounts applied in calculations)
            is_private = u_gross_val > 0 and abs(u_gross_val - net_tar_orig) / u_gross_val < 0.001
            # Net tariff and Python fallback values
            if is_private:
                u_net_new = u_gross_val * (1 - overhead)
                net_t_new = qty_eff * u_net_new
            else:
                combined  = vol + appeals + overhead + cap_f
                u_net_new = u_gross_val * (1 - combined)
                net_t_new = qty_eff * u_net_new
            # Service display name
            _svc_code    = str(r.get('קוד שירות', '')).strip()
            _svc_display = f"{r['שם שירות']} - {_svc_code}" if _svc_code else r['שם שירות']
            qty_raw = r['כמות שירותים רגילים']
            ws.write(row, CN, _svc_display, fmt['mgmt_normal'])
            ws.write_formula(row, CQ, f'={qty_raw}*(1-{ns_ref})', fmt['mgmt_curr'], qty_eff)
            ws.write(row, CG, u_gross_val,  fmt['mgmt_curr'])
            if is_private:
                ws.write_formula(row, CNT,
                    f'=C{er}*(1-{ovh_ref})',
                    fmt['mgmt_curr'], u_net_new)
            else:
                ws.write_formula(row, CNT,
                    f'=C{er}*(1-({vol_ref}+{app_ref}+{ovh_ref}+{cap_ref}))',
                    fmt['mgmt_curr'], u_net_new)
            ws.write_formula(row, CGT,  f'=B{er}*C{er}', fmt['mgmt_curr'], gross_t)
            ws.write_formula(row, CNTK, f'=B{er}*D{er}', fmt['mgmt_curr'], net_t_new)
            s_net_t += net_t_new
            row += 1
        data_end_excel = row
        _cgt_col  = chr(ord('A') + CGT)   # 'E'
        _cntk_col = chr(ord('A') + CNTK)  # 'F'
        ws.write(row, CN, 'סה"כ', fmt['mgmt_normal_bold'])
        ws.write_formula(row, CGT,
            f'=SUM({_cgt_col}{data_start_excel}:{_cgt_col}{data_end_excel})',
            fmt['mgmt_curr_bold'], df_rev_rows['סה"כ ברוטו'].sum())
        ws.write_formula(row, CNTK,
            f'=SUM({_cntk_col}{data_start_excel}:{_cntk_col}{data_end_excel})',
            fmt['mgmt_curr_bold'], s_net_t)
        rev_net_cell = f'{_cntk_col}{row + 1}'
        row += 2

    # ---- Manpower -------------------------------------------------------
    df_manpower = df_flat[df_flat['קטגוריה'] == 'Manpower']
    if not df_manpower.empty:
        ws.merge_range(row, 0, row, 5, 'פירוט כוח אדם', fmt['mgmt_title_sec'])
        row += 1
        # 6 cols: A=name  B=FTEs  C=annual cost/unit  D=sess qty  E=sess price  F=total
        for i, h in enumerate([
            'שם / תפקיד', 'תקנים', 'עלות שנתית לתקן (₪)',
            'כמות ססיות לתקן', 'מחיר ססייה (₪)', 'סה"כ עלות (₪)',
        ]):
            ws.write(row, i, h, fmt['mgmt_header'])
        row += 1
        mp_data_start_excel = row + 1
        df_mp_std   = df_manpower[df_manpower['Calc_Mode'] == 'FTE']
        df_mp_shift = df_manpower[df_manpower['Calc_Mode'].isin(['Daily', 'Hourly'])]
        for _, r in df_mp_std.iterrows():
            er             = row + 1   # 1-based Excel row for formulas
            annual_salary  = abs(r['סה"כ נטו לכיס'])
            sess_qty       = r['כמות שירותי ססיה']
            sess_cost_unit = r['עלות ססיה']
            sess_total     = sess_qty * sess_cost_unit
            fte_count      = max(float(r['כמות שירותים רגילים']), 1)
            unit_cost      = r['עלות לשירות']
            sess_per_fte   = sess_qty / fte_count if fte_count else 0
            if annual_salary == 0 and sess_total > 0:
                # Sessions-only FTE: total = FTEs × sessions_per_FTE × price
                total_cost             = sess_total
                annual_col, annual_fmt = '',        fmt['mgmt_normal']
                sess_cnt_col           = int(sess_per_fte)
                sess_prc_col           = sess_cost_unit
                mp_total_formula       = f'=B{er}*D{er}*E{er}'
            elif sess_total > 0:
                # Both annual salary and sessions: total = FTEs × (annual + sess×price)
                total_cost             = annual_salary + sess_total
                annual_col, annual_fmt = unit_cost,  fmt['mgmt_curr']
                sess_cnt_col           = int(sess_per_fte)
                sess_prc_col           = sess_cost_unit
                mp_total_formula       = f'=B{er}*(C{er}+D{er}*E{er})'
            else:
                # Salary-only FTE: total = FTEs × annual
                total_cost             = annual_salary
                annual_col, annual_fmt = unit_cost,  fmt['mgmt_curr']
                sess_cnt_col           = ''
                sess_prc_col           = ''
                mp_total_formula       = f'=B{er}*C{er}'
            # Suppress zero annual cost / zero session count
            if annual_col == 0:
                annual_col, annual_fmt = '', fmt['mgmt_normal']
            if sess_cnt_col == 0:
                sess_cnt_col = ''
                sess_prc_col = ''
            ws.write(row, 0, r['שם שירות'],                fmt['mgmt_normal'])
            ws.write(row, 1, r['כמות שירותים רגילים'],     fmt['mgmt_normal'])
            ws.write(row, 2, annual_col,                    annual_fmt)
            ws.write(row, 3, sess_cnt_col,                  fmt['mgmt_normal'])
            ws.write(row, 4, sess_prc_col,
                     fmt['mgmt_curr'] if sess_prc_col != '' else fmt['mgmt_normal'])
            ws.write_formula(row, 5, mp_total_formula,      fmt['mgmt_curr'], total_cost)
            s_mp += total_cost; row += 1
        for _, r in df_mp_shift.iterrows():
            er     = row + 1
            sh_tot = abs(r['סה"כ נטו לכיס'])
            ws.write(row, 0, r['שם שירות'],                fmt['mgmt_normal'])
            ws.write(row, 1, r['כמות שירותים רגילים'],     fmt['mgmt_normal'])
            ws.write(row, 2, r['עלות לשירות'],              fmt['mgmt_curr'])
            ws.write(row, 3, '',                             fmt['mgmt_normal'])
            ws.write(row, 4, '',                             fmt['mgmt_normal'])
            ws.write_formula(row, 5, f'=B{er}*C{er}',       fmt['mgmt_curr'], sh_tot)
            s_mp += sh_tot; row += 1
        mp_last_data_excel = row
        ws.write(row, 0, 'סה"כ כוח אדם', fmt['mgmt_normal_bold'])
        ws.write_formula(row, 5, f'=SUM(F{mp_data_start_excel}:F{mp_last_data_excel})', fmt['mgmt_curr_bold'], s_mp)
        mp_total_cell = f'F{row + 1}'
        row += 2

    # ---- Operations -----------------------------------------------------
    df_op = df_flat[
        (df_flat['קטגוריה'] == 'Operation') &
        (df_flat['סוג'] != 'השקעה חד-פעמית') &
        (df_flat['Row_Type'] != 'Session')
    ]
    if not df_op.empty:
        ws.merge_range(row, 0, row, 5, 'פירוט הוצאות תפעול שוטף', fmt['mgmt_title_sec'])
        row += 1
        for i, h in enumerate(['סעיף הוצאה', 'עלות יחידה (₪)', 'כמות', 'סה"כ (₪)']):
            ws.write(row, i, h, fmt['mgmt_header'])
        row += 1
        op_data_start_excel = row + 1
        for _, r in df_op.iterrows():
            er       = row + 1
            op_tot   = r['סה"כ נטו לכיס']
            op_unit  = r['עלות לשירות']
            ws.write(row, 0, r['שם שירות'],                fmt['mgmt_normal'])
            ws.write(row, 1, op_unit if op_unit != 0 else '',
                     fmt['mgmt_curr'] if op_unit != 0 else fmt['mgmt_normal'])
            ws.write(row, 2, r['כמות שירותים רגילים'],     fmt['mgmt_normal'])
            ws.write_formula(row, 3, f'=-B{er}*C{er}',      fmt['mgmt_curr'], op_tot)
            s_op += op_tot; row += 1
        op_last_data_excel = row
        ws.write(row, 0, 'סה"כ תפעול', fmt['mgmt_normal_bold'])
        ws.write_formula(row, 3, f'=SUM(D{op_data_start_excel}:D{op_last_data_excel})', fmt['mgmt_curr_bold'], s_op)
        op_total_cell = f'D{row + 1}'
        row += 2

    # ---- Investments ----------------------------------------------------
    df_inv = df_flat[df_flat['סוג'] == 'השקעה חד-פעמית']
    if not df_inv.empty:
        ws.merge_range(row, 0, row, 5, 'פירוט השקעות', fmt['mgmt_title_sec'])
        row += 1
        for i, h in enumerate(['סעיף השקעה', 'עלות יחידה (₪)', 'כמות', 'שנות חיים', 'סה"כ (₪)']):
            ws.write(row, i, h, fmt['mgmt_header'])
        row += 1
        inv_data_start_excel = row + 1
        for _, r in df_inv.iterrows():
            er       = row + 1
            inv_tot  = r['סה"כ נטו לכיס']
            inv_unit = r['עלות לשירות']
            ws.write(row, 0, r['שם שירות'],                fmt['mgmt_normal'])
            ws.write(row, 1, inv_unit if inv_unit != 0 else '',
                     fmt['mgmt_curr'] if inv_unit != 0 else fmt['mgmt_normal'])
            ws.write(row, 2, r['כמות שירותים רגילים'],     fmt['mgmt_normal'])
            ws.write(row, 3, r.get('Lifespan', 10),         fmt['mgmt_normal'])
            ws.write_formula(row, 4, f'=-B{er}*C{er}',      fmt['mgmt_curr'], inv_tot)
            si += inv_tot; row += 1
        inv_last_data_excel = row
        ws.write(row, 0, 'סה"כ השקעות', fmt['mgmt_normal_bold'])
        ws.write_formula(row, 4, f'=SUM(E{inv_data_start_excel}:E{inv_last_data_excel})', fmt['mgmt_curr_bold'], si)
        inv_total_cell = f'E{row + 1}'
        row += 2

    # ---- Comments -------------------------------------------------------
    # Use a floating text-box so the economist can edit the note directly
    # in Excel without re-downloading the report from the app.
    if comments:
        ws.write(row, 0, 'הערות הכלכלן', fmt['mgmt_header'])
        row += 1
        for _r in range(row, row + 10):
            ws.set_row(_r, 18)
        # Auto-detect direction: RTL for Hebrew text, LTR for English
        _rtl = any('\u0590' <= c <= '\u05FF' for c in comments)
        ws.insert_textbox(row, 0, comments, {
            'width':           620,
            'height':          180,
            'font':            {'name': 'Arial', 'size': 11},
            'align':           {'vertical': 'top',
                                'horizontal': 'right' if _rtl else 'left'},
            'text_direction':  'rtl' if _rtl else 'ltr',
            'object_position': 1,   # move but don't size with cells
        })
        row += 10

    # ---- Compute Python fallback values for summary ---------------------
    prof_b_new           = s_net_t - s_mp + s_op   # s_op is already negative
    total_net_profit_new = prof_b_new + si           # si is already negative
    roi_new              = (abs(si) / prof_b_new) if (prof_b_new > 0 and si < 0) else 0
    rec_new              = "✅ מומלץ" if total_net_profit_new > 0 else "🛑 לא מומלץ"

    # ---- Summary table – compact (written last, formulas ref detail totals) -
    # Items are written only when their value != 0, so no empty rows appear.
    # We track the 1-based Excel row each item lands on to build EBITDA/PROFIT
    # formulas dynamically.
    s_row = SUMM_HEADER + 1   # 0-based write row, starts at 2
    ws.write(SUMM_HEADER, 0, 'מדד',     fmt['mgmt_header'])
    ws.write(SUMM_HEADER, 1, 'ערך (₪)', fmt['mgmt_header'])

    rev_er = hr_er = ops_er = capex_er = ebitda_er = profit_er = None

    if s_net_t != 0:
        rev_er = s_row + 1
        if rev_net_cell:
            ws.write_formula(s_row, 1, f'={rev_net_cell}', fmt['mgmt_sum_val'], s_net_t)
        else:
            ws.write(s_row, 1, s_net_t, fmt['mgmt_sum_val'])
        ws.write(s_row, 0, 'סה"כ הכנסות שנתיות', fmt['mgmt_sum_label'])
        s_row += 1

    if s_mp != 0:
        hr_er = s_row + 1
        if mp_total_cell:
            ws.write_formula(s_row, 1, f'=-{mp_total_cell}', fmt['mgmt_sum_val'], -s_mp)
        else:
            ws.write(s_row, 1, -s_mp, fmt['mgmt_sum_val'])
        ws.write(s_row, 0, 'סה"כ הוצאות כוח אדם', fmt['mgmt_sum_label'])
        s_row += 1

    if s_op != 0:
        ops_er = s_row + 1
        if op_total_cell:
            ws.write_formula(s_row, 1, f'={op_total_cell}', fmt['mgmt_sum_val'], s_op)
        else:
            ws.write(s_row, 1, s_op, fmt['mgmt_sum_val'])
        ws.write(s_row, 0, 'סה"כ הוצאות תפעול', fmt['mgmt_sum_label'])
        s_row += 1

    if si != 0:
        capex_er = s_row + 1
        if inv_total_cell:
            ws.write_formula(s_row, 1, f'={inv_total_cell}', fmt['mgmt_sum_val'], si)
        else:
            ws.write(s_row, 1, si, fmt['mgmt_sum_val'])
        ws.write(s_row, 0, 'השקעה חד-פעמית', fmt['mgmt_sum_label'])
        s_row += 1

    # Operating profit = revenue + HR + ops (only present items)
    ebitda_er    = s_row + 1
    ebitda_parts = [f'B{er}' for er in [rev_er, hr_er, ops_er] if er is not None]
    ws.write_formula(s_row, 1,
        ('=' + '+'.join(ebitda_parts)) if ebitda_parts else '=0',
        fmt['mgmt_profit_val'], prof_b_new)
    ws.write(s_row, 0, 'רווח תפעולי', fmt['mgmt_profit_label'])
    s_row += 1

    # Net profit = operating profit + CAPEX (only if CAPEX exists)
    profit_er    = s_row + 1
    profit_parts = [f'B{ebitda_er}']
    if capex_er is not None:
        profit_parts.append(f'B{capex_er}')
    ws.write_formula(s_row, 1, '=' + '+'.join(profit_parts),
                     fmt['mgmt_profit_val'], total_net_profit_new)
    ws.write(s_row, 0, 'רווח כולל (בניכוי השקעה)', fmt['mgmt_profit_label'])
    s_row += 1

    # ROI – only if there is an investment with a meaningful payback period
    if capex_er is not None and roi_new != 0:
        ws.write_formula(s_row, 1,
            f'=IF(B{ebitda_er}>0,-B{capex_er}/B{ebitda_er},0)',
            fmt['mgmt_sum_val'], roi_new)
        ws.write(s_row, 0, 'שנים להחזר השקעה', fmt['mgmt_sum_label'])
        s_row += 1

    # Recommendation
    ws.write_formula(s_row, 1,
        f'=IF(B{profit_er}>0,"\u2705 \u05de\u05d5\u05de\u05dc\u05e5","\U0001f6d1 \u05dc\u05d0 \u05de\u05d5\u05de\u05dc\u05e5")',
        fmt['mgmt_sum_val'], rec_new)
    ws.write(s_row, 0, 'המלצה עסקית', fmt['mgmt_sum_label'])

    # ---- Column widths --------------------------------------------------
    ws.set_column('A:A', 35)   # service name / label
    ws.set_column('B:B', 16)   # effective qty / summary values
    ws.set_column('C:C', 16)   # gross tariff
    ws.set_column('D:D', 16)   # net tariff
    ws.set_column('E:F', 18)   # total gross, total net / assumption labels+values
    ws.set_column('G:G', 14)   # extra


def create_hybrid_report_sheet(writer, df_flat, p_name, capex, opex, rev, prof_b, prof_p, roi, rec, comments, params, include_cap=True):
    wb = writer.book
    fmt = _add_formats(wb)

    # Create management-friendly sheet first so it appears as the first tab
    create_management_report_sheet(wb, fmt, df_flat, p_name, capex, opex, rev, prof_b, prof_p, roi, rec, comments, params, include_cap=include_cap)

    show_scenarios = not (
        (df_flat['Pct_Opt_Raw'] == 0).all() and (df_flat['Pct_Pess_Raw'] == 0).all()
    )

    ws = wb.add_worksheet('דוח כלכלי')
    ws.right_to_left()
    ws_meta = wb.add_worksheet('מתודולוגיה והנחות')
    ws_meta.right_to_left()

    # ---- Methodology sheet -----------------------------------------------
    ws_meta.merge_range('A1:B1', "הנחות יסוד (פרמטרים)", fmt['title_sec'])
    ws_meta.write(1, 0, "פרמטר", fmt['header'])
    ws_meta.write(1, 1, "ערך", fmt['header'])
    hebrew_params = {
        "OVERHEAD_RATE": "אחוז תקורה",
        "HMO_DISCOUNT": "הנחת קופות חולים",
        "VOL_DISCOUNT": "הנחת מחזור",
        "APPEALS_PROV": "הפרשה לערעורים",
        "NO_SHOW_RATE": "אחוז אי-הגעה (No Show)",
        "CAP_RATE_FACTOR": "תעריף שולי (CAP)",
    }
    r_p = 2
    for k, v in params.items():
        if k == 'HMO_DISCOUNT':
            continue   # הוסר — הנחת קופות אינה בשימוש
        ws_meta.write(r_p, 0, hebrew_params.get(k, k), fmt['normal'])
        ws_meta.write(r_p, 1, f"{v * 100:.1f}%", fmt['normal'])
        r_p += 1

    r_p += 2
    ws_meta.merge_range(r_p, 0, r_p, 1, "מונחים ומתודולוגיה", fmt['title_sec'])
    r_p += 1
    df_meth = generate_methodology()
    ws_meta.write(r_p, 0, "מונח", fmt['header'])
    ws_meta.write(r_p, 1, "הסבר", fmt['header'])
    r_p += 1
    for _, row_m in df_meth.iterrows():
        ws_meta.write(r_p, 0, row_m['מונח'], fmt['normal'])
        ws_meta.write(r_p, 1, row_m['הסבר מפורט'], fmt['normal'])
        r_p += 1
    ws_meta.set_column('A:A', 30)
    ws_meta.set_column('B:B', 70)

    # ---- Derived totals --------------------------------------------------
    df_op_only = df_flat[(df_flat['קטגוריה'] == 'Operation') & (df_flat['סוג'] != 'השקעה חד-פעמית')]
    total_op_exp = abs(df_op_only['סה"כ נטו לכיס'].sum())
    df_hr_only = df_flat[df_flat['קטגוריה'] == 'Manpower']
    total_hr_exp = abs(df_hr_only['סה"כ נטו לכיס'].sum())
    total_capex = abs(capex)
    total_net_profit = prof_b - capex

    df_rev_cap = df_flat[df_flat['קטגוריה'] == 'Revenue']
    total_rev_cap = df_rev_cap['סה"כ אחרי קאפ'].sum()
    op_profit_cap = total_rev_cap - total_op_exp - total_hr_exp
    total_net_profit_cap = op_profit_cap - total_capex
    roi_cap = (total_capex / op_profit_cap) if op_profit_cap > 0 else 0
    rec_cap = "✅ מומלץ" if total_net_profit_cap > 0 else "🛑 לא מומלץ"

    # ---- Main report sheet summary table ---------------------------------
    ws.merge_range('B1:D1', f"דוח מסכם: {p_name}", fmt['title_main'])
    ws.merge_range('F2:H10', generate_verbal_analysis(prof_b, 0, prof_p, capex, -opex, rev, roi, df_flat), fmt['text_box'])

    row_idx = 2
    ws.write(row_idx, 1, "מדד / סעיף", fmt['header'])
    ws.write(row_idx, 2, "תרחיש נטו", fmt['header'])
    if include_cap:
        ws.write(row_idx, 3, "תרחיש קאפ", fmt['header'])
    row_idx += 1

    summary_rows = [
        ("סה\"כ הכנסות", rev, total_rev_cap, fmt['sum_rev_label'], fmt['sum_rev_val'], rev != 0 or total_rev_cap != 0),
        ("סה\"כ הוצאות תפעול", -total_op_exp, -total_op_exp, fmt['sum_label'], fmt['sum_val'], total_op_exp != 0),
        ("סה\"כ הוצאות כוח אדם", -total_hr_exp, -total_hr_exp, fmt['sum_label'], fmt['sum_val'], total_hr_exp != 0),
        ("סה\"כ הוצאות השקעה", -total_capex, -total_capex, fmt['sum_inv_label'], fmt['sum_inv_val'], total_capex != 0),
        ("רווח כולל (בניכוי השקעה)", total_net_profit, total_net_profit_cap, fmt['sum_label'], fmt['sum_profit_val'], True),
        ("רווח תפעולי (EBITDA)", prof_b, op_profit_cap, fmt['sum_label'], fmt['sum_val'], True),
    ]
    for label, val_net, val_cap, lbl_fmt, val_fmt, show in summary_rows:
        if show:
            ws.write(row_idx, 1, label, lbl_fmt)
            ws.write(row_idx, 2, val_net, val_fmt)
            if include_cap:
                ws.write(row_idx, 3, val_cap, val_fmt)
            row_idx += 1

    ws.write(row_idx, 1, "ROI (שנים להחזר)", fmt['sum_label'])
    ws.write(row_idx, 2, f"{roi:.1f}", fmt['sum_val'])
    if include_cap:
        ws.write(row_idx, 3, f"{roi_cap:.1f}", fmt['sum_val'])
    row_idx += 1
    ws.write(row_idx, 1, "המלצה עסקית", fmt['sum_label'])
    ws.write(row_idx, 2, rec, fmt['sum_val'])
    if include_cap:
        ws.write(row_idx, 3, rec_cap, fmt['sum_val'])
    row_idx += 3

    # ---- Revenue detail --------------------------------------------------
    df_rev = df_flat[df_flat['קטגוריה'] == 'Revenue']
    if not df_rev.empty:
        info_headers = ["שם השירות", "כמות שנתית", "תעריף ברוטו ליח'", "תעריף נטו ליח'"]
        if include_cap:
            info_headers.append("תעריף קאפ ליח'")
        ws.merge_range(row_idx, 0, row_idx, len(info_headers) - 1, "פירוט הכנסות - מידע כללי", fmt['title_sec'])
        row_idx += 1
        for i, h in enumerate(info_headers):
            ws.write(row_idx, i, h, fmt['header'])
        row_idx += 1
        for _, row in df_rev.iterrows():
            _code = str(row.get('קוד שירות', '')).strip()
            _svc_lbl = f"{row['שם שירות']} - {_code}" if _code else row['שם שירות']
            ws.write(row_idx, 0, _svc_lbl, fmt['normal'])
            ws.write(row_idx, 1, row['כמות שירותים רגילים'], fmt['normal'])
            ws.write(row_idx, 2, row['תעריף יחידה ברוטו'], fmt['curr'])
            ws.write(row_idx, 3, row['תעריף יחידה אחרי הנחות'], fmt['curr'])
            if include_cap:
                ws.write(row_idx, 4, row['תעריף יחידה תחת cap'], fmt['curr'])
            row_idx += 1
        row_idx += 1

        rev_headers = ["שם השירות", "סה\"כ הכנסה ברוטו", "סה\"כ הכנסה נטו"]
        if include_cap:
            rev_headers.append("סה\"כ הכנסה בקאפ")
        rev_headers += [
            f"עלות תקורה ({params.get('OVERHEAD_RATE', 0.29) * 100:.0f}%)", "סה\"כ נטו אחרי תקורה",
        ]
        if show_scenarios:
            rev_headers += ["סה\"כ נטו אופטימי", "סה\"כ נטו פסימי"]
        ws.merge_range(row_idx, 0, row_idx, len(rev_headers) - 1, "פירוט הכנסות - סכימות ותחשיבים", fmt['title_sec'])
        row_idx += 1
        for i, h in enumerate(rev_headers):
            ws.write(row_idx, i, h, fmt['header'])
        row_idx += 1

        s_gross = s_net = s_cap = s_ovh = s_pocket = s_opt = s_pess = 0
        for _, row in df_rev.iterrows():
            _code2 = str(row.get('קוד שירות', '')).strip()
            _svc_lbl2 = f"{row['שם שירות']} - {_code2}" if _code2 else row['שם שירות']
            ws.write(row_idx, 0, _svc_lbl2, fmt['normal'])
            ws.write(row_idx, 1, row['סה"כ ברוטו'], fmt['curr'])
            ws.write(row_idx, 2, row['סה"כ אחרי הנחות'], fmt['curr'])
            _col = 3
            if include_cap:
                ws.write(row_idx, _col, row['סה"כ אחרי קאפ'], fmt['curr']); _col += 1
            ws.write(row_idx, _col, row['עלות תקורה'], fmt['curr']); _col += 1
            ws.write(row_idx, _col, row['סה"כ נטו לכיס'], fmt['curr']); _col += 1
            s_gross += row['סה"כ ברוטו']
            s_net   += row['סה"כ אחרי הנחות']
            s_cap   += row['סה"כ אחרי קאפ']
            s_ovh   += row['עלות תקורה']
            s_pocket += row['סה"כ נטו לכיס']
            if show_scenarios:
                ws.write(row_idx, _col, row['תרחיש אופטימי'], fmt['curr']); _col += 1
                ws.write(row_idx, _col, row['תרחיש פסימי'], fmt['curr'])
                s_opt  += row['תרחיש אופטימי']
                s_pess += row['תרחיש פסימי']
            row_idx += 1

        ws.write(row_idx, 0, "סה\"כ", fmt['normal_bold'])
        _col = 1
        for val in [s_gross, s_net]:
            ws.write(row_idx, _col, val, fmt['curr_bold']); _col += 1
        if include_cap:
            ws.write(row_idx, _col, s_cap, fmt['curr_bold']); _col += 1
        for val in [s_ovh, s_pocket]:
            ws.write(row_idx, _col, val, fmt['curr_bold']); _col += 1
        if show_scenarios:
            ws.write(row_idx, _col, s_opt,  fmt['curr_bold']); _col += 1
            ws.write(row_idx, _col, s_pess, fmt['curr_bold'])
        row_idx += 2

    # ---- Manpower detail -------------------------------------------------
    df_manpower = df_flat[df_flat['קטגוריה'] == 'Manpower']
    if not df_manpower.empty:
        df_mp_std = df_manpower[df_manpower['Calc_Mode'] == 'FTE']
        df_mp_shift = df_manpower[df_manpower['Calc_Mode'].isin(['Daily', 'Hourly'])]

        if not df_mp_std.empty:
            has_sessions = (df_mp_std['כמות שירותי ססיה'] * df_mp_std['עלות ססיה']).sum() > 0
            mp_headers = ["תפקיד / משרה", "עלות שנתית למשרה", "תקנים (FTE)", "סה\"כ עלות בסיס (ללא ססיות)"]
            if has_sessions:
                mp_headers += ["כמות ססיה (שנתי)", "עלות ססיה"]
            mp_headers.append("סה\"כ עלות כוללת")
            if show_scenarios:
                mp_headers += ["סה\"כ אופטימי", "סה\"כ פסימי"]

            ws.merge_range(row_idx, 0, row_idx, len(mp_headers) - 1, "פירוט הוצאות - כוח אדם עלות שנתית", fmt['title_sec'])
            row_idx += 1
            for i, h in enumerate(mp_headers):
                ws.write(row_idx, i, h, fmt['header'])
            row_idx += 1
            s_base_total = 0

            for _, row in df_mp_std.iterrows():
                base_cost = abs(row['סה"כ נטו לכיס'])
                fte = row['כמות שירותים רגילים']
                unit_cost = row['עלות לשירות']
                sess_vol = row['כמות שירותי ססיה']
                sess_price = row['עלות ססיה']
                total_sess = sess_vol * sess_price
                total_combined = base_cost + total_sess
                c_idx = 0

                ws.write(row_idx, c_idx, row['שם שירות'], fmt['normal']); c_idx += 1
                ws.write(row_idx, c_idx, unit_cost, fmt['curr']); c_idx += 1
                ws.write(row_idx, c_idx, fte, fmt['normal']); c_idx += 1
                ws.write(row_idx, c_idx, base_cost, fmt['curr']); c_idx += 1
                if has_sessions:
                    ws.write(row_idx, c_idx, sess_vol, fmt['normal']); c_idx += 1
                    ws.write(row_idx, c_idx, sess_price, fmt['curr']); c_idx += 1
                ws.write(row_idx, c_idx, total_combined, fmt['curr']); c_idx += 1
                if show_scenarios:
                    ws.write(row_idx, c_idx, total_combined * (row['Pct_Opt_Raw'] / 100), fmt['curr']); c_idx += 1
                    ws.write(row_idx, c_idx, total_combined * (row['Pct_Pess_Raw'] / 100), fmt['curr']); c_idx += 1
                s_base_total += total_combined
                row_idx += 1

            total_col = 4 + (2 if has_sessions else 0)
            ws.write(row_idx, 0, "סה\"כ כוח אדם רגיל", fmt['normal_bold'])
            ws.write(row_idx, total_col, s_base_total, fmt['curr_bold'])
            row_idx += 2

        if not df_mp_shift.empty:
            shift_headers = [
                "סוג תורנות/משמרת", "ערך יום/שעה בסיס", "שווי ערך יום/משמרת (בסיס)",
                "אחוז העמסת מעביד", "מקדם תעסוקתי/תוספת", "שווי כולל מקדם/תוספת",
                "כמות משמרות שנתית", "תקינה (מס' עובדים)", "סה\"כ שכר שנתי",
            ]
            ws.merge_range(row_idx, 0, row_idx, 8, "פירוט הוצאות - מסלולי תורנויות ומשמרות", fmt['title_sec'])
            row_idx += 1
            for i, h in enumerate(shift_headers):
                ws.write(row_idx, i, h, fmt['header'])
            row_idx += 1
            s_shift_base = 0

            for _, row in df_mp_shift.iterrows():
                c_mode = row.get('Calc_Mode')
                base_val_raw = row.get('Base_Value') if c_mode == 'Daily' else row.get('Hour_Cost')
                weight_val = row.get('Weight', 1) if c_mode == 'Daily' else row.get('Hours_Per_Shift', 1)
                worth_val = base_val_raw * weight_val
                qty_shifts = row.get('Qty_Shifts_Per_Emp', 1)
                overhead = row.get('Overhead', 0)
                bonus = row.get('Occ_Bonus', 0)
                loaded_val = worth_val * (1 + overhead) * (1 + bonus)
                num_emps = row['כמות שירותים רגילים']
                total_cost = row['סה"כ נטו לכיס']
                c_idx = 0

                ws.write(row_idx, c_idx, row['שם שירות'], fmt['normal']); c_idx += 1
                ws.write(row_idx, c_idx, base_val_raw, fmt['curr']); c_idx += 1
                ws.write(row_idx, c_idx, worth_val, fmt['curr']); c_idx += 1
                ws.write(row_idx, c_idx, overhead, fmt['pct']); c_idx += 1
                ws.write(row_idx, c_idx, bonus, fmt['pct']); c_idx += 1
                ws.write(row_idx, c_idx, loaded_val, fmt['curr']); c_idx += 1
                ws.write(row_idx, c_idx, qty_shifts, fmt['normal']); c_idx += 1
                ws.write(row_idx, c_idx, num_emps, fmt['normal']); c_idx += 1
                ws.write(row_idx, c_idx, total_cost, fmt['curr']); c_idx += 1
                s_shift_base += total_cost
                row_idx += 1

            ws.write(row_idx, 0, "סה\"כ תורנויות", fmt['normal_bold'])
            ws.write(row_idx, 8, s_shift_base, fmt['curr_bold'])
            row_idx += 3

    # ---- Operation detail -----------------------------------------------
    df_op = df_flat[(df_flat['קטגוריה'] == 'Operation') & (df_flat['סוג'] != 'השקעה חד-פעמית')]
    if not df_op.empty:
        op_headers = ["סעיף הוצאה", "עלות יחידה", "כמות", "אחוז ניצולת", "סה\"כ עלות (בסיס)"]
        if show_scenarios:
            op_headers += ["סה\"כ אופטימי", "סה\"כ פסימי"]
        ws.merge_range(row_idx, 0, row_idx, len(op_headers) - 1, "פירוט הוצאות - תפעול שוטף", fmt['title_sec'])
        row_idx += 1
        for i, h in enumerate(op_headers):
            ws.write(row_idx, i, h, fmt['header'])
        row_idx += 1
        so_base = 0

        for _, row in df_op.iterrows():
            ws.write(row_idx, 0, row['שם שירות'], fmt['normal'])
            ws.write(row_idx, 1, row['עלות לשירות'], fmt['curr'])
            ws.write(row_idx, 2, row['כמות שירותים רגילים'], fmt['normal'])
            ws.write(row_idx, 3, 1.0, fmt['pct'])
            ws.write(row_idx, 4, row['סה"כ נטו לכיס'], fmt['curr'])
            if show_scenarios:
                ws.write(row_idx, 5, row['תרחיש אופטימי'], fmt['curr'])
                ws.write(row_idx, 6, row['תרחיש פסימי'], fmt['curr'])
            so_base += row['סה"כ נטו לכיס']
            row_idx += 1

        ws.write(row_idx, 0, "סה\"כ תפעול", fmt['normal_bold'])
        ws.write(row_idx, 4, so_base, fmt['curr_bold'])
        row_idx += 2

    # ---- Investment detail ----------------------------------------------
    df_inv = df_flat[df_flat['סוג'] == 'השקעה חד-פעמית']
    if not df_inv.empty:
        ws.merge_range(row_idx, 0, row_idx, 5, "פירוט השקעות (CAPEX)", fmt['title_sec'])
        row_idx += 1
        inv_headers = ["סעיף השקעה", "עלות יחידה", "כמות", "שנות חיים (פחת)", "סה\"כ השקעה"]
        for i, h in enumerate(inv_headers):
            ws.write(row_idx, i, h, fmt['header'])
        row_idx += 1
        si = 0

        for _, row in df_inv.iterrows():
            ws.write(row_idx, 0, row['שם שירות'], fmt['normal'])
            ws.write(row_idx, 1, row['עלות לשירות'], fmt['curr'])
            ws.write(row_idx, 2, row['כמות שירותים רגילים'], fmt['normal'])
            ws.write(row_idx, 3, row.get('Lifespan', 10), fmt['normal'])
            ws.write(row_idx, 4, row['סה"כ נטו לכיס'], fmt['curr'])
            si += row['סה"כ נטו לכיס']
            row_idx += 1

        ws.write(row_idx, 0, "סה\"כ השקעות", fmt['normal_bold'])
        ws.write(row_idx, 4, si, fmt['curr_bold'])

    row_idx += 3
    if comments:
        ws.write(row_idx, 0, "הערות הכלכלן", fmt['header'])
        row_idx += 1
        for _r in range(row_idx, row_idx + 8):
            ws.set_row(_r, 20)
        ws.merge_range(row_idx, 0, row_idx + 7, 7, comments, fmt['text_box'])

    ws.set_column('A:A', 35)
    ws.set_column('B:K', 18)
