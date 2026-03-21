# Split Session Cost Columns Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development or superpowers:executing-plans.

**Goal:** Replace single "עלות ססיה" column with "עלות ססיה ברוטו" (user input) and "עלות מעביד ססיה" (= gross x employer_factor).

**Architecture:** 3-file change: calculations.py data model, views.py Streamlit table, report.py Excel.

**Tech Stack:** Python, pandas, Streamlit, xlsxwriter. All edits via Bash py -c (Hebrew path workaround).

**Spec:** docs/superpowers/specs/2026-03-21-split-session-cost-columns-design.md

---

## Chunk 1: calculations.py

### Task 1: Split the session cost column in df_flat

**Files:** Growth Model/calculations.py | Growth Model/tests/test_calculations.py

Column "עלות ססיה" appears 4 times in row dicts (Manpower, Session, Revenue, Revenue Session rows).
employer_factor is already extracted: `employer_factor = params.get('EMPLOYER_FACTOR', 1.31)`

- [ ] **Step 1: Add failing test to test_calculations.py**

```python
def test_calc_split_sess_cost_columns():
    items = [{
        'Category': Category.MANPOWER, 'Name': 'N', 'Quantity': 1,
        'Unit_Cost': 120000, 'Sessions': 5, 'Sess_Price': 200,
        'Pct_Opt': 0, 'Pct_Pess': 0, 'Calc_Mode': 'FTE',
    }]
    params = {'OVERHEAD_RATE': 0, 'VOL_DISCOUNT': 0, 'APPEALS_PROV': 0,
              'NO_SHOW_RATE': 0, 'CAP_RATE_FACTOR': 1, 'HMO_DISCOUNT': 0,
              'EMPLOYER_FACTOR': 1.31}
    df, *_ = calculate_detailed_rows(items, params)
    assert "עלות ססיה ברוטו" in df.columns, "ברוטו col missing"
    assert "עלות מעביד ססיה" in df.columns, "מעביד col missing"
    assert "עלות ססיה" not in df.columns, "old col must be gone"
    r = df[df['Row_Type'] == 'Main'].iloc[0]
    assert r["עלות ססיה ברוטו"] == 200
    assert abs(r["עלות מעביד ססיה"] - 200*1.31) < 0.01
```

- [ ] **Step 2: Run test - expect FAIL**
```
cd "C:/Users/yoyo1/OneDrive/Desktop/Growth-model/Growth Model"
py -m pytest tests/test_calculations.py::test_calc_split_sess_cost_columns -v
```
Expected: FAIL with KeyError or AssertionError.

- [ ] **Step 3: Patch calculations.py via py -c**

Strategy: regex sub replaces all 4 occurrences in one pass.

```python
# Run inside Growth Model directory:
# py -c "..." (or via write to temp file)
import re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
path = 'calculations.py'
with open(path, encoding='utf-8') as f: src = f.read()
GROSS = chr(0x05e2)+chr(0x05dc)+chr(0x05d5)+chr(0x05ea)+' '+chr(0x05e1)+chr(0x05e1)+chr(0x05d9)+chr(0x05d4)+' '+chr(0x05d1)+chr(0x05e8)+chr(0x05d5)+chr(0x05d8)+chr(0x05d5)
EMP   = chr(0x05e2)+chr(0x05dc)+chr(0x05d5)+chr(0x05ea)+' '+chr(0x05de)+chr(0x05e2)+chr(0x05d1)+chr(0x05d9)+chr(0x05d3)+' '+chr(0x05e1)+chr(0x05e1)+chr(0x05d9)+chr(0x05d4)
OLD   = chr(0x05e2)+chr(0x05dc)+chr(0x05d5)+chr(0x05ea)+' '+chr(0x05e1)+chr(0x05e1)+chr(0x05d9)+chr(0x05d4)
INDENT = '                '
src = re.sub(
    chr(34)+OLD+chr(34)+r': (sess_cost|rev_sess_cost),',
    lambda m: chr(34)+GROSS+chr(34)+f': {m.group(1)},'+chr(10)+INDENT+chr(34)+EMP+chr(34)+f': {m.group(1)} * employer_factor,',
    src
)
assert src.count(chr(34)+OLD+chr(34)) == 0, 'Old key still present'
with open(path, 'w', encoding='utf-8') as f: f.write(src)
print('OK')
```

- [ ] **Step 4: Run test - expect PASS**
```
py -m pytest tests/test_calculations.py -v
```

