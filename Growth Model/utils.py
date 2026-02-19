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
    for i, row in df.head(50).iterrows():
        row_str = " ".join(row.astype(str).fillna("").values).lower()
        if sum(1 for kw in required_keywords if kw.lower() in row_str) >= threshold:
            return i
    return -1


# ---------------------------------------------------------------------------
# Session-state data validation
# ---------------------------------------------------------------------------

def check_data_health(growth_items: list) -> HealthIssue:
    critical_fields = {
        'Quantity': 'כמות / תקנים',
        'Unit_Cost': 'עלות ליחידה',
        'Unit_Revenue': 'תעריף',
        'Pct_Opt': 'אחוז אופטימי',
        'Pct_Pess': 'אחוז פסימי',
    }
    for i, item in enumerate(growth_items):
        name = item.get('Name', 'ללא שם')
        for field_key, heb_name in critical_fields.items():
            val = item.get(field_key)
            is_missing = val is None or (isinstance(val, float) and np.isnan(val))
            if is_missing:
                return HealthIssue(
                    has_issue=True,
                    message=f"בשורה **{i + 1}** ('{name}'), נמחק הערך בעמודה **{heb_name}**.",
                    row_index=i,
                    field=field_key,
                )
    return HealthIssue(has_issue=False)
