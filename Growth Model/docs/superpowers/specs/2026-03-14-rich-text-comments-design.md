# Rich Text Comments Editor — Design Spec

## Goal

Replace the plain `st.text_area` in the "הערות הכלכלן" section with a Word-like rich text editor (Quill.js), and embed the formatted content as a PNG image in the exported Excel file.

## Architecture

Three-layer pipeline:
1. **UI layer** — `streamlit-quill` renders a Quill.js WYSIWYG editor; output is an HTML string
2. **Conversion layer** — `html_to_png_bytes()` in `utils.py` wraps the HTML, launches headless Chromium via `playwright` in a background thread (avoids asyncio conflict), returns PNG bytes
3. **Excel layer** — `report.py` embeds the PNG bytes via `ws.insert_image()` at both comment insertion sites

## Tech Stack

- `streamlit-quill` — Quill.js editor Streamlit component (pip)
- `playwright` (Python) — headless Chromium for HTML→PNG (pip + `playwright install chromium`, one-time)
- `xlsxwriter` — already in use, `insert_image()` supports `BytesIO` via `image_data` option

---

## Component 1: UI Editor (`views.py`)

**Replace** `st.text_area(...)` with `st_quill(...)` from `streamlit-quill`.

**Graceful degradation** — wrap import at module top:
```python
try:
    from streamlit_quill import st_quill
    _QUILL_AVAILABLE = True
except ImportError:
    _QUILL_AVAILABLE = False
```

**Usage in show_report_view():**
```python
if _QUILL_AVAILABLE:
    html_content = st_quill(
        placeholder="הזן כאן הערות, הנחות יסוד, מגבלות, המלצות לממשל...",
        html=True,
        key='general_comments',
        toolbar=[
            [{'header': [1, 2, 3, False]}],
            ['bold', 'underline', 'italic'],
            [{'list': 'ordered'}, {'list': 'bullet'}],
            ['link'],
            ['clean'],
        ],
    )
else:
    html_content = st.text_area(
        "הערות הכלכלן:",
        key='general_comments',
        height=180,
        placeholder="הזן כאן הערות, הנחות יסוד, מגבלות, המלצות לממשל...",
    )
```

**Note on `table` toolbar item:** `streamlit-quill` wraps Quill 1.x which does not ship with a native table module. Omit `'table'` from the toolbar to avoid a silent JS error. Tables are not supported in Quill 1.x.

**Backward compatibility:**
`st.session_state.general_comments` may hold legacy plain text. The `is_html()` helper in `utils.py` distinguishes old from new content safely.

---

## Component 2: HTML → PNG conversion (`utils.py`)

### `is_html(text: str) -> bool`
Use a strict check — must find an opening HTML tag, not just `<` or `>`:
```python
import re
def is_html(text: str) -> bool:
    return bool(text and re.search(r'<[a-z]', text, re.IGNORECASE))
```
This avoids false positives for plain text containing `>` (e.g., `"ROI > 5 שנים"`).

### `strip_html(html: str) -> str`
```python
def strip_html(html: str) -> str:
    return re.sub(r'<[^>]+>', '', html).strip()
```

### `html_to_png_bytes(html: str, width_px: int = 700) -> bytes`

**Threading:** Streamlit runs on an asyncio event loop (Tornado). `sync_playwright()` uses its own event loop internally and raises `RuntimeError` if called from within a running loop on Python 3.13. Solution: run Playwright in a `ThreadPoolExecutor` worker thread, which has no running loop.

