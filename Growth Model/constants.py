class Category:
    REVENUE = "Revenue"
    MANPOWER = "Manpower"
    OPERATION = "Operation"
    INVESTMENT = "Investment"


CAT_MAP = {
    Category.REVENUE: "הכנסות והיקף פעילות",
    Category.MANPOWER: "מצבת כוח אדם",
    Category.OPERATION: "הוצאות תפעול שוטפות",
    Category.INVESTMENT: "השקעות הקמה וציוד",
}

SESSION_STATE_DEFAULTS = {
    'growth_items': [],
    'history': [],
    'general_comments': "",
    'manpower_form_cost': 0.0,
    'view_mode': 'edit',
    'latest_df_flat_mapping': {},
    'srv_multi_select': [],
    'def6': [],
    'has_unsaved_changes': False,
}
