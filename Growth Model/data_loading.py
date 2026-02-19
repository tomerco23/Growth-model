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

        header_idx = -1
        for i, row in df_raw.head(50).iterrows():
            row_str = str(row.values)
            if "קוד" in row_str and "שירות" in row_str and "תעריף" in row_str:
                header_idx = i
                break

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


def _load_hr_costs(xls: pd.ExcelFile, df_hr_structure: pd.DataFrame, msgs: list) -> pd.DataFrame:
    try:
        df_costs_raw = pd.read_excel(xls, 'DB_HR_Costs', header=None)
        header_idx = find_true_header_index(df_costs_raw, ['Maarach', 'Job Desc'], threshold=1)
        if header_idx == -1:
            return df_hr_structure

        df = pd.read_excel(xls, 'DB_HR_Costs', header=header_idx)
        df = _rename_hr_columns(df)

        val_col = next(
            (c for c in df.columns if 'Values' in str(c) or 'ערכים' in str(c)), None
        )
        if 'Job Desc' not in df.columns or not val_col:
            return df_hr_structure

        idx_cols = [c for c in GROUP_COLS if c in df.columns]
        month_cols = [c for c in df.columns if c not in idx_cols + ['Category ID', val_col]]
        for mc in month_cols:
            df[mc] = pd.to_numeric(df[mc], errors='coerce')

        df = df.dropna(subset=idx_cols, how='all')
        pivoted = df.pivot_table(index=idx_cols, columns=val_col, values=month_cols, aggfunc='sum')

        cost_key = [k for k in pivoted.columns.get_level_values(1).unique() if 'סכום' in str(k) or 'שכר' in str(k)]
        emp_key = [k for k in pivoted.columns.get_level_values(1).unique() if 'עובדים' in str(k) or 'מספר' in str(k)]

        if not (cost_key and emp_key):
            return df_hr_structure

        c_k, e_k = cost_key[0], emp_key[0]
        calculated_costs_list = []
        for idx, row in pivoted.iterrows():
            found_cost = 0.0
            for month in reversed(month_cols):
                if (month, c_k) in row.index and (month, e_k) in row.index:
                    cost_val, emp_val = row[(month, c_k)], row[(month, e_k)]
                    if pd.notna(cost_val) and pd.notna(emp_val) and emp_val > 0:
                        found_cost = float(cost_val) / float(emp_val)
                        break
            record = {idx_cols[i]: idx[i] for i in range(len(idx_cols))}
            record['Calculated_Monthly_Cost'] = found_cost
            calculated_costs_list.append(record)

        df_calculated = pd.DataFrame(calculated_costs_list)
        if not df_hr_structure.empty and not df_calculated.empty:
            df_hr_structure = df_hr_structure.merge(df_calculated, on=idx_cols, how='left')
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
        h_srv = df.melt(
            id_vars=['Original_Label'],
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
        df_hr_structure = _load_hr_costs(xls, df_hr_structure, msgs)

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
