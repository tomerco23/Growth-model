import numpy as np
import pandas as pd
import streamlit as st

from utils import (
    normalize_code,
    clean_currency,
    find_true_header_index,
    extract_clean_code_from_string,
)


# ---------------------------------------------------------------------------
# MOH price-list parser
# ---------------------------------------------------------------------------

@st.cache_data(ttl=3600, show_spinner=False)
def parse_moh_file(uploaded_file):
    try:
        filename = uploaded_file.name
        file_ext = filename.split('.')[-1].lower()

        if 'csv' in file_ext:
            try:
                df_raw = pd.read_csv(uploaded_file, header=None, encoding='utf-8', dtype=str)
            except UnicodeDecodeError:
                df_raw = pd.read_csv(uploaded_file, header=None, encoding='windows-1255', dtype=str)
        else:
            df_raw = pd.read_excel(uploaded_file, header=None, dtype=str)

        header_idx = find_true_header_index(df_raw, ["קוד", "שירות", "תעריף"], threshold=3)

        if header_idx != -1:
            uploaded_file.seek(0)
            if 'csv' in file_ext:
                try:
                    df = pd.read_csv(uploaded_file, header=header_idx, encoding='utf-8', dtype=str)
                except UnicodeDecodeError:
                    df = pd.read_csv(uploaded_file, header=header_idx, encoding='windows-1255', dtype=str)
            else:
                df = pd.read_excel(uploaded_file, header=header_idx, dtype=str)

            col_code = next(
                (c for c in df.columns if "קוד" in str(c) and "שירות" in str(c)), None
            )
            col_name = next(
                (c for c in df.columns if "שם" in str(c) and "שירות" in str(c)), None
            )
            col_tariff = next(
                (c for c in df.columns if "תעריף" in str(c) and ("ב" in str(c) or "B" in str(c))),
                None,
            )
            if not col_tariff:
                col_tariff = next(
                    (
                        c for c in df.columns
                        if "תעריף" in str(c)
                        and "א" not in str(c)
                        and "ג" not in str(c)
                        and "חו" not in str(c)
                    ),
                    None,
                )

            if col_code and col_tariff:
                final = df[[col_code, col_name if col_name else col_code, col_tariff]].copy()
                final.columns = ['Code', 'Name', 'Tariff']
                final['Code'] = final['Code'].apply(normalize_code)
                final['Tariff'] = final['Tariff'].apply(clean_currency)
                result = final.dropna(subset=['Code', 'Tariff'])
                return result, f"✅ {filename}: נטענו {len(result)} שירותים"

        return None, f"❌ {filename}: מבנה לא מזוהה"

    except Exception as e:
        return None, f"❌ {uploaded_file.name}: {str(e)}"


# ---------------------------------------------------------------------------
# Main internal file loader
# ---------------------------------------------------------------------------

def _rename_hr_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename_map = {
        'מערך': 'Maarach',
        'אגף': 'Agaf',
        'חטיבה': 'Hativa',
        'מחלקה': 'Machleket Em',
        'יחידה': 'Yahida',
        'סקטור': 'Sector',
        'תפקיד': 'Job Desc',
    }
    df.rename(columns=rename_map, inplace=True)

    if 'Job Desc' not in df.columns:
        job_col = next(
            (c for c in df.columns if 'תפקיד' in str(c) or 'Job' in str(c)), None
        )
        if job_col:
            df.rename(columns={job_col: 'Job Desc'}, inplace=True)

    if 'Sector' not in df.columns:
        sec_col = next(
            (c for c in df.columns if 'סקטור' in str(c) or 'Sector' in str(c)), None
        )
        if sec_col:
            df.rename(columns={sec_col: 'Sector'}, inplace=True)

    return df


GROUP_COLS = ['Maarach', 'Agaf', 'Hativa', 'Machleket Em', 'Yahida', 'Sector', 'Job Desc']
EXCLUDE_ID_COLS = [
    'Category ID', 'Job Code', 'Code', 'ID', 'Name',
    'First Name', 'Last Name', 'ת.ז', 'שם פרטי', 'שם משפחה',
]