- [ ] **Step 5: Syntax check**
```
py -m py_compile calculations.py && echo OK
```

- [ ] **Step 6: Commit**
```bash
cd "C:/Users/yoyo1/OneDrive/Desktop/Growth-model"
git add "Growth Model/calculations.py" "Growth Model/tests/test_calculations.py"
git commit -m "feat(calc): split עלות ססיה into ברוטו + מעביד columns"
```

---

## Chunk 2: views.py

### Task 2: Update Streamlit edit table and input labels

**Files:** Growth Model/views.py

6 targeted str.replace() changes via py -c. Always assert old string exists before replacing.

| # | Location | Old | New |
|---|----------|-----|-----|
| 1 | HR input ~411 | "מחיר ססיה" | "עלות ססיה ברוטו" |
| 2 | Rev input ~519 | "עלות ססיה" (in number_input label) | "עלות ססיה ברוטו" |
| 3 | edit handler ~325 | `elif col == "עלות ססיה":` | `elif col == "עלות ססיה ברוטו":` |
| 4 | computed col ~553 | `editable_df["עלות ססיה"]` | `editable_df["עלות מעביד ססיה"]` |
| 5 | cols_order ~560 | `'עלות ססיה', 'עלות ססיות שנתית'` | `'עלות ססיה ברוטו', 'עלות מעביד ססיה', 'עלות ססיות שנתית'` |
| 6 | column_config ~575 | old single entry | עלות ססיה ברוטו editable + עלות מעביד ססיה disabled |

- [ ] **Step 1: Apply all 6 patches via py -c**

Example for patch 6 (column_config) - key old/new strings:
```python
old6 = chr(34)+'עלות ססיה ברוטו'+chr(34)+chr(34)
# ... write to temp py file and run with 'py tempfile.py'
```

Full old string for entry 6:
```
"עלות ססיה": st.column_config.NumberColumn("עלות ססיה (₪)", format="%.0f"),
```
New (two entries, same indentation):
```
"עלות ססיה ברוטו": st.column_config.NumberColumn("עלות ססיה ברוטו (₪)", format="%.0f"),
"עלות מעביד ססיה": st.column_config.NumberColumn("עלות מעביד ססיה (₪)", format="%.0f", disabled=True),
```

- [ ] **Step 2: Syntax check**
```
py -m py_compile views.py && echo OK
```

- [ ] **Step 3: Commit**
```bash
git add "Growth Model/views.py"
git commit -m "feat(views): split session cost cols to ברוטו+מעביד in edit table"
```

---

## Chunk 3: report.py

### Task 3a: Add employer_factor to management sheet assumptions panel

In create_management_report_sheet (~line 162). Assumptions are at cols E-F, rows 2-6 (VOL/APP/NS/OVH/CAP).
Add EMP_ROW=7 (Excel row 8).

- [ ] **Step 1: 3 insertions via py -c**

a) After `cap_f = params.get('CAP_RATE_FACTOR', 0)` insert:
   `employer_f = params.get('EMPLOYER_FACTOR', 1.31)`

b) After `NS_ROW, OVH_ROW, CAP_ROW = 4, 5, 6` insert on next line:
   `EMP_ROW = 7`

c) After the for-loop that writes VOL/APP/NS/OVH/CAP (after `ws.write(ar, AC, val, fmt['assump_pct'])` line) add:
```python
ws.write(EMP_ROW, AL, 'עלות מעביד', fmt['assumption_box'])
ws.write(EMP_ROW, AC, f'×{employer_f:.2f}', fmt['assump_pct'])
```

- [ ] **Step 2: Syntax check**
```
py -m py_compile report.py && echo OK
```

---

### Task 3b: Split session cols in create_management_report_sheet manpower table

Location: ~lines 315-420 (4-branch dynamic layout + data loop).

**New column layout table:**

| Branch | Columns | Indices |
|--------|---------|---------|
| has_annual_cost AND has_sessions | שם, תקנים, עלות שנתית, כמות ססיות, עלות ססיה ברוטו, עלות מעביד ססיה, סה"כ | C_ANN=2 C_SQ=3 C_SP_GROSS=4 C_SP_EMP=5 C_TOT=6 |
| has_annual_cost only (no change) | שם, תקנים, עלות שנתית, סה"כ | C_ANN=2 C_TOT=3 |
| has_sessions only | שם, תקנים, כמות ססיות, עלות ססיה ברוטו, עלות מעביד ססיה, סה"כ | C_SQ=2 C_SP_GROSS=3 C_SP_EMP=4 C_TOT=5 |
| neither (no change) | שם, תקנים, סה"כ | C_TOT=2 |

