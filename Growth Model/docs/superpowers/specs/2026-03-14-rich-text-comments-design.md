# Rich Text Comments Editor — Design Spec

## Goal

Replace the plain `st.text_area` in the "הערות הכלכלן" section with a Word-like rich text editor (Quill.js), and embed the formatted content as an image in the exported Excel file.

## Architecture

Three-layer pipeline:
1. **UI layer** — `streamlit-quill` renders a Quill.js WYSIWYG editor; output is an HTML string
2. **Conversion layer** — `html_to_png_bytes()` in `utils.py` wraps the HTML, launches headless Chromium via `playwright`, screenshots the result, returns PNG bytes
3. **Excel layer** — `report.py` embeds the PNG bytes via `ws.insert_image()` instead of the current `ws.insert_textbox()`

## Tech Stack

- `streamlit-quill` — Quill.js editor Streamlit component (pip)
- `playwright` (Python) — headless Chromium for HTML→PNG (pip + `playwright install chromium`)
- `xlsxwriter` — already in use, `insert_image()` supports `BytesIO`

---

## Component 1: UI Editor (`views.py`)

**Replace** `st.text_area(...)` with `st_quill(...)` from `streamlit-quill`.

**Toolbar configuration:**
```python
from streamlit_quill import st_quill

html_content = st_quill(
    placeholder="הזן כאן הערות, הנחות יסוד, מגבלות, המלצות לממשל...",
    html=True,          # return HTML string
    key='general_comments',
    toolbar=[
        [{'header': [1, 2, 3, False]}],
        ['bold', 'underline', 'italic'],
        [{'list': 'ordered'}, {'list': 'bullet'}],
        ['link', 'table'],
        ['clean'],
    ],
)
```

**RTL / Hebrew:**
Pass an `html` wrapper with `dir="rtl"` as the initial value when the editor loads. The `html_to_png_bytes()` function also injects RTL styling.

**Graceful degradation:**
Wrap the import in a try/except. If `streamlit_quill` is not installed, fall back to the original `st.text_area`.

```python
try:
    from streamlit_quill import st_quill
    _QUILL_AVAILABLE = True
except ImportError:
    _QUILL_AVAILABLE = False
```

**Backward compatibility:**
`st.session_state.general_comments` may contain legacy plain text (no HTML tags). The `is_html()` helper distinguishes old from new content.

---

## Component 2: HTML → PNG conversion (`utils.py`)

### `is_html(text: str) -> bool`
```python
def is_html(text: str) -> bool:
    return bool(text and '<' in text and '>' in text)
```

### `html_to_png_bytes(html: str, width_px: int = 700) -> bytes`

Full implementation:
```python
def html_to_png_bytes(html: str, width_px: int = 700) -> bytes:
    """Render an HTML string to PNG bytes using Playwright headless Chromium.
    Returns PNG bytes ready for xlsxwriter insert_image().
    Raises RuntimeError if Playwright or Chromium is unavailable.
    """
    from playwright.sync_api import sync_playwright

    wrapper = f"""
    <!DOCTYPE html>
    <html dir="rtl" lang="he">
    <head>
    <meta charset="utf-8">
    <style>
        body {{
            font-family: Arial, sans-serif;
            font-size: 13px;
            line-height: 1.5;
            direction: rtl;
            text-align: right;
            width: {width_px}px;
            margin: 0;
            padding: 12px;
            background: #FFFFCC;
            box-sizing: border-box;
        }}
        h1 {{ font-size: 20px; margin: 8px 0; }}
        h2 {{ font-size: 17px; margin: 6px 0; }}
        h3 {{ font-size: 14px; margin: 5px 0; }}
        table {{ border-collapse: collapse; width: 100%; }}
        td, th {{ border: 1px solid #888; padding: 4px 8px; }}
        a {{ color: #1a0dab; }}
        ol, ul {{ padding-right: 20px; padding-left: 0; }}
    </style>
    </head>
    <body>{html}</body>
    </html>
    """

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": width_px + 24, "height": 2000})
        page.set_content(wrapper, wait_until="domcontentloaded")
        # Clip to actual content height
        body_height = page.evaluate("document.body.scrollHeight")
        png_bytes = page.screenshot(
            clip={"x": 0, "y": 0, "width": width_px + 24, "height": body_height},
            full_page=False,
        )
        browser.close()

    return png_bytes
```

**Error handling:** caller wraps in try/except; on failure, falls back to plain text.

---

## Component 3: Excel embedding (`report.py`)

In `create_management_report_sheet()`, replace the `insert_textbox` block:

**Before:**
```python
if comments:
    ws.insert_textbox(row, 0, comments, { ... })
```

**After:**
```python
if comments:
    if is_html(comments):
        try:
            from utils import html_to_png_bytes
            png = html_to_png_bytes(comments)
            ws.insert_image(row, 0, 'comments.png',
                            {'image_data': io.BytesIO(png),
                             'x_scale': 1.0, 'y_scale': 1.0})
        except Exception:
            # fallback to plain text textbox
            ws.insert_textbox(row, 0, _strip_html(comments), { ... })
    else:
        ws.insert_textbox(row, 0, comments, { ... })
```

### `_strip_html(html: str) -> str`
Simple tag stripper for the fallback path (used in `utils.py`):
```python
import re
def strip_html(html: str) -> str:
    return re.sub(r'<[^>]+>', '', html).strip()
```

---

## Error / Fallback Matrix

| Condition | UI | Excel |
|-----------|-----|-------|
| Both installed & Chromium ready | Quill editor | PNG image |
| `playwright install chromium` not run | Quill editor | fallback textbox + `st.warning` |
| `streamlit-quill` not installed | plain `st.text_area` | textbox as before |
| Legacy plain-text content | displayed as-is in editor | `insert_textbox` unchanged |

---

## Files Changed

| File | Change |
|------|--------|
| `views.py` | Replace `st.text_area` with `st_quill()`, graceful import fallback |
| `utils.py` | Add `is_html()`, `html_to_png_bytes()`, `strip_html()` |
| `report.py` | Replace `insert_textbox` with `insert_image` + fallback |
| `requirements.txt` | Add `streamlit-quill`, `playwright` |

## Requirements

```
streamlit-quill
playwright
```

One-time setup after install:
```bash
python -m playwright install chromium
```