def _load_hr_staffing(xls: pd.ExcelFile, msgs: list):
    df_hr_structure = pd.DataFrame()
    df_hr_counts = pd.DataFrame()
    try:
        df_raw = pd.read_excel(xls, 'DB_HR_Staffing', header=None)
        header_idx = find_true_header_index(df_raw, ['Maarach', 'Job Desc'], threshold=1)
        if header_idx != -1:
            df = pd.read_excel(xls, 'DB_HR_Staffing', header=header_idx)
            df = _rename_hr_columns(df)

            valid_group_cols = [c for c in GROUP_COLS if c in df.columns]
            exclude_cols = valid_group_cols + EXCLUDE_ID_COLS
            value_cols = [c for c in df.columns if c not in exclude_cols]

            for vc in value_cols:
                df[vc] = pd.to_numeric(df[vc], errors='coerce')

            df['__Total_FTE__'] = df[value_cols].sum(axis=1, min_count=0).fillna(1)

            if valid_group_cols:
                df_hr_counts = (
                    df.groupby(valid_group_cols)['__Total_FTE__']
                    .sum()
                    .reset_index(name='Existing_FTE')
                )

            keep_cols = [c for c in GROUP_COLS if c in df.columns]
            if keep_cols:
                df_hr_structure = df[keep_cols].drop_duplicates()
    except Exception as e:
        msgs.append(f"שגיאה בטעינת Staffing: {str(e)}")

    return df_hr_structure, df_hr_counts