```python
import concurrent.futures

def html_to_png_bytes(html: str, width_px: int = 700) -> bytes:
    """Render HTML to PNG bytes via Playwright headless Chromium.
    Runs in a thread to avoid asyncio conflict with Streamlit's event loop.
    Raises RuntimeError if Playwright or Chromium is unavailable.
    """
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        return ex.submit(_render_html_sync, html, width_px).result()


def _render_html_sync(html: str, width_px: int) -> bytes:
    from playwright.sync_api import sync_playwright

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
    line-height: 1.5;
    direction: rtl;
    text-align: right;
    background: #FFFFCC;
  }}
  h1 {{ font-size: 20px; margin: 8px 0; }}
  h2 {{ font-size: 17px; margin: 6px 0; }}
  h3 {{ font-size: 14px; margin: 5px 0; }}
  a  {{ color: #1a0dab; }}
  ol, ul {{ padding-right: 20px; padding-left: 0; }}
  table {{ border-collapse: collapse; width: 100%; }}
  td, th {{ border: 1px solid #888; padding: 4px 8px; }}
</style>
</head>
<body>{html}</body>
</html>"""

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        # overflow:hidden + exact width eliminates scrollbar
        page = browser.new_page(viewport={{"width": width_px, "height": 2000}})
        page.set_content(wrapper, wait_until="domcontentloaded")
        body_h = page.evaluate("document.body.scrollHeight")
        png = page.screenshot(
            clip={{"x": 0, "y": 0, "width": width_px, "height": body_h}},
            full_page=False,
        )
        browser.close()
    return png
```

---

## Component 3: Excel embedding (`report.py`)

**Two sites** currently use the comments string — both must be updated:

### Site 1 — `create_management_report_sheet()` (~line 419)

**Before:**
```python
if comments:
    _rtl = any('\u0590' <= c <= '\u05FF' for c in comments)
    ws.insert_textbox(row, 0, comments, { ... })
```

**After:**
```python
if comments:
    _embed_comments_image(ws, row, 0, comments, wb)
```

### Site 2 — detail sheet (~line 1061)

**Before:**
```python
if comments:
    ws.merge_range(row_idx, 0, row_idx + 7, 7, comments, fmt['text_box'])
```

**After:**
```python
if comments:
    _embed_comments_image(ws, row_idx, 0, comments, wb)
```

### Shared helper `_embed_comments_image()`

Add to `report.py`:
```python
def _embed_comments_image(ws, row: int, col: int, comments: str, wb) -> None:
    """Embed comments as PNG image if HTML, otherwise fallback to textbox."""
    from utils import is_html, html_to_png_bytes, strip_html
    import io

    if is_html(comments):
        try:
            png = html_to_png_bytes(comments)
            ws.insert_image(row, col, 'comments.png', {
                'image_data': io.BytesIO(png),
                'object_position': 1,   # move and size with cells
                'x_scale': 1.0,
                'y_scale': 1.0,
            })
            return
        except Exception:
            comments = strip_html(comments)   # fall through to textbox

    # Plain text fallback
    _rtl = any('\u0590' <= c <= '\u05FF' for c in comments)
    ws.insert_textbox(row, col, comments, {
        'width': 700, 'height': 200,
        'font': {'size': 11},
        'align': {'vertical': 'top', 'horizontal': 'right' if _rtl else 'left'},
    })
```

**`object_position: 1`** — image moves and sizes with cells, so it does not overflow into adjacent content regardless of PNG height.

---

## Error / Fallback Matrix

| Condition | UI | Excel |
|-----------|-----|-------|
| Both installed + Chromium ready | Quill editor | PNG image |
| `playwright install chromium` not run | Quill editor | fallback textbox + no crash |
| `streamlit-quill` not installed | plain `st.text_area` | textbox as before |
| Legacy plain-text content (no HTML tags) | displayed as-is | `insert_textbox` unchanged |
| Plain text with `>` or `<` chars | displayed as-is | `is_html()` returns False → textbox |

---

## Files Changed

| File | Change |
|------|--------|
| `views.py` | Replace `st.text_area` with `st_quill()` + import fallback |
| `utils.py` | Add `is_html()`, `strip_html()`, `html_to_png_bytes()`, `_render_html_sync()` |
| `report.py` | Add `_embed_comments_image()`; replace both comment-embedding sites |
| `requirements.txt` | **Create new file** with `streamlit-quill` and `playwright` |

## `requirements.txt` (new file)

```
streamlit
streamlit-quill
pandas
numpy
xlsxwriter
playwright
```

## One-time setup after `pip install`

```bash
python -m playwright install chromium
```

This downloads an isolated Chromium binary (~150 MB) to the Playwright cache directory. Does not affect system Chrome. Must be run once per environment.
