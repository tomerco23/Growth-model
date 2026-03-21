# Discount Cascade Redesign – Design Spec
**Date:** 2026-03-21
**Status:** Approved

## Background

The current revenue calculation applies discounts sequentially and multiplicatively, with overhead deducted as a separate post-discount step. The business requested a cleaner additive cascade where all discounts (HMO + volume/turnover + appeals + overhead) are summed into a single bracket, then a CAP factor is applied as a final multiplier.

## New Formula

```
u_final    = u_gross x (1 - (VOL_DISCOUNT + APPEALS_PROV + OVERHEAD_RATE)) x CAP_RATE_FACTOR
net_pocket = qty_net x u_final
```

Default parameter values:
| Parameter | Value | Hebrew label |
|-----------|-------|-------------|
| VOL_DISCOUNT | 1.9% | הנחת מחזור |
| APPEALS_PROV | 4.0% | הנחת ערעור |
| OVERHEAD_RATE | 29.0% | הנחת תקורה |
| CAP_RATE_FACTOR | 35.0% | מקדם קאפ |

Combined discount = 34.9% -> u_net = u_gross x 0.651
Final rate = u_net x 0.35

## Old Formula (replaced)

```
global_discount_factor = 1 - (VOL_DISCOUNT + APPEALS_PROV)   # HMO was unused
u_net   = u_gross x active_discount_factor
u_cap   = u_gross x CAP_RATE_FACTOR                           # independent of discounts
ovh_cost = tot_net x OVERHEAD_RATE
net_pocket = tot_net - ovh_cost
```

Key differences:
- HMO_DISCOUNT was NOT applied in the old code (bug / intentional omission)
- Overhead was a post-discount subtraction, not part of the discount bracket
- CAP was applied to gross rate independently; now applied to discounted rate

## Implementation – calculations.py Revenue Branch

```python
combined_discount = (
    params['VOL_DISCOUNT'] + params['APPEALS_PROV']
    + params['OVERHEAD_RATE']
)
global_discount_factor = 1 - combined_discount
active_discount_factor = (
    1 - item.get('Manual_Discount_Pct') / 100.0
    if item.get('Manual_Discount_Pct') is not None
    else global_discount_factor
)

if item.get('Is_Private'):
    u_net   = u_gross   # bypass all discounts
    u_final = u_gross
else:
    u_net   = u_gross * active_discount_factor       # after all discounts, before CAP
    u_final = u_net * params['CAP_RATE_FACTOR']      # final rate

ovh_cost   = qty_net * u_net * params['OVERHEAD_RATE']  # display only
net_pocket = qty_net * u_final
```

## Display Columns – Mapping

| Column | Old meaning | New meaning |
|--------|-------------|-------------|
| תעריף יחידה אחרי הנחות | after VOL+APPEALS | = u_final (single step, same as תחת cap) |
| תעריף יחידה תחת cap | gross x CAP | = u_final = u_gross x (1-discounts) x CAP |
| עלות תקורה | separate overhead deduction | 0 (overhead baked into formula, no separate display) |
| סה"כ אחרי הנחות | qty_net x u_net (old) | qty_net x u_final |
| סה"כ אחרי קאפ | qty_net x u_cap (old) | qty_net x u_final |
| סה"כ נטו לכיס | tot_net - ovh_cost | qty_net x u_final |

## Private Services

Is_Private = True continues to bypass all discounts and CAP:
net_pocket = qty_net x u_gross

## Manual Discount Override

When Manual_Discount_Pct is set, it replaces global_discount_factor entirely.
Single step: u_final = u_gross x (1 - Manual_Discount_Pct/100) x CAP

## Files to Modify

1. calculations.py – Revenue branch (~lines 169-235): replace discount logic
2. CLAUDE.md – Update Business Logic section with new formula

## Out of Scope

- No changes to sidebar params UI (all 5 parameters remain)
- No changes to MANPOWER / OPERATION / INVESTMENT branches
- No column renames in the output DataFrame