def _load_hr_costs(
    xls: pd.ExcelFile,
    df_hr_structure: pd.DataFrame,
    df_hr_counts: pd.DataFrame,
    msgs: list,
) -> pd.DataFrame:
    try:
        df_costs_raw = pd.read_excel(xls, 'DB_HR_Costs', header=None)
        header_idx = find_true_header_index(df_costs_raw, ['Maarach', 'Job Desc'], threshold=1)
        if header_idx == -1:
            return df_hr_structure

        df = pd.read_excel(xls, 'DB_HR_Costs', header=header_idx)
        df = _rename_hr_columns(df)

        if 'Job Desc' not in df.columns:
            return df_hr_structure

        val_col = next(
            (c for c in df.columns if 'Values' in str(c) or 'ערכים' in str(c)), None
        )
        idx_cols = [c for c in GROUP_COLS if c in df.columns]
        df_calculated = None  # set in one of the two branches below

        if val_col:
            # ── OLD FORMAT: Values pivot column (עלות כ״א + עלות משרות) ──────
            month_cols = [c for c in df.columns if c not in idx_cols + ['Category ID', val_col]]
            for mc in month_cols:
                df[mc] = pd.to_numeric(df[mc], errors='coerce')

            df = df.dropna(subset=idx_cols, how='all')
            pivoted = df.pivot_table(index=idx_cols, columns=val_col, values=month_cols, aggfunc='sum')

            cost_key = [k for k in pivoted.columns.get_level_values(1).unique()
                        if 'סכום' in str(k) or 'שכר' in str(k)
                        or ('עלות' in str(k) and 'משרות' not in str(k))]
            emp_key = [k for k in pivoted.columns.get_level_values(1).unique()
                       if 'עובדים' in str(k) or 'מספר' in str(k) or 'משרות' in str(k)]

            if not (cost_key and emp_key):
                return df_hr_structure

            c_k, e_k = cost_key[0], emp_key[0]
            valid_months = [m for m in month_cols
                            if (m, c_k) in pivoted.columns and (m, e_k) in pivoted.columns]

            # to_frame() handles both single-level and MultiIndex correctly
            df_calculated = pivoted.index.to_frame(index=False)
            df_calculated.columns = idx_cols
            df_calculated['Calculated_Monthly_Cost'] = 0.0

            if valid_months:
                cost_m = pivoted[[(m, c_k) for m in valid_months]].copy()
                emp_m  = pivoted[[(m, e_k) for m in valid_months]].copy()
                cost_m.columns = valid_months
                emp_m.columns  = valid_months

                valid_mask = cost_m.notna() & emp_m.notna() & (emp_m > 0)
                unit_cost  = (cost_m / emp_m).where(valid_mask)

                # Take most-recent valid month per row (vectorized, no iterrows)
                rev_months = list(reversed(valid_months))
                valid_rev  = unit_cost[rev_months].notna().to_numpy(dtype=bool)
                has_valid  = valid_rev.any(axis=1)
                vals       = unit_cost[rev_months].to_numpy(dtype=float)
                first_pos  = valid_rev.argmax(axis=1)
                df_calculated['Calculated_Monthly_Cost'] = np.where(
                    has_valid, vals[np.arange(len(vals)), first_pos], 0.0
                )

        else:
            # ── NEW FORMAT: direct monthly cost columns, Sector rows ──────────
            # Each row = one dept+job+sector combo; columns = monthly cost values.
            month_cols = [c for c in df.columns if c not in idx_cols + ['Category ID']]
            for mc in month_cols:
                df[mc] = pd.to_numeric(df[mc], errors='coerce')

            df = df.dropna(subset=idx_cols, how='all')

            # Drop exception rows where Sector starts with '-' (e.g. '-9-חר...')
            if 'Sector' in df.columns:
                df = df[~df['Sector'].astype(str).str.startswith('-', na=False)]

            # Group by all idx_cols (including Sector) → total monthly cost per group
            grp = df.groupby(idx_cols)[month_cols].sum()
            n_months = len(month_cols)

            # Vectorized: most-recent non-zero valid month's total cost per row
            grp_vals = grp.to_numpy(dtype=float)
            rev_vals  = grp_vals[:, ::-1]
            valid_rev = np.isfinite(rev_vals) & (rev_vals > 0)
            has_valid = valid_rev.any(axis=1)
            first_pos = valid_rev.argmax(axis=1)
            latest_total = np.where(
                has_valid, rev_vals[np.arange(len(rev_vals)), first_pos], 0.0
            )

            df_calculated = grp.reset_index()[idx_cols].copy()
            df_calculated['_total_cost'] = latest_total

            # Per-employee monthly cost = total_cost / avg_monthly_fte
            # avg_monthly_fte = Existing_FTE (sum across all months) / n_months
            if not df_hr_counts.empty and 'Existing_FTE' in df_hr_counts.columns:
                fte_key = [c for c in idx_cols if c in df_hr_counts.columns]
                df_calculated = df_calculated.merge(
                    df_hr_counts[fte_key + ['Existing_FTE']], on=fte_key, how='left'
                )
                avg_fte = (
                    df_calculated['Existing_FTE'].fillna(1) / max(n_months, 1)
                ).clip(lower=0.1)
            else:
                avg_fte = pd.Series(1.0, index=df_calculated.index)

            df_calculated['Calculated_Monthly_Cost'] = df_calculated['_total_cost'] / avg_fte

        # ── Merge calculated costs into df_hr_structure ───────────────────────
        if df_calculated is not None and not df_hr_structure.empty and not df_calculated.empty:
            merge_key = [c for c in idx_cols if c in df_hr_structure.columns]
            df_hr_structure = df_hr_structure.merge(
                df_calculated[merge_key + ['Calculated_Monthly_Cost']], on=merge_key, how='left'
            )
            df_hr_structure['Monthly_Cost'] = df_hr_structure['Calculated_Monthly_Cost'].fillna(0)
            df_hr_structure['Annual_Cost'] = df_hr_structure['Monthly_Cost'] * 12
            msgs.append("✅ נטענו תעריפי שכר מדויקים פר-מחלקה (לפי נתוני החודש האחרון הזמין)")

    except Exception as e:
        msgs.append(f"⚠️ שגיאה בטעינת מחירון עלויות: {str(e)}")

    return df_hr_structure


