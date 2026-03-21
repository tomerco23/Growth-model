import re
import html as _html_mod
import concurrent.futures
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


# ---------------------------------------------------------------------------
# Rich-text helpers (Quill HTML ↔ Excel)
# ---------------------------------------------------------------------------

def is_html(text: str) -> bool:
    """Return True only when text contains an HTML opening tag (e.g. <p>, <h1>).
    Uses a strict regex to avoid false positives on plain text with > or <."""
    return bool(text and re.search(r'<[a-zA-Z]', text))


def strip_html(html: str) -> str:
    """Remove all HTML tags and return plain text (no entity decoding)."""
    return re.sub(r'<[^>]+>', '', html).strip()


def html_to_plain_text(html: str) -> str:
    """Convert Quill HTML to readable plain text with proper line breaks.

    Handles <br>, </p>, </li> -> newline; decodes &nbsp; &amp; etc.
    """
    NL = chr(10)
    text = re.sub(r'<br\s*/?>', NL, html, flags=re.IGNORECASE)
    text = re.sub(r'</p>', NL, text, flags=re.IGNORECASE)
    text = re.sub(r'</li>', NL, text, flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', '', text)
    text = _html_mod.unescape(text)
    while NL * 3 in text:
        text = text.replace(NL * 3, NL * 2)
    text = text.replace(chr(160), chr(32))  # &nbsp; -> regular space
    return text.strip()


def _render_html_sync(html: str, width_px: int) -> bytes:
    """Internal: render HTML to PNG bytes using Playwright (called in a thread)."""
    from playwright.sync_api import sync_playwright  # noqa: PLC0415

    wrapper = f"""<!DOCTYPE html>
<html dir="rtl" lang="he">
<head>
<meta charset="utf-8">
<style>
  *, *::before, *::after {{ box-sizing: border-box; }}
  html, body {{
    margin: 0; padding: 12px;
    width: {width_px}px;
    overflow: hidden;
    font-family: Arial, sans-serif;
    font-size: 13px;
    line-height: 1.6;
    direction: rtl;
    text-align: right;
    background: #FFFFCC;
  }}
  h1 {{ font-size: 20px; margin: 8px 0 4px; }}
  h2 {{ font-size: 17px; margin: 7px 0 3px; }}
  h3 {{ font-size: 14px; margin: 6px 0 2px; }}
  a  {{ color: #1a0dab; }}
  ol, ul {{ padding-right: 22px; padding-left: 0; margin: 4px 0; }}
  table {{ border-collapse: collapse; width: 100%; margin: 6px 0; }}
  td, th {{ border: 1px solid #888; padding: 4px 8px; }}
  /* strip Quill editor chrome if HTML came directly from quill.root.innerHTML */
  .ql-editor {{ padding: 0 !important; }}
  p {{ margin: 0 0 4px; }}
</style>
</head>
<body>{html}</body>
</html>"""

    MAX_HEIGHT = 5000
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": width_px, "height": MAX_HEIGHT})
        page.set_content(wrapper, wait_until="domcontentloaded")
        body_h = min(int(page.evaluate("document.body.scrollHeight")), MAX_HEIGHT)
        png = page.screenshot(
            full_page=False,
            clip={"x": 0, "y": 0, "width": width_px, "height": max(body_h, 40)},
        )
        browser.close()
    return png


def html_to_png_bytes(html: str, width_px: int = 700) -> bytes:
    """Render an HTML string to a PNG image (bytes) via headless Chromium.

    Runs Playwright in a ThreadPoolExecutor worker to avoid the
    'event loop already running' error inside Streamlit's async context
    (Python 3.13 + Tornado).

    Raises RuntimeError if Playwright / Chromium is unavailable.
    """
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        return ex.submit(_render_html_sync, html, width_px).result()


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
