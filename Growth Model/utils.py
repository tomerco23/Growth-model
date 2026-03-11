import re
import numpy as np
import pandas as pd
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Data-health result
# ---------------------------------------------------------------------------

@dataclass
class HealthIssue:
    has_issue: bool
    message: str = ""
    row_index: int = -1
    field: str = ""


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------

def has_hebrew(text: str) -> bool:
    return any("\u0590" <= c <= "\u05EA" for c in str(text))


def format_number_str(num) -> str:
    if num is None:
        return ""
    try:
        val = float(num)
        if pd.isna(val) or val in (float('inf'), float('-inf')):
            return "0"
    except (TypeError, ValueError):
        return "0"
    if abs(val) >= 1000:
        return f"{val:,.0f}"
    return f"{val:,.2f}"


# ---------------------------------------------------------------------------
# Code / currency normalisation
# ---------------------------------------------------------------------------

def normalize_code(code) -> str | None:
    if pd.isna(code) or code is None or str(code).strip() == "":
        return None
    s = str(code).strip().strip('"').strip("'")
    if s.endswith('.0'):
        s = s[:-2]
    s = s.lstrip('0')
    return "0" if s == "" else s


def clean_currency(x):
    if isinstance(x, str):
        clean = re.sub(r'[^\d.]', '', x)
        return pd.to_numeric(clean, errors='coerce')
    return x


def extract_clean_code_from_string(val) -> str | None:
    val = str(val).strip().strip('"')
    if '-' in val:
        parts = val.split('-', 1)
        pot_code = parts[0].strip()
        if not has_hebrew(pot_code) and (
            any(c.isdigit() for c in pot_code) or len(pot_code) > 1
        ):
            return normalize_code(pot_code)
    return normalize_code(val)


# ---------------------------------------------------------------------------
# DataFrame helpers
# ---------------------------------------------------------------------------

def find_true_header_index(df: pd.DataFrame, required_keywords: list, threshold: int = 1) -> int:
    head = df.head(50).fillna("").astype(str)
    if head.empty or required_keywords == []:
        return -1
    row_strings = head.iloc[:, 0].str.lower()
    for col in head.columns[1:]:
        row_strings = row_strings + " " + head[col].str.lower()
    counts = sum(row_strings.str.contains(kw.lower(), regex=False) for kw in required_keywords)
    matches = counts[counts >= threshold]
    return int(matches.index[0]) if not matches.empty else -1


# ---------------------------------------------------------------------------
# Session-state data validation
# ---------------------------------------------------------------------------

_FIELD_NAMES_HEB = {
    'Quantity':     'כמות / תקנים',
    'Unit_Cost':    'עלות ליחידה',
    'Unit_Revenue': 'תעריף',
    'Pct_Opt':      'אחוז אופטימי',
    'Pct_Pess':     'אחוז פסימי',
}
_COMMON_FIELDS = ['Quantity', 'Pct_Opt', 'Pct_Pess']
_FIELDS_BY_CATEGORY = {
    'Revenue':    _COMMON_FIELDS + ['Unit_Revenue'],
    'Manpower':   _COMMON_FIELDS + ['Unit_Cost'],
    'Operation':  _COMMON_FIELDS + ['Unit_Cost'],
    'Investment': _COMMON_FIELDS + ['Unit_Cost'],
}


def check_data_health(growth_items: list) -> HealthIssue:
    for i, item in enumerate(growth_items):
        name = item.get('Name', 'ללא שם')
        cat = item.get('Category', '')
        fields = _FIELDS_BY_CATEGORY.get(cat, _COMMON_FIELDS)
        for field_key in fields:
            val = item.get(field_key)
            is_missing = val is None or (isinstance(val, float) and np.isnan(val))
            if is_missing:
                return HealthIssue(
                    has_issue=True,
                    message=f"בשורה **{i + 1}** ('{name}'), נמחק הערך בעמודה **{_FIELD_NAMES_HEB[field_key]}**.",
                    row_index=i,
                    field=field_key,
                )
    return HealthIssue(has_issue=False)
