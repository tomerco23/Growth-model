import pandas as pd

from constants import CAT_MAP, Category


def calculate_detailed_rows(items: list, params: dict):
    rows = []
    total_capex = 0.0
    total_opex = 0.0
    total_rev = 0.0
    total_prof_base = 0.0
    total_prof_opt = 0.0
    total_prof_pess = 0.0

    for idx, item in enumerate(items):
        cat_eng = item['Category']
        cat_heb = CAT_MAP.get(cat_eng, cat_eng)
        name = item['Name']
        qty = float(item.get('Quantity') or 0.0)
        srv_name = name
        code = ""

        pct_opt_val = item.get('Pct_Opt', 100) / 100.0
        pct_pess_val = item.get('Pct_Pess', 100) / 100.0
        g_y2 = item.get('Growth_Y2', 0) / 100.0
        g_y3 = item.get('Growth_Y3', 0) / 100.0
        g_y4 = item.get('Growth_Y4', 0) / 100.0

        # Shared base row dict — avoids repeating every field each branch
        base_row = {
            "Item_Index": idx,
            "Row_Type": "Main",
            "Category_Heb": cat_heb,
            "קטגוריה": cat_eng,
            "שם שירות": srv_name,
            "קוד שירות": code,
            "Is_One_Time": item.get('Is_One_Time', False),
            "כמות שירותים רגילים": qty,
            "עלות לשירות": 0,
            "כמות שירותי ססיה": 0,
            "עלות ססיה": 0,
            "תעריף יחידה ברוטו": 0,
            "תעריף יחידה אחרי הנחות": 0,
            "תעריף יחידה תחת cap": 0,
            'סה"כ ברוטו': 0,
            'סה"כ אחרי הנחות': 0,
            'סה"כ אחרי קאפ': 0,
            "עלות תקורה": 0,
            'סה"כ נטו לכיס': 0,
            "תרחיש אופטימי": 0,
            "תרחיש פסימי": 0,
            "Pct_Opt_Raw": item.get('Pct_Opt', 100),
            "Pct_Pess_Raw": item.get('Pct_Pess', 100),
            "Net_Y2": 0,
            "Net_Y3": 0,
            "Net_Y4": 0,
        }

        # ---- Investment / one-time CAPEX --------------------------------
        if cat_eng == Category.INVESTMENT or (
            cat_eng == Category.OPERATION and item.get('Is_One_Time')
        ):
            unit_cost = item.get('Unit_Cost') or 0.0
            base_cost = qty * unit_cost
            val_base = -base_cost
            total_capex += base_cost

            row = {
                **base_row,
                "סוג": "השקעה חד-פעמית",
                "עלות לשירות": unit_cost,
                'סה"כ נטו לכיס': val_base,
                "תרחיש אופטימי": -base_cost * pct_opt_val,
                "תרחיש פסימי": -base_cost * pct_pess_val,
                "Lifespan": item.get('Lifespan', 10),
            }
            rows.append(row)

        # ---- Manpower ---------------------------------------------------
        elif cat_eng == Category.MANPOWER:
            unit_cost = item.get('Unit_Cost') or 0.0
            sess_qty = item.get('Sessions', 0)
            sess_cost = item.get('Sess_Price', 0)

            cost_hr_only = qty * unit_cost
            val_base_hr = -cost_hr_only
            total_opex += cost_hr_only

            row = {
                **base_row,
                "סוג": "הוצאה שוטפת",
                "עלות לשירות": unit_cost,
                "כמות שירותי ססיה": sess_qty * 12,
                "עלות ססיה": sess_cost,
                'סה"כ נטו לכיס': val_base_hr,
                "תרחיש אופטימי": val_base_hr * pct_opt_val,
                "תרחיש פסימי": val_base_hr * pct_pess_val,
                "Net_Y2": val_base_hr,
                "Net_Y3": val_base_hr,
                "Net_Y4": val_base_hr,
                "Calc_Mode": item.get('Calc_Mode', 'FTE'),
                "Base_Value": item.get('Base_Value', 0),
                "Weight": item.get('Weight', 0),
                "Qty_Shifts_Per_Emp": item.get('Qty_Shifts_Per_Emp', 0),
                "Overhead": item.get('Overhead', 0),
                "Hour_Cost": item.get('Hour_Cost', 0),
                "Hours_Per_Shift": item.get('Hours_Per_Shift', 0),
                "Occ_Bonus": item.get('Occ_Bonus', 0),
            }
            rows.append(row)

            if sess_qty > 0 and sess_cost > 0:
                val_base_sess = -(sess_qty * sess_cost * 12)
                total_opex += abs(val_base_sess)
                sess_row = {
                    **base_row,
                    "Row_Type": "Session",
                    "Category_Heb": "ססיות כ\"א",
                    "קטגוריה": Category.OPERATION,
                    "סוג": "הוצאה שוטפת",
                    "שם שירות": f"ססיות - {srv_name}",
                    "כמות שירותים רגילים": sess_qty * 12,
                    "עלות לשירות": sess_cost,
                    "כמות שירותי ססיה": sess_qty * 12,
                    "עלות ססיה": sess_cost,
                    'סה"כ נטו לכיס': val_base_sess,
                    "תרחיש אופטימי": val_base_sess * pct_opt_val,
                    "תרחיש פסימי": val_base_sess * pct_pess_val,
                    "Net_Y2": val_base_sess,
                    "Net_Y3": val_base_sess,
                    "Net_Y4": val_base_sess,
                }
                rows.append(sess_row)

            total_prof_base += val_base_hr + (val_base_sess if sess_qty > 0 else 0)
            total_prof_opt += val_base_hr * pct_opt_val + (
                val_base_sess * pct_opt_val if sess_qty > 0 else 0
            )
            total_prof_pess += val_base_hr * pct_pess_val + (
                val_base_sess * pct_pess_val if sess_qty > 0 else 0
            )

        # ---- Recurring operation ----------------------------------------
        elif cat_eng == Category.OPERATION and not item.get('Is_One_Time'):
            unit_cost = item.get('Unit_Cost') or 0.0
            val_base = -(qty * unit_cost)
            total_opex += abs(val_base)

            row = {
                **base_row,
                "סוג": "הוצאה שוטפת",
                "עלות לשירות": unit_cost,
                'סה"כ נטו לכיס': val_base,
                "תרחיש אופטימי": val_base * pct_opt_val,
                "תרחיש פסימי": val_base * pct_pess_val,
                "Net_Y2": val_base,
                "Net_Y3": val_base,
                "Net_Y4": val_base,
            }
            rows.append(row)
            total_prof_base += val_base
            total_prof_opt += val_base * pct_opt_val
            total_prof_pess += val_base * pct_pess_val

        # ---- Revenue ----------------------------------------------------
        elif cat_eng == Category.REVENUE:
            parts = name.split(' - ')
            code = parts[0] if len(parts) > 1 else ""
            srv_name = " - ".join(parts[1:]) if len(parts) > 1 else name

            active_no_show = (
                item.get('Manual_No_Show') / 100.0
                if item.get('Manual_No_Show') is not None
                else params['NO_SHOW_RATE']
            )
            qty_net = qty * (1 - active_no_show) * (0.93 if item.get('Is_New') else 1.0)
            u_gross = item.get('Unit_Revenue') or 0.0

            global_discount_factor = 1 - (params['VOL_DISCOUNT'] + params['APPEALS_PROV'])
            active_discount_factor = (
                1 - (item.get('Manual_Discount_Pct') / 100.0)
                if item.get('Manual_Discount_Pct') is not None
                else global_discount_factor
            )

            if item.get('Is_Private'):
                u_net = u_gross
                u_cap = u_gross
            else:
                u_net = u_gross * active_discount_factor
                u_cap = u_gross * params['CAP_RATE_FACTOR']

            tot_gross = qty_net * u_gross
            tot_net = qty_net * u_net
            tot_cap = qty_net * u_cap
            ovh_cost = tot_net * params['OVERHEAD_RATE']
            net_pocket = tot_net - ovh_cost

            val_base = net_pocket
            total_rev += val_base
            total_prof_base += val_base
            total_prof_opt += val_base * pct_opt_val
            total_prof_pess += val_base * pct_pess_val

            val_y2 = val_base * (1 + g_y2)
            val_y3 = val_y2 * (1 + g_y3)
            val_y4 = val_y3 * (1 + g_y4)

            rev_sess_vol = item.get('Rev_Sess_Vol', 0)
            rev_sess_cost = item.get('Rev_Sess_Cost', 0)

            row = {
                **base_row,
                "סוג": "הכנסה",
                "שם שירות": srv_name,
                "קוד שירות": code,
                "תעריף יחידה ברוטו": u_gross,
                "תעריף יחידה אחרי הנחות": u_net,
                "תעריף יחידה תחת cap": u_cap,
                'סה"כ ברוטו': tot_gross,
                'סה"כ אחרי הנחות': tot_net,
                'סה"כ אחרי קאפ': tot_cap,
                "עלות תקורה": ovh_cost,
                'סה"כ נטו לכיס': val_base,
                "תרחיש אופטימי": val_base * pct_opt_val,
                "תרחיש פסימי": val_base * pct_pess_val,
                "כמות שירותי ססיה": rev_sess_vol,
                "עלות ססיה": rev_sess_cost,
                "Net_Y2": val_y2,
                "Net_Y3": val_y3,
                "Net_Y4": val_y4,
            }
            rows.append(row)

            if rev_sess_vol > 0 and rev_sess_cost > 0:
                val_base_rs = -(rev_sess_vol * rev_sess_cost)
                sess_row = {
                    **base_row,
                    "Row_Type": "SessionInfo",
                    "Category_Heb": "ססיות (למידע)",
                    "קטגוריה": Category.OPERATION,
                    "סוג": "הוצאה שוטפת",
                    "שם שירות": f"תחשיב ססיות (מידע) - {srv_name}",
                    "קוד שירות": code,
                    "כמות שירותים רגילים": rev_sess_vol,
                    "עלות לשירות": rev_sess_cost,
                    "כמות שירותי ססיה": rev_sess_vol,
                    "עלות ססיה": rev_sess_cost,
                    'סה"כ נטו לכיס': val_base_rs,
                    "תרחיש אופטימי": val_base_rs * pct_opt_val,
                    "תרחיש פסימי": val_base_rs * pct_pess_val,
                    "Net_Y2": val_base_rs,
                    "Net_Y3": val_base_rs,
                    "Net_Y4": val_base_rs,
                }
                rows.append(sess_row)

    roi = (total_capex / total_prof_base) if total_prof_base > 0 else 0
    return (
        pd.DataFrame(rows),
        total_capex,
        total_opex,
        total_rev,
        total_prof_base,
        total_prof_opt,
        total_prof_pess,
        roi,
    )
