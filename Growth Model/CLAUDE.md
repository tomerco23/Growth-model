# Growth Model – Ichilov Hospital
## מודל צמיחה – איכילוב

You are the lead AI Developer for the "Growth Model" (מודל צמיחה), a Streamlit-based economic decision-support web app for hospital management. 

---

## Project Structure

```
Growth Model/
├── app.py           – Entry point, sidebar, session state, routing edit↔report
├── views.py         – UI: show_edit_view(), show_report_view(), show_marginal_productivity_tool()
├── calculations.py  – calculate_detailed_rows() → df_flat + KPIs
├── data_loading.py  – load_growth_data(), load_employee_counts()
├── constants.py     – Category enum, CAT_MAP, SESSION_STATE_DEFAULTS
├── utils.py         – normalize_code(), extract_clean_code_from_string(), format_number_str()
├── report.py        – Excel export (xlsxwriter)
└── CLAUDE.md        – this file
```

---

## Data Files

| File | Purpose |
|------|---------|
| `DB איכילוב.xlsx` | Main internal HR file – loaded via sidebar file_uploader |
| `תעריפי משרד הבריאות 2026.xlsx` | MOH price list – loaded as external file |

### Sheets in `DB איכילוב.xlsx`

#### `DB_HR_Costs` (header row index 4)
- **10,846 rows × 34 columns**
- Each job appears in **pairs of rows** by the `Values` column:
  - `'עלות כ״א'` → monthly salary cost (e.g. ₪15,866)
  - `'עלות משרות'` → headcount / FTE count (e.g. 1.00, 2.00)
- Columns: `Maarach, Agaf, Hativa, Machleket Em, Yahida, Job Desc, Values, [month columns Jan-2024 … Feb-2026]`
- **⚠️ No `'מספר עובדים'` column – it's called `'עלות משרות'`**
- **⚠️ No `'סכום שכר'` column – it's called `'עלות כ״א'`**

#### `DB_HR_Staffing` (header detected dynamically)
- FTE staffing data, used for job hierarchy/filter in the manpower form
- Parsed into `df_hr` (with `Annual_Cost`, `Monthly_Cost` merged in from HR_Costs)

#### `DB_Service_count` (header row index 3)
- **5,845 rows × 32 columns**
- Each row = one service code per unit, with monthly visit counts
- Columns: `Maarach, Agaf, Hativa, Machleket Em Key, Yahida Key, Code Desc, [ינואר 2024 … פברואר 2026]`
- 26 months of data (Jan 2024 – Feb 2026)
- Loaded via `_load_service_hierarchy()` → melted to `h_srv` with `[Original_Label, Date, Value]`

---

## Key Column Name Gotchas

```python
# data_loading.py search patterns – must match actual Excel column names:
cost_key: 'סכום' OR 'שכר' OR ('עלות' AND NOT 'משרות')  # matches 'עלות כ״א'
emp_key:  'עובדים' OR 'מספר' OR 'משרות'                 # matches 'עלות משרות'
```

---

## Data Flow

```
DB איכילוב.xlsx
  ├── DB_HR_Staffing  → _load_hr_staffing() → df_hr_structure (job hierarchy)
  ├── DB_HR_Costs     → _load_hr_costs()    → df_hr (+ Annual_Cost, Monthly_Cost)
  │                   → load_employee_counts() → df_emp_counts
  │                      [GROUP_COLS..., Total_Employee_Months, Avg_Monthly_Employees, Months_Count]
  └── DB_Service_count → _load_service_hierarchy() → df_srv_hier_map, h_srv

app.py passes to views:
  show_edit_view(..., df_emp_counts=df_emp_counts)
  show_report_view(..., h_srv=h_srv, df_emp_counts=df_emp_counts)
```

---

## Business Logic

### Revenue Calculation (`calculations.py`)
```
qty_net = qty × (1 - no_show_rate) × (0.93 if new_service)
u_net   = u_gross × (1 - hmo_discount) × (1 - vol_discount) × (1 - appeals_prov)
u_cap   = u_gross × cap_rate_factor
net_pocket = qty_net × u_net × (1 - overhead_rate)
```