def _load_service_hierarchy(xls: pd.ExcelFile, msgs: list):
    df_srv_hier_map = pd.DataFrame()
    h_srv = pd.DataFrame()
    try:
        df_srv_count_raw = pd.read_excel(xls, 'DB_Service_count', header=None)
        header_idx_flat = find_true_header_index(
            df_srv_count_raw, ['Maarach', 'Agaf', 'Code Desc'], threshold=2
        )
        if header_idx_flat == -1:
            return df_srv_hier_map, h_srv

        df = pd.read_excel(xls, 'DB_Service_count', header=header_idx_flat)
        rename_map_srv = {
            'Code Desc': 'Original_Label',
            'Machleket Em Key': 'Machleket Em',
            'Yahida Key': 'Yahida',
        }
        df.rename(columns=rename_map_srv, inplace=True)

        if 'Original_Label' in df.columns:
            df['Code'] = df['Original_Label'].apply(extract_clean_code_from_string)
        else:
            df['Code'] = None

        hier_cols = ['Maarach', 'Agaf', 'Hativa', 'Machleket Em', 'Yahida', 'Original_Label', 'Code']
        existing_cols = [c for c in hier_cols if c in df.columns]
        df_srv_hier_map = (
            df[existing_cols].copy()
            .drop_duplicates(subset=['Code'])
            .fillna("-")
        )

        value_vars = [
            c for c in df.columns
            if c not in existing_cols and 'Unnamed' not in str(c)
        ]
        dept_id_vars = [
            c for c in ['Maarach', 'Agaf', 'Hativa', 'Machleket Em', 'Yahida', 'Original_Label']
            if c in df.columns
        ]
        h_srv = df.melt(
            id_vars=dept_id_vars,
            value_vars=value_vars,
            var_name='Date',
            value_name='Value',
        )

    except Exception as e:
        msgs.append(f"שגיאה בעיבוד היסטוריה: {str(e)}")

    return df_srv_hier_map, h_srv


@st.cache_data(
    ttl=3600,
    show_spinner="טוען ומעבד נתונים (תקנים, עלויות ושירותים)...",
)
def load_growth_data(file_internal, file_external_list):
    msgs = []
    try:
        xls = pd.ExcelFile(file_internal)

        df_hr_structure, df_hr_counts = _load_hr_staffing(xls, msgs)
        df_hr_structure = _load_hr_costs(xls, df_hr_structure, df_hr_counts, msgs)

        df_hr = df_hr_structure.copy() if not df_hr_structure.empty else pd.DataFrame()
        if 'Annual_Cost' not in df_hr.columns:
            df_hr['Annual_Cost'] = 0
            df_hr['Monthly_Cost'] = 0
        df_hr = df_hr.fillna("-")

        # External price lists
        df_srv_prices = pd.DataFrame(columns=['Code', 'Name', 'Tariff'])
        if file_external_list:
            dfs = []
            for f in file_external_list:
                d, m = parse_moh_file(f)
                msgs.append(m)
                if d is not None:
                    dfs.append(d)
            if dfs:
                full = pd.concat(dfs, ignore_index=True)
                full['Code'] = full['Code'].apply(normalize_code)
                df_srv_prices = full.drop_duplicates(subset=['Code'], keep='last')
        else:
            msgs.append("⚠️ לא הועלו מחירונים")

        df_srv_hier_map, h_srv = _load_service_hierarchy(xls, msgs)

        k_hr = 'Job Desc'
        k_srv = 'Original_Label'
        h_hr = pd.DataFrame()

        return df_hr, df_srv_prices, df_srv_hier_map, df_hr_counts, h_srv, k_hr, k_srv, msgs

    except Exception as e:
        return None, None, None, None, None, None, None, [f"קריסה כללית בטעינה: {str(e)}"]


# ---------------------------------------------------------------------------
# Employee-count loader  (מספר עובדים מ-DB_HR_Costs)
# ---------------------------------------------------------------------------

