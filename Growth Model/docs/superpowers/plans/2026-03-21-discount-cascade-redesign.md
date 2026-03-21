# Discount Cascade Redesign Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the multiplicative multi-step discount calculation with an additive single-bracket formula: `u_gross * (1 - (VOL + APPEALS + OVERHEAD)) * CAP_RATE_FACTOR`

**Architecture:** Single-function change inside the Revenue branch of `calculate_detailed_rows()` in `calculations.py`. `report.py` Excel formulas are updated to match. A new `test_calculations.py` file covers the formula with unit tests. `CLAUDE.md` is updated to reflect the new formula.

**Tech Stack:** Python, pandas, plain assertion tests (see `test_report.py` pattern)

**Spec:** `docs/superpowers/specs/2026-03-21-discount-cascade-redesign.md`

---

## Chunk 1: Tests + Implementation

### Task 1: Write failing tests for the new formula

**Files:**
- Create: `Growth Model/test_calculations.py`

- [ ] **Step 1: Create test file with failing tests**

Create `Growth Model/test_calculations.py`:

```python
# -*- coding: utf-8 -*-
"""Unit tests for the new additive discount cascade formula."""
import sys
sys.path.insert(0, '.')
from calculations import calculate_detailed_rows

PARAMS = {
    'VOL_DISCOUNT':    0.019,
    'APPEALS_PROV':    0.04,
    'OVERHEAD_RATE':   0.29,
    'CAP_RATE_FACTOR': 0.35,
    'NO_SHOW_RATE':    0.0,
}

# combined discount = 0.019 + 0.04 + 0.29 = 0.349
# u_net_factor  = 1 - 0.349  = 0.651
# u_final_factor = 0.651 * 0.35 = 0.22785

U_GROSS        = 1000.0
EXPECTED_U_NET   = round(U_GROSS * (1 - 0.349), 6)   # 651.0
EXPECTED_U_FINAL = round(EXPECTED_U_NET * 0.35, 6)   # 227.85


def _revenue_item(overrides=None):
    item = {
        'Category': 'Revenue',
        'Name': '001 - שירות בדיקה',
        'Quantity': 100,
        'Unit_Revenue': U_GROSS,
        'Is_New': False,
        'Is_Private': False,
        'Manual_No_Show': None,
        'Manual_Discount_Pct': None,
        'Pct_Opt': 0,
        'Pct_Pess': 0,
        'Growth_Y2': 0,
        'Growth_Y3': 0,
        'Growth_Y4': 0,
        'Rev_Sess_Vol': 0,
        'Rev_Sess_Cost': 0,
    }
    if overrides:
        item.update(overrides)
    return item


def test_unit_rate_after_discounts():
    """u_net should equal u_gross * (1 - combined_discount)."""
    df, *_ = calculate_detailed_rows([_revenue_item()], PARAMS)
    row = df[df['סוג'] == 'הכנסה'].iloc[0]
    actual = round(row['תעריף יחידה אחרי הנחות'], 6)
    assert actual == EXPECTED_U_NET, (
        f"תעריף אחרי הנחות: expected {EXPECTED_U_NET}, got {actual}"
    )
    print(f"PASS: u_net = {actual}")


def test_unit_rate_under_cap():
    """u_final (תחת cap) should equal u_net * CAP_RATE_FACTOR."""
    df, *_ = calculate_detailed_rows([_revenue_item()], PARAMS)
    row = df[df['סוג'] == 'הכנסה'].iloc[0]
    actual = round(row['תעריף יחידה תחת cap'], 6)
    assert actual == EXPECTED_U_FINAL, (
        f"תעריף תחת cap: expected {EXPECTED_U_FINAL}, got {actual}"
    )
    print(f"PASS: u_final = {actual}")


def test_net_pocket_equals_qty_times_u_final():
    """net_pocket should equal qty_net * u_final (no separate overhead step)."""
    qty = 100
    df, *_ = calculate_detailed_rows([_revenue_item({'Quantity': qty})], PARAMS)
    row = df[df['סוג'] == 'הכנסה'].iloc[0]
    qty_net  = qty * (1 - PARAMS['NO_SHOW_RATE'])
    expected = round(qty_net * EXPECTED_U_FINAL, 4)
    actual   = round(row['סה"כ נטו לכיס'], 4)
    assert actual == expected, (
        f"net_pocket: expected {expected}, got {actual}"
    )
    print(f"PASS: net_pocket = {actual:,.2f}")


def test_private_service_bypasses_all_discounts():
    """Private services must have net_pocket = qty_net * u_gross."""
    qty = 50
    df, *_ = calculate_detailed_rows(
        [_revenue_item({'Quantity': qty, 'Is_Private': True})], PARAMS
    )
    row = df[df['סוג'] == 'הכנסה'].iloc[0]
    expected = round(qty * U_GROSS, 4)
    actual   = round(row['סה"כ נטו לכיס'], 4)
    assert actual == expected, (
        f"Private net_pocket: expected {expected}, got {actual}"
    )
    print(f"PASS: private net_pocket = {actual:,.2f}")


def test_manual_discount_replaces_global_cap_still_applied():
    """Manual discount replaces global_discount_factor; CAP still applied."""
    manual_pct = 30.0
    qty = 100
    df, *_ = calculate_detailed_rows(
        [_revenue_item({'Quantity': qty, 'Manual_Discount_Pct': manual_pct})], PARAMS
    )
    row = df[df['סוג'] == 'הכנסה'].iloc[0]
    expected_u_net   = U_GROSS * (1 - manual_pct / 100)          # 700
    expected_u_final = expected_u_net * PARAMS['CAP_RATE_FACTOR'] # 245
    expected_net     = round(qty * expected_u_final, 4)
    actual_net       = round(row['סה"כ נטו לכיס'], 4)
    assert actual_net == expected_net, (
        f"Manual discount net_pocket: expected {expected_net}, got {actual_net}"
    )
    print(f"PASS: manual discount net_pocket = {actual_net:,.2f}")


if __name__ == '__main__':
    print("=" * 60)
    test_unit_rate_after_discounts()
    test_unit_rate_under_cap()
    test_net_pocket_equals_qty_times_u_final()
    test_private_service_bypasses_all_discounts()
    test_manual_discount_replaces_global_cap_still_applied()
    print("=" * 60)
    print("ALL TESTS PASSED")
```