### Marginal Productivity Tool (`show_marginal_productivity_tool`)
- **Numerator**: total services for selected service from `h_srv` (all months summed)
- **Denominator**: `Total_Employee_Months` for selected `Job Desc` from `df_emp_counts`
  - `Total_Employee_Months = Σ(monthly headcount)` e.g. 3 employees × 12 months = 36
- **Formula**: `productivity = total_services / total_emp_months`
- **Forecast**: `N employees × M months × productivity = additional services`

---

## Params (sidebar defaults)
```python
OVERHEAD_RATE  = 29%
HMO_DISCOUNT   = 18.5%
VOL_DISCOUNT   = 1.9%
APPEALS_PROV   = 4%
CAP_RATE_FACTOR = 35%
NO_SHOW_RATE   = 0%
```

---

## Session State Keys
```python
'growth_items'      # list of dicts – the model items
'view_mode'         # 'edit' | 'report'
'history'           # list of snapshots for undo
'general_comments'  # economist's notes, exported to Excel
```

---

## GROUP_COLS (HR hierarchy)
```python
['Maarach', 'Agaf', 'Hativa', 'Machleket Em', 'Yahida', 'Sector', 'Job Desc']
```

---

## What Was Deliberately Removed
- `build_marginal_productivity_map()` – used global employee denominator (wrong)
- `prod_map` parameter from `calculate_detailed_rows()` and all views
- 3 columns from revenue table: `שירותים היסטורי`, `תקנים`, `שירותים/תקן`

# Growth Model Project - AI Assistant Guidelines

## 🧠 The Multi-Agent Thinking Process
For EVERY feature request, bug fix, or architecture change, you MUST internally consult with these 4 personas before writing any code:
1. **The Product Manager (UX/UI)**: Focuses on Streamlit layout, reducing user cognitive load, visual storytelling, and clear Hebrew microcopy.
2. **The Chief Economist (Business Logic)**: Focuses on the accuracy of ROI, CAP scenarios, and generating actionable executive summaries.
3. **The Data Pipeline Engineer**: Focuses on robust error handling for messy Excel uploads and preventing crashes.
4. **The Performance Architect (Efficiency Expert)**: Focuses strictly on execution speed, memory optimization, and reducing app overhead. Evaluates time and space complexity before approving any code.

**Workflow:** When I ask for a feature, first output a short bulleted plan showing what each agent suggests (especially the Performance Architect). Wait for my approval before modifying the files.

## 🏗️ Strict Coding & Performance Standards
- **Performance First**: You MUST write the most efficient code possible. 
  - **No Loops in Pandas**: Use fully vectorized operations in `pandas` and `numpy`. Never use `iterrows()` or `apply()` if a vectorized alternative exists.
  - **Caching**: Liberally and correctly use `@st.cache_data` for heavy data loading and data processing functions so they only run once.
  - **Memory Management**: Load only required columns from Excel files (`usecols`), and use appropriate data types (e.g., `category` for repetitive strings) to save RAM.
- **Language**: All Python variables/functions in English. All UI elements (`st.write`, charts) in fluent Hebrew.
- **State**: Always use safely `st.session_state.get('key', default)`.## 🛠️ Tools & Skills at your disposal
Whenever you write logic or data processing code, use terminal commands to run `pytest` or Python scripts to verify your logic before confirming completion.

## ⏪ Version Control & Safety (Git)
Before making any significant changes to the codebase, you MUST:
1. Check the git status. If the working tree is clean, proceed. If not, ask me if you should commit the current state first.
2. After implementing a new feature or fixing a bug successfully, automatically run `git add .` and `git commit -m "Agent update: [Brief description of what was added/fixed]"`.
This ensures we always have a safe restore point to go back to. If a change breaks the app, you will help me use `git checkout` or `git revert` to undo it.