@st.cache_data(ttl=3600, show_spinner=False)
def load_employee_counts(file_internal) -> pd.DataFrame:
    """
    טוען ספירת עובדים חודשית לחישוב תפוקה שולית.

    מחזיר DataFrame עם עמודות:
        [GROUP_COLS..., 'Total_Employee_Months', 'Avg_Monthly_Employees', 'Months_Count']

    פורמט חדש: קורא מ-DB_HR_Staffing (ערכי FTE חודשיים ישירות, ללא pivot).
    פורמט ישן: קורא מ-DB_HR_Costs עם עמודת Values (pivot "מספר עובדים").
    """
    try:
        xls = pd.ExcelFile(file_internal)

        # ── NEW FORMAT: DB_HR_Staffing has direct monthly FTE values ─────────
        if 'DB_HR_Staffing' in xls.sheet_names:
            try:
                df_raw = pd.read_excel(xls, 'DB_HR_Staffing', header=None)
                header_idx = find_true_header_index(df_raw, ['Maarach', 'Job Desc'], threshold=1)
                if header_idx != -1:
                    df = pd.read_excel(xls, 'DB_HR_Staffing', header=header_idx)
                    df = _rename_hr_columns(df)

                    if 'Job Desc' in df.columns:
                        idx_cols = [c for c in GROUP_COLS if c in df.columns]
                        month_cols = [c for c in df.columns if c not in idx_cols + ['Category ID']]
                        for mc in month_cols:
                            df[mc] = pd.to_numeric(df[mc], errors='coerce')
                        df = df.dropna(subset=idx_cols, how='all')

                        emp_data = df.groupby(idx_cols)[month_cols].sum().reset_index()
                        emp_data['Total_Employee_Months'] = emp_data[month_cols].fillna(0).sum(axis=1)
                        emp_data['Avg_Monthly_Employees'] = emp_data[month_cols].fillna(0).mean(axis=1)
                        emp_data['Months_Count'] = len(month_cols)

                        result = emp_data[idx_cols + ['Total_Employee_Months', 'Avg_Monthly_Employees', 'Months_Count']]
                        if not result.empty:
                            return result
            except Exception:
                pass  # fall through to old-format path

        # ── OLD FORMAT: DB_HR_Costs with Values pivot ─────────────────────────
        df_raw = pd.read_excel(xls, 'DB_HR_Costs', header=None)
        header_idx = find_true_header_index(df_raw, ['Maarach', 'Job Desc'], threshold=1)
        if header_idx == -1:
            return pd.DataFrame()

        df = pd.read_excel(xls, 'DB_HR_Costs', header=header_idx)
        df = _rename_hr_columns(df)

        val_col = next(
            (c for c in df.columns if 'Values' in str(c) or 'ערכים' in str(c)), None
        )
        if 'Job Desc' not in df.columns or not val_col:
            return pd.DataFrame()

        idx_cols = [c for c in GROUP_COLS if c in df.columns]
        month_cols = [c for c in df.columns if c not in idx_cols + ['Category ID', val_col]]
        for mc in month_cols:
            df[mc] = pd.to_numeric(df[mc], errors='coerce')

        df = df.dropna(subset=idx_cols, how='all')
        pivoted = df.pivot_table(index=idx_cols, columns=val_col, values=month_cols, aggfunc='sum')

        # מחפש את מפתח "מספר עובדים" / "עלות משרות"
        emp_key = next(
            (k for k in pivoted.columns.get_level_values(1).unique()
             if 'עובדים' in str(k) or 'מספר' in str(k) or 'משרות' in str(k)), None
        )
        if not emp_key:
            return pd.DataFrame()

        emp_cols = [c for c in pivoted.columns if c[1] == emp_key]
        if not emp_cols:
            return pd.DataFrame()

        emp_data = pivoted[emp_cols].copy()
        emp_data.columns = [m for m, _ in emp_cols]   # flatten → שמות חודשים בלבד
        emp_data = emp_data.reset_index()

        month_names = [m for m, _ in emp_cols]
        emp_data['Total_Employee_Months'] = (
            emp_data[month_names].apply(pd.to_numeric, errors='coerce').fillna(0).sum(axis=1)
        )
        emp_data['Avg_Monthly_Employees'] = (
            emp_data[month_names].apply(pd.to_numeric, errors='coerce').fillna(0).mean(axis=1)
        )
        emp_data['Months_Count'] = len(month_names)

        return emp_data[idx_cols + ['Total_Employee_Months', 'Avg_Monthly_Employees', 'Months_Count']]

    except Exception:
        return pd.DataFrame()


