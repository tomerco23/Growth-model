# Design: Split Session Cost Column into Gross + Employer

**Date:** 2026-03-21  
**Status:** Approved

## Summary

Replace the single "עלות ססיה" column with two columns:
- **"עלות ססיה ברוטו"** — raw session cost entered by the user
- **"עלות מעביד ססיה"** — derived: `עלות ססיה ברוטו × employer_factor`

Also add `employer_factor` to the "הנחות החישוב" assumptions block in the management report sheet.

---

## Files & Changes

### 1. calculations.py
Four row-dicts currently contain `"עלות ססיה": sess_cost`:
- Manpower row, Session row, Revenue row, Revenue Session row

**Change:** Replace each with:
```
"עלות ססיה ברוטו": sess_cost,
"עלות מעביד ססיה": sess_cost * employer_factor,
```

### 2. views.py
- Input labels: "מחיר ססיה" / "עלות ססיה" → "עלות ססיה ברוטו"
- Edit handler key: "עלות ססיה" → "עלות ססיה ברוטו"
- Computed column: qty × עלות ססיה → qty × עלות מעביד ססיה (confirmed by user)
- Column list: add 'עלות מעביד ססיה' after 'עלות ססיה ברוטו' (read-only)
- column_config: ברוטו editable, מעביד read-only NumberColumn

### 3. report.py
- Management assumptions block: add EMP_ROW=7, label='עלות מעביד', value=employer_factor, format x1.31
- Manpower Excel table: split session columns from 2 to 3: כמות + ברוטו + מעביד
- total_col offset: 4 + (3 if has_sessions else 0)

## Decisions
- "עלות ססיות שנתית" = qty × עלות מעביד ססיה (confirmed)
- employer_factor assumption cell uses x notation, not %
- "עלות מעביד ססיה" in Streamlit is read-only
