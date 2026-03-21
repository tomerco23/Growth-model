# -*- coding: utf-8 -*-
"""Unit tests for the new additive discount cascade formula."""
import sys
sys.path.insert(0, ".")
from calculations import calculate_detailed_rows

PARAMS = {
    "HMO_DISCOUNT":    0.185,
    "VOL_DISCOUNT":    0.019,
    "APPEALS_PROV":    0.04,
    "OVERHEAD_RATE":   0.29,
    "CAP_RATE_FACTOR": 0.35,
    "NO_SHOW_RATE":    0.0,
}

# combined discount = 0.019 + 0.04 + 0.29 = 0.349
# u_final = u_gross * (1 - 0.349) * 0.35 = u_gross * 0.22785

U_GROSS          = 1000.0
EXPECTED_U_FINAL = round(U_GROSS * (1 - 0.349) * 0.35, 6)   # 227.85


def _revenue_item(overrides=None):
    item = {
        "Category": "Revenue",
        "Name": "001 - test",
        "Quantity": 100,
        "Unit_Revenue": U_GROSS,
        "Is_New": False,
        "Is_Private": False,
        "Manual_No_Show": None,
        "Manual_Discount_Pct": None,
        "Pct_Opt": 0,
        "Pct_Pess": 0,
        "Growth_Y2": 0,
        "Growth_Y3": 0,
        "Growth_Y4": 0,
        "Rev_Sess_Vol": 0,
        "Rev_Sess_Cost": 0,
    }
    if overrides:
        item.update(overrides)
    return item


def test_unit_rate_after_discounts():
    df, *_ = calculate_detailed_rows([_revenue_item()], PARAMS)
    row = df[df["סוג"] == "הכנסה"].iloc[0]
    actual = round(row["תעריף יחידה אחרי הנחות"], 6)
    assert actual == EXPECTED_U_FINAL, f"expected {EXPECTED_U_FINAL}, got {actual}"
    print(f"PASS: u_final (after discounts) = {actual}")


def test_unit_rate_under_cap():
    df, *_ = calculate_detailed_rows([_revenue_item()], PARAMS)
    row = df[df["סוג"] == "הכנסה"].iloc[0]
    actual = round(row["תעריף יחידה תחת cap"], 6)
    assert actual == EXPECTED_U_FINAL, f"expected {EXPECTED_U_FINAL}, got {actual}"
    print(f"PASS: u_final (under cap) = {actual}")


def test_net_pocket():
    qty = 100
    df, *_ = calculate_detailed_rows([_revenue_item({"Quantity": qty})], PARAMS)
    row = df[df["סוג"] == "הכנסה"].iloc[0]
    expected = round(qty * EXPECTED_U_FINAL, 4)
    actual   = round(row['סה"כ נטו לכיס'], 4)
    assert actual == expected, f"expected {expected}, got {actual}"
    print(f"PASS: net_pocket = {actual:,.2f}")


def test_private_bypass():
    qty = 50
    df, *_ = calculate_detailed_rows([_revenue_item({"Quantity": qty, "Is_Private": True})], PARAMS)
    row = df[df["סוג"] == "הכנסה"].iloc[0]
    expected = round(qty * U_GROSS, 4)
    actual   = round(row['סה"כ נטו לכיס'], 4)
    assert actual == expected, f"expected {expected}, got {actual}"
    print(f"PASS: private = {actual:,.2f}")


def test_manual_discount():
    manual_pct = 30.0
    qty = 100
    df, *_ = calculate_detailed_rows([_revenue_item({"Quantity": qty, "Manual_Discount_Pct": manual_pct})], PARAMS)
    row = df[df["סוג"] == "הכנסה"].iloc[0]
    expected = round(qty * U_GROSS * (1 - manual_pct/100) * PARAMS["CAP_RATE_FACTOR"], 4)
    actual   = round(row['סה"כ נטו לכיס'], 4)
    assert actual == expected, f"expected {expected}, got {actual}"
    print(f"PASS: manual discount = {actual:,.2f}")


if __name__ == "__main__":
    print("=" * 60)
    test_unit_rate_after_discounts()
    test_unit_rate_under_cap()
    test_net_pocket()
    test_private_bypass()
    test_manual_discount()
    print("=" * 60)
    print("ALL TESTS PASSED")
