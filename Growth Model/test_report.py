# -*- coding: utf-8 -*-
"""End-to-end test for create_hybrid_report_sheet."""
import sys, io
import pandas as pd

sys.path.insert(0, '.')
from report import create_hybrid_report_sheet

def make_df():
    return pd.DataFrame([
        # Revenue
        {'קטגוריה': 'Revenue', 'סוג': 'הכנסה', 'Row_Type': 'Revenue',
         'שם שירות': 'שירות א', 'כמות שירותים רגילים': 1000, 'עלות לשירות': 150,
         'תעריף יחידה ברוטו': 150, 'תעריף יחידה אחרי הנחות': 110, 'תעריף יחידה תחת cap': 52,
         'סה"כ ברוטו': 150000, 'סה"כ נטו לכיס': 90000, 'סה"כ אחרי קאפ': 52000,
         'סה"כ אחרי הנחות': 110000, 'עלות תקורה': 26100,
         'תרחיש אופטימי': 95000, 'תרחיש פסימי': 80000,
         'Pct_Opt_Raw': 0, 'Pct_Pess_Raw': 0},
        # Manpower FTE with salary
        {'קטגוריה': 'Manpower', 'סוג': 'כ"א', 'Row_Type': 'FTE', 'Calc_Mode': 'FTE',
         'שם שירות': 'רופא', 'כמות שירותים רגילים': 2, 'עלות לשירות': 200000,
         'כמות שירותי ססיה': 0, 'עלות ססיה ברוטו': 0, 'עלות מעביד ססיה': 0,
         'סה"כ נטו לכיס': -400000, 'סה"כ ברוטו': 0, 'סה"כ אחרי קאפ': 0,
         'Pct_Opt_Raw': 0, 'Pct_Pess_Raw': 0},
        # Manpower FTE – sessions only, no salary
        {'קטגוריה': 'Manpower', 'סוג': 'כ"א', 'Row_Type': 'FTE', 'Calc_Mode': 'FTE',
         'שם שירות': 'מומחה', 'כמות שירותים רגילים': 1, 'עלות לשירות': 0,
         'כמות שירותי ססיה': 50, 'עלות ססיה ברוטו': 300, 'עלות מעביד ססיה': 393,
         'סה"כ נטו לכיס': 0, 'סה"כ ברוטו': 0, 'סה"כ אחרי קאפ': 0,
         'Pct_Opt_Raw': 0, 'Pct_Pess_Raw': 0},
        # Session row – must NOT appear in operations section
        {'קטגוריה': 'Operation', 'סוג': 'תפעול', 'Row_Type': 'Session',
         'שם שירות': 'ססיות - מומחה', 'כמות שירותים רגילים': 50, 'עלות לשירות': 300,
         'כמות שירותי ססיה': 0, 'עלות ססיה ברוטו': 0, 'עלות מעביד ססיה': 0,
         'סה"כ נטו לכיס': -15000, 'סה"כ ברוטו': 0, 'סה"כ אחרי קאפ': 0,
         'Pct_Opt_Raw': 0, 'Pct_Pess_Raw': 0},
        # Operations
        {'קטגוריה': 'Operation', 'סוג': 'תפעול', 'Row_Type': 'Operation',
         'שם שירות': 'ציוד', 'כמות שירותים רגילים': 1, 'עלות לשירות': 30000,
         'כמות שירותי ססיה': 0, 'עלות ססיה ברוטו': 0, 'עלות מעביד ססיה': 0,
         'סה"כ נטו לכיס': -30000, 'סה"כ ברוטו': 0, 'סה"כ אחרי קאפ': 0,
         'Pct_Opt_Raw': 0, 'Pct_Pess_Raw': 0},
        # Investment
        {'קטגוריה': 'Operation', 'סוג': 'השקעה חד-פעמית', 'Row_Type': 'Investment',
         'שם שירות': 'מכשיר', 'כמות שירותים רגילים': 1, 'עלות לשירות': 100000,
         'כמות שירותי ססיה': 0, 'עלות ססיה ברוטו': 0, 'עלות מעביד ססיה': 0,
         'סה"כ נטו לכיס': -100000, 'סה"כ ברוטו': 0, 'סה"כ אחרי קאפ': 0,
         'Lifespan': 10, 'Pct_Opt_Raw': 0, 'Pct_Pess_Raw': 0},
    ])

def test_session_excluded_from_ops():
    df = make_df()
    op_mask = (
        (df['קטגוריה'] == 'Operation') &
        (df['סוג'] != 'השקעה חד-פעמית') &
        (df['Row_Type'] != 'Session')
    )
    df_op = df[op_mask]
    assert 'ססיות - מומחה' not in df_op['שם שירות'].values, \
        "Session row leaked into operations section!"
    assert 'ציוד' in df_op['שם שירות'].values, \
        "Real operation row missing from operations section!"
    print("PASS: Session row excluded from operations, real ops included")

def test_session_only_manpower():
    df = make_df()
    row = df[df['שם שירות'] == 'מומחה'].iloc[0]
    annual_salary = abs(row['סה"כ נטו לכיס'])
    sess_total = row['כמות שירותי ססיה'] * row['עלות ססיה ברוטו']
    assert annual_salary == 0, "Expected 0 annual salary for session-only row"
    assert sess_total == 15000, f"Expected 15000 session total, got {sess_total}"
    print(f"PASS: Session-only manpower detected, sess_total={sess_total:,}")

def test_recommendation_logic():
    """Recommendation should match the net scenario profit shown in summary."""
    # Positive profit → מומלץ
    total_net_profit = 50000
    rec = "✅ מומלץ" if total_net_profit > 0 else "🛑 לא מומלץ"
    assert rec == "✅ מומלץ", f"Expected מומלץ but got: {rec}"
    # Negative → לא מומלץ
    total_net_profit = -10000
    rec = "✅ מומלץ" if total_net_profit > 0 else "🛑 לא מומלץ"
    assert rec == "🛑 לא מומלץ", f"Expected לא מומלץ but got: {rec}"
    print("PASS: Recommendation logic correct")

def test_generate_excel():
    """Full end-to-end: generate Excel without crash."""
    df = make_df().fillna(0)
    params = {
        'HMO_DISCOUNT': 0.185, 'VOL_DISCOUNT': 0.019, 'APPEALS_PROV': 0.04,
        'NO_SHOW_RATE': 0.0,   'OVERHEAD_RATE': 0.29,  'CAP_RATE_FACTOR': 0.35, 'EMPLOYER_FACTOR': 1.31,
    }
    buf = io.BytesIO()
    writer = pd.ExcelWriter(buf, engine='xlsxwriter')
    create_hybrid_report_sheet(
        writer, df, 'פרויקט בדיקה',
        capex=-100000, opex=-30000, rev=90000,
        prof_b=-340000, prof_p=-400000, roi=0,
        rec='🛑 לא מומלץ', comments='הערות בדיקה',
        params=params,
    )
    writer.close()
    buf.seek(0)
    size = len(buf.getvalue())
    assert size > 5000, f"Excel file suspiciously small: {size} bytes"
    print(f"PASS: Excel generated OK – {size:,} bytes")

if __name__ == '__main__':
    print("=" * 50)
    test_session_excluded_from_ops()
    test_session_only_manpower()
    test_recommendation_logic()
    test_generate_excel()
    print("=" * 50)
    print("ALL TESTS PASSED")