- [ ] **Step 2: Run tests – confirm they FAIL**

```bash
cd "Growth Model" && python test_calculations.py
```

Expected: AssertionError on `test_unit_rate_after_discounts` because the old formula is still in place.

---

### Task 2: Implement the new discount formula in `calculations.py`

**Files:**
- Modify: `Growth Model/calculations.py` lines ~182–200

- [ ] **Step 3: Replace Revenue discount block**

In `calculations.py`, find this exact block:

```python
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
```

Replace with:

```python
            combined_discount = (
                params['VOL_DISCOUNT']
                + params['APPEALS_PROV'] + params['OVERHEAD_RATE']
            )
            global_discount_factor = 1 - combined_discount
            active_discount_factor = (
                1 - (item.get('Manual_Discount_Pct') / 100.0)
                if item.get('Manual_Discount_Pct') is not None
                else global_discount_factor
            )

            if item.get('Is_Private'):
                u_net   = u_gross
                u_final = u_gross
            else:
                u_net   = u_gross * active_discount_factor
                u_final = u_net * params['CAP_RATE_FACTOR']

            tot_gross  = qty_net * u_gross
            tot_net    = qty_net * u_net
            tot_cap    = qty_net * u_final
            ovh_cost   = qty_net * u_net * params['OVERHEAD_RATE']
            net_pocket = qty_net * u_final
```

Also update the row dict (~line 215): change `"תעריף יחידה תחת cap": u_cap` to `"תעריף יחידה תחת cap": u_final`.

- [ ] **Step 4: Run tests – confirm they PASS**

```bash
cd "Growth Model" && python test_calculations.py
```

Expected output:
```
============================================================
PASS: u_net = 651.0
PASS: u_final = 227.85
PASS: net_pocket = 22,785.00
PASS: private net_pocket = 50,000.00
PASS: manual discount net_pocket = 24,500.00
============================================================
ALL TESTS PASSED
```

- [ ] **Step 5: Run existing report tests to check nothing broke**

```bash
python test_report.py
```

Expected: `ALL TESTS PASSED`

- [ ] **Step 6: Commit calculations change**

```bash
cd .. && git add "Growth Model/calculations.py" "Growth Model/test_calculations.py"
git commit -m "feat(calculations): additive discount cascade (HMO+VOL+APPEALS+OVERHEAD)*CAP"
```

---

### Task 3: Update CLAUDE.md business logic section

**Files:**
- Modify: `Growth Model/CLAUDE.md`

- [ ] **Step 7: Update formula documentation**