- [ ] **Step 1: Update 4 layout branches via py -c**
  Replace header lists and old `C_SP=N` with `C_SP_GROSS=N, C_SP_EMP=N+1, C_TOT=N+2`.

- [ ] **Step 2: Update data loop via py -c (~lines 343-396)**

Old:
```python
sess_cost_unit = r['עלות ססיה']
sess_total     = sess_qty * sess_cost_unit
sp_v           = sess_cost_unit
# ...cell writes: ws.write(row, C_SP, sp_v, ...)
# ...formula uses: _cl(C_SP)
```

New:
```python
sess_cost_gross = r['עלות ססיה ברוטו']
sess_cost_emp   = r['עלות מעביד ססיה']
sess_total      = sess_qty * sess_cost_emp    # actual cost includes employer factor
sp_gross_v      = sess_cost_gross
sp_emp_v        = sess_cost_emp
# ...cell writes: ws.write(row, C_SP_GROSS, sp_gross_v, ...)
#                 ws.write(row, C_SP_EMP,   sp_emp_v,   ...)
# ...formula uses: _cl(C_SP_EMP)
```

Also update shift-worker blank writes (~line 407):
```python
# Old: if C_SQ is not None and C_SQ > 2:
#          ws.write(row, C_SQ, ...) / ws.write(row, C_SP, ...)
# New: add blank for C_SP_EMP as well when C_SP_EMP is not None
```

- [ ] **Step 3: Syntax check**
```
py -m py_compile report.py && echo OK
```

---

### Task 3c: Split session cols in create_hybrid_report_sheet manpower table

Location: ~lines 966-1015 (simpler, no 4-branch layout).

- [ ] **Step 1: Patch mp_headers via py -c**

Old: `mp_headers += ["כמות ססיה (שנתי)", "עלות ססיה"]`
New: `mp_headers += ["כמות ססיה (שנתי)", "עלות ססיה ברוטו", "עלות מעביד ססיה"]`

- [ ] **Step 2: Patch data row loop via py -c (~lines 992-1004)**

Old:
```python
sess_price = row['עלות ססיה']
total_sess = sess_vol * sess_price
total_combined = base_cost + total_sess
# ...
ws.write(row_idx, c_idx, sess_vol,   fmt['normal']); c_idx += 1
ws.write(row_idx, c_idx, sess_price, fmt['curr']);   c_idx += 1
```

New:
```python
sess_price_gross = row['עלות ססיה ברוטו']
sess_price_emp   = row['עלות מעביד ססיה']
total_sess       = sess_vol * sess_price_emp    # use employer rate for actual cost
total_combined   = base_cost + total_sess
# ...
ws.write(row_idx, c_idx, sess_vol,         fmt['normal']); c_idx += 1
ws.write(row_idx, c_idx, sess_price_gross, fmt['curr']);   c_idx += 1
ws.write(row_idx, c_idx, sess_price_emp,   fmt['curr']);   c_idx += 1
```

- [ ] **Step 3: Fix total_col offset via py -c**

Old: `total_col = 4 + (2 if has_sessions else 0)`
New: `total_col = 4 + (3 if has_sessions else 0)`

- [ ] **Step 4: Full test suite**
```
cd "C:/Users/yoyo1/OneDrive/Desktop/Growth-model/Growth Model"
py -m pytest tests/ -v
```
Expected: ALL PASS.

- [ ] **Step 5: Commit**
```bash
git add "Growth Model/report.py"
git commit -m "feat(report): split session cost cols in Excel + employer_factor in assumptions"
```

---

## Final Verification Checklist

- [ ] `py -m pytest tests/ -v` -- all green
- [ ] `py -m py_compile calculations.py views.py report.py` -- no errors
- [ ] Exact old column name "עלות ססיה" absent from all .py files
- [ ] Streamlit table: "עלות ססיה ברוטו" editable, "עלות מעביד ססיה" has disabled=True
- [ ] "עלות ססיות שנתית" = qty x עלות מעביד ססיה
- [ ] Excel management assumptions panel: row 8 = "עלות מעביד" x1.31
- [ ] Excel manpower tables: 3 session cols (qty + עלות ססיה ברוטו + עלות מעביד ססיה)