In `CLAUDE.md`, find the Business Logic section that contains:
```
u_net   = u_gross × (1 - hmo_discount) × (1 - vol_discount) × (1 - appeals_prov)
u_cap   = u_gross × cap_rate_factor
net_pocket = qty_net × u_net × (1 - overhead_rate)
```

Replace with:
```
u_net      = u_gross × (1 − (HMO_DISCOUNT + VOL_DISCOUNT + APPEALS_PROV + OVERHEAD_RATE))
u_final    = u_net × CAP_RATE_FACTOR
net_pocket = qty_net × u_final
```

- [ ] **Step 8: Commit docs update**

```bash
git add "Growth Model/CLAUDE.md"
git commit -m "docs(CLAUDE.md): update revenue formula to additive discount cascade"
```


---

### Task 4: Update report.py -- Excel formulas and assumption cells

**Files:**
- Modify: Growth Model/report.py

Three sub-areas to update:

#### 4a. create_management_report_sheet -- add HMO assumption cell + fix formula

**Step 9a:** After the line cap_f = params.get('CAP_RATE_FACTOR', 0), add:
    hmo = params.get('HMO_DISCOUNT', 0)

**Step 9b:** After the line CAP_ROW = 6, add:
    HMO_ROW = 7
    hmo_ref = '$F$8'

**Step 9c:** Append to the assumption loop:
    (HMO_ROW, 'הנחת קופות', hmo),

**Step 9d:** Replace Python fallback for non-private:
    OLD: combined  = vol + appeals + overhead + cap_f
         u_net_new = u_gross_val * (1 - combined)
         net_t_new = qty_eff * u_net_new
    NEW: u_net_new   = u_gross_val * (1 - (vol + appeals + overhead))
         u_final_new = u_net_new * cap_f
         net_t_new   = qty_eff * u_final_new

**Step 9b:** Replace Python fallback for private:
    OLD: if is_private:
             u_net_new = u_gross_val * (1 - overhead)
             net_t_new = qty_eff * u_net_new
    NEW: if is_private:
             u_net_new   = u_gross_val
             u_final_new = u_gross_val
             net_t_new   = qty_eff * u_gross_val

**Step 9c:** Replace Excel formula writes:
    OLD private:     f'=C{er}*(1-{ovh_ref})'         fallback=u_net_new
    OLD non-private: f'=C{er}*(1-({vol_ref}+{app_ref}+{ovh_ref}+{cap_ref}))'  fallback=u_net_new
    NEW private:     f'=C{er}'                        fallback=u_net_new
    NEW non-private: f'=C{er}*(1-({vol_ref}+{app_ref}+{ovh_ref}))*{cap_ref}'  fallback=u_final_new

Note: CNTK formula =B{er}*D{er} and s_net_t += net_t_new remain unchanged.

**Step 9d:** Update docstring line:
    OLD: CAP is always baked into the net tariff using additive combined discounts.
    NEW: Formula: u_gross * (1 - (VOL+APPEALS+OVERHEAD)) * CAP_RATE_FACTOR.

#### 4b. generate_methodology() -- update formula descriptions

Find:
    ("חישוב הכנסה נטו", "הנוסחה: מחיר מחירון (ברוטו) x (1 - (הנחת מחזור + הפרשה לערעורים))."),
    ("חישוב הכנסה קאפ (CAP)", "הנוסחה: מחיר מחירון (ברוטו) * מקדם קאפ (תעריף שולי). ללא הנחות נוספות."),

Replace with:
    ("חישוב הכנסה נטו", "הנוסחה: תעריף ברוטו x (1 - (הנחת קופות + הנחת מחזור + הפרשה לערעורים + תקורה)) x מקדם קאפ."),
    ("חישוב הכנסה קאפ (CAP)", "מקדם קאפ מוחל כמכפיל על התעריף לאחר כל ההנחות (לא כהנחה נוספת)."),

#### 4c. Metadata sheet -- re-enable HMO_DISCOUNT row

Delete these two lines:
        if k == 'HMO_DISCOUNT':
            continue   # הוסר -- הנחת קופות אינה בשימוש

- [ ] **Step 9: Apply all sub-changes to report.py**

- [ ] **Step 10: Run existing report tests**

Run: python test_report.py (from Growth Model/)
Expected: ALL TESTS PASSED

- [ ] **Step 11: Commit report.py changes**

git add "Growth Model/report.py"
git commit -m "feat(report): update Excel formulas to additive discount cascade with CAP multiplier"

---

## Done

All five unit tests pass. test_report.py also passes. Three commits made. The new additive cascade formula is live in both calculations and the Excel export.

