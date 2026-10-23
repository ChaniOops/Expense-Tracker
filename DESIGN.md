# UI/UX Design Specification
## Personal Finance & Expense Tracker Web Application

---

## 1. Design Overview & Principles
- **Document Version:** 1.0.0
- **Document Status:** Approved / Baseline
- **Target Audience:** College project evaluators, students, and personal finance users.
- **Foundational Principles:**
  - **Simplicity & Clarity:** Information is structured hierarchically with clear visual priorities. No distracting elements, no excessive animations, and no unnecessary decorative clutter.
  - **Academic & Professional Aesthetic:** Modern, clean, and modest, utilizing native **Bootstrap 5.3+** design patterns rather than an over-engineered SaaS framework.
  - **Information Density:** Clean white-space with high data legibility, ensuring numbers, dates, and currency are instantly readable.
  - **Accessibility & Contrast:** High contrast text, explicit form labels, keyboard navigation indicators, and redundant visual cues (colors accompanied by signs or text badges).

---

## 2. Visual Style & Design System

### 2.1 Color Palette
The color palette leverages Bootstrap 5's semantic tokens customized for personal financial applications:

| Token | Hex Code | Semantic Role | Usage Example |
|---|---|---|---|
| `--bs-primary` | `#0d6efd` | Primary Action / Accent | Primary buttons, active nav links, brand icon |
| `--bs-secondary` | `#6c757d` | Secondary / Neutral | Cancel buttons, secondary badges, helper text |
| `--bs-success` | `#198754` | Positive Flow / Income | Income values, surplus balance, normal budget (<80%) |
| `--bs-warning` | `#ffc107` | Warning / Attention | Budget alert threshold (80%–100%), pending warnings |
| `--bs-danger` | `#dc3545` | Negative Flow / Expense | Expense values, deficit balance, budget exceeded (>100%) |
| `--bs-body-bg` | `#f8f9fa` | Page Background | Neutral, soft light gray background for low eye-strain |
| `--bs-surface` | `#ffffff` | Card / Container Surface | Form cards, KPI metric tiles, table containers |
| `--bs-body-color`| `#212529` | Primary Body Text | Main text, table data, titles |
| `--bs-muted` | `#6c757d` | Muted Text | Dates, descriptions, subtitle metadata |
| `--bs-border` | `#dee2e6` | Standard Border | Card dividers, table borders, input strokes |

#### Financial Color Semantics
- **Income Transactions:** Green text (`text-success`), preceded by a `+` sign and an "Income" badge (`badge bg-success-subtle text-success`).
- **Expense Transactions:** Red text (`text-danger`), preceded by a `-` sign and an "Expense" badge (`badge bg-danger-subtle text-danger`).
- **Net Balance:** Green if $\ge 0.00$; Red if $< 0.00$.
- **Budgets:**
  - $< 80\%$ utilized: Green progress bar (`bg-success`).
  - $80\% - 100\%$ utilized: Amber progress bar (`bg-warning text-dark`).
  - $> 100\%$ utilized: Red progress bar (`bg-danger`) with an exclamation badge.

### 2.2 Typography
Uses system font stack for instant loading and crisp rendering across OS platforms:
- **Font Family:** `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif`
- **Monospace (for amounts & numbers):** `SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace`
- **Scale:**
  - Page Title (`h2`): 1.75rem (28px), font-weight 600
  - Section Header (`h4` / `h5`): 1.25rem–1.5rem, font-weight 600
  - KPI Stat Figures: 1.85rem (30px), font-weight 700, tabular numbers
  - Standard Body Text: 1rem (16px), regular 400
  - Metadata / Small text: 0.875rem (14px), regular 400

### 2.3 Borders, Shadows, and Elevation
- **Cards:** White background, thin border (`1px solid #dee2e6`), border radius `rounded-3` (8px), subtle elevation (`shadow-sm`).
- **Modals:** Centered, border radius `rounded-3`, standard backdrop blur or dim overlay.
- **Buttons:** Border radius `rounded-2` (6px), padding `py-2 px-3`. No pill-shaped or glowing buttons.
- **Inputs:** Standard Bootstrap input height (`form-control`), border radius `rounded-2`, clear focus rings with default browser accessible outline.

---

## 3. Application Layout Architecture

### 3.1 Global Navigation & Shell
A single standard **Bootstrap Navbar** pinned to the top of all authenticated pages:
- **Brand / Logo:** Simple financial icon (or standard SVG wallet/chart) + "ExpenseTracker" in bold text.
- **Primary Nav Links:**
  - **Dashboard** (`/`)
  - **Transactions** (`/transactions`)
  - **Budgets** (`/budgets`)
  - **Reports** (`/reports`)
  - **Categories** (`/categories`)
- **Right-Aligned User Profile Menu:**
  - Displays logged-in user name (e.g., `👤 John Doe`).
  - Dropdown or direct link with a clear **Logout** button.
- **Mobile Behavior:** Collapses into a responsive hamburger menu (`navbar-toggler`) that opens a clean dropdown list on mobile screens.

```
+-----------------------------------------------------------------------------------+
| [Brand] ExpenseTracker    Dashboard   Transactions   Budgets   Reports   Categories  | [User: alex] [Logout] |
+-----------------------------------------------------------------------------------+
|  [Flash Message: Transaction added successfully!                             (X)] |
+-----------------------------------------------------------------------------------+
|  Page Title Header (e.g. "Monthly Budgets")             [+ Add New Budget Button] |
|                                                                                   |
|  Main Content Container (Bootstrap container-xl)                                  |
|                                                                                   |
+-----------------------------------------------------------------------------------+
|  Footer: (c) 2026 Expense Tracker • College Capstone Project                       |
+-----------------------------------------------------------------------------------+
```

### 3.2 Flash Notification System
- Positioned immediately beneath the navbar, full container width.
- Rendered via standard Bootstrap alerts:
  - Success messages: `alert alert-success alert-dismissible fade show`
  - Error messages: `alert alert-danger alert-dismissible fade show`
  - Warning messages: `alert alert-warning alert-dismissible fade show`
- Include a close (`btn-close`) button to allow immediate dismissal.

---

## 4. Screen-by-Screen Specifications

### 4.1 Authentication Pages (`/login`, `/register`)
- **Layout:** Centered card layout on a clean neutral background (`col-md-6 col-lg-4 mx-auto mt-5`).
- **Brand Identity:** Centered application title and sub-header ("Sign in to your account" or "Create an account").
- **Form Controls:**
  - Floating labels or clear static labels above inputs (`form-label`).
  - Inputs: Username/Email, Password, Password Confirmation (on register).
  - Checkbox for "Remember Me" (on login).
  - Submit button: `btn-primary w-100 py-2 mt-3`.
- **Navigation Links:**
  - Login page includes: "Don't have an account? Register here".
  - Register page includes: "Already have an account? Log in here".
- **Validation Presentation:** Server-side validation errors displayed in an alert or inline beneath the invalid field (`invalid-feedback d-block`).

---

### 4.2 Dashboard (`/`)
Designed for an immediate, high-level snapshot of the active calendar month.

1. **Header Row:**
   - Left: Greeting & Current Month indicator (e.g., "Dashboard — October 2026").
   - Right: Quick Action Buttons: `+ Add Transaction` (primary) and `+ Set Budget` (outline secondary).

2. **Top Metric Cards (4-column grid: `col-12 col-sm-6 col-lg-3`):**
   - **Card 1 (Monthly Income):** Label "Total Income", amount in `text-success` (e.g., `$3,500.00`), subtitle "Current month".
   - **Card 2 (Monthly Expenses):** Label "Total Expenses", amount in `text-danger` (e.g., `$1,820.50`), subtitle "Current month".
   - **Card 3 (Net Balance):** Label "Net Balance", amount in `text-success` or `text-danger` (e.g., `+$1,679.50`), subtitle "Income minus expenses".
   - **Card 4 (Transactions):** Label "Total Transactions", integer count (e.g., `24`), subtitle "Logged this month".

3. **Analytics Section (2-column layout: `col-12 col-lg-5` and `col-12 col-lg-7`):**
   - **Left Card: Expense Breakdown by Category:**
     - Header: "Current Month Expenses by Category".
     - Body: Chart.js Doughnut Chart container (`style="max-height: 280px;"`).
     - Empty State: If expenses = $0.00, render a centered gray icon and message: *"No expenses logged for this month yet."*
   - **Right Card: 6-Month Income vs. Expenses:**
     - Header: "Income vs. Expenses (Last 6 Months)".
     - Body: Chart.js Bar Chart with side-by-side bars (Green for Income, Red for Expense) across month labels.
     - Empty State: Fallback message if no transaction history exists.

4. **Recent Activity Table (Full width: `col-12 mt-4`):**
   - Header: "Recent Transactions" with a link to "View All".
   - Table displaying the last 5 transactions: `Date`, `Title`, `Category`, `Payment Method`, `Amount`.
   - Empty State: *"No recent transactions found. Click '+ Add Transaction' to get started."*

---

### 4.3 Transactions Screen (`/transactions`)
A centralized ledger designed for efficient scanning, filtering, and data management.

1. **Header & Action Bar:**
   - Page Title: "Transactions Ledger".
   - Action: `+ Add Transaction` button opening the transaction creation form or modal.

2. **Filter & Search Toolbar (Card with `p-3 mb-3 bg-white`):**
   - **Row 1:**
     - Search Input: Text search matching transaction title (`col-12 col-md-4`).
     - Category Dropdown: "All Categories", grouped by Income and Expense (`col-6 col-md-3`).
     - Type Dropdown: "All Types", "Income", "Expense" (`col-6 col-md-2`).
   - **Row 2:**
     - Date Range: `Start Date` and `End Date` inputs (`col-6 col-md-2` each).
     - Sort By: Dropdown ("Date: Newest First", "Date: Oldest First", "Amount: High to Low", "Amount: Low to High") (`col-6 col-md-3`).
     - Buttons: `Filter` (primary) and `Reset` (outline-secondary) (`col-12 col-md-2 d-flex align-items-end gap-2`).

3. **Transaction Table (`table table-hover align-middle`):**
   - **Columns:**
     - `Date` (Monospace format `YYYY-MM-DD`)
     - `Title` (Bold text with optional description text beneath in muted small font)
     - `Category` (Badge indicating category name and type)
     - `Payment Method` (Simple badge or muted text)
     - `Amount` (Right-aligned, bold, green `+ $X.XX` or red `- $X.XX`)
     - `Actions` (Right-aligned, Edit button `btn-outline-primary btn-sm` and Delete button `btn-outline-danger btn-sm`)

4. **Delete Confirmation Dialog:**
   - Native Bootstrap modal triggering on Delete click:
     - Header: "Confirm Deletion"
     - Body: "Are you sure you want to delete the transaction **[Title]** for **[Amount]**? This action cannot be undone."
     - Actions: `Cancel` (`btn-secondary`) and `Delete Transaction` (`btn-danger`).

5. **Responsive Mobile Strategy:**
   - Wrap the table in `.table-responsive` to prevent layout overflow.
   - For extra small viewports ($< 576\text{px}$), optional compact stacking where Title and Amount are prominent, with Category and Date in smaller text below.

---

### 4.4 Budgets Screen (`/budgets`)
Focused on visual feedback and spending control.

1. **Header & Creation Form:**
   - Header: "Monthly Budgets".
   - Budget Setup Card (`card mb-4`):
     - Form fields: Expense Category (dropdown filtered strictly to Expense categories), Month selector, Year selector, Budget Limit Amount ($).
     - Action button: `Save Budget` (`btn-primary`).

2. **Budget Monitoring Grid (`row g-3`):**
   - Each budget renders as an individual metric card (`col-12 col-md-6 col-lg-4`):
     - **Card Header:** Category Name badge + Month/Year text.
     - **Card Body:**
       - **Figures:**
         - Budget Limit: `$500.00`
         - Spent: `$420.00`
         - Remaining: `+$80.00` (or `-$50.00` in red bold if exceeded)
       - **Progress Bar (`progress` with height `16px`):**
         - Value: `84%`
         - Color Coding:
           - Green (`bg-success`): Spent $< 80\%$
           - Amber (`bg-warning text-dark`): Spent $80\% - 100\%$ (accompanied by "⚠️ Approaching limit")
           - Red (`bg-danger`): Spent $> 100\%$ (accompanied by "🚨 Budget Exceeded!")
     - **Card Footer:** Action row with Edit and Delete options.

3. **Empty State:**
   - When no budgets exist for the selected period:
     - Centered card: *"No monthly budgets defined for this period. Use the form above to set your first category budget."*

---

### 4.5 Monthly Reports Screen (`/reports`)
Provides exportable financial statements and category breakdowns for any specified month.

1. **Filter & Action Header:**
   - Month and Year dropdown selectors.
   - Action Buttons: `Generate Report` (`btn-primary`) and `Export CSV` (`btn-outline-success` with download icon).

2. **Summary KPI Strip (4 cards):**
   - Total Income, Total Expenses, Net Savings, Transaction Count for the selected period.

3. **Insight Callout Section:**
   - **Largest Expense Tile (`alert alert-light border`):**
     - Displays the title, category, date, and amount of the single largest expense in the selected month.
     - If no expenses exist: Displays *"No expense transactions recorded in this period."*

4. **Category Breakdown Table:**
   - Columns: `Category Name`, `Category Type`, `Total Spent`, `Share of Total Expenses (%)`.
   - Displays percentage distribution with subtle visual inline bars.

5. **Period Ledger Table:**
   - Chronological table of all transactions within the selected month.

---

### 4.6 Category Settings Screen (`/categories`)
Enables users to manage default and custom categories.

1. **Header:** "Category Management".
2. **Add Category Card:**
   - Simple inline or stacked form: Category Name input, Category Type selector (`Expense` or `Income`), `Add Category` button.
3. **Category Lists (2 Columns):**
   - Column 1: **Expense Categories** list-group with badges.
   - Column 2: **Income Categories** list-group with badges.
   - Each list item includes category name, transaction count badge, and a delete button (disabled if transaction count $> 0$ with tooltip explaining why).

---

## 5. Interaction States & System Feedback

| State / Event | Expected Visual & Behavioral Feedback |
|---|---|
| **Hover on clickable items** | Table rows highlight (`table-hover`), buttons darken slightly, card elevation subtly increases. |
| **Form Input Focus** | Bootstrap standard blue focus ring (`box-shadow: 0 0 0 0.25rem rgba(13, 110, 253, 0.25)`). |
| **Invalid Form Submission** | Red border on inputs (`is-invalid`), error message text rendered directly below the input in red text (`invalid-feedback`). |
| **Successful Record Action** | Flash banner at top of target screen with green background (`alert-success`), automatically dismissible. |
| **Delete Action** | Triggers modal overlay with exact record details. Prevents accidental one-click deletion. |
| **Zero Filter Matches** | Replaces table rows with a single spanning row: *"No transactions match your search/filter criteria. [Reset Filters]"* |
| **No Data in Charts** | Renders a clean styled HTML empty-state box instead of an empty or broken canvas element. |

---

## 6. Responsive Breakpoint Behavior

| Component | Desktop ($\ge 992\text{px}$) | Tablet ($768\text{px} - 991\text{px}$) | Mobile ($< 768\text{px}$) |
|---|---|---|---|
| **Navigation** | Full horizontal bar with all links visible | Collapsed navbar with toggle button | Collapsed hamburger menu, full-width dropdown |
| **Metric Cards** | 4 columns side-by-side (`col-lg-3`) | 2 columns per row (`col-md-6`) | 1 column stacked (`col-12`) |
| **Dashboard Charts** | Side-by-side (5 cols : 7 cols) | Stacked vertically | Stacked vertically, fixed canvas height ($240\text{px}$) |
| **Filter Toolbar** | Single/double horizontal row | Stacked into 2 rows | Full vertical stack with full-width submit button |
| **Data Tables** | Full table with all columns | Horizontal scroll container (`.table-responsive`) | Responsive table with abbreviated padding |
| **Budget Grid** | 3 cards per row (`col-lg-4`) | 2 cards per row (`col-md-6`) | 1 card per row (`col-12`) |

---

## 7. Accessibility (a11y) Guidelines
- **Form Controls:** Every input, select, and textarea has a programmatic `<label for="...">` matching the input `id`.
- **Keyboard Navigation:** All interactive elements (buttons, inputs, links, modals) are focusable via `Tab` key and activate via `Enter` or `Space`.
- **Color Independence:** Colors are never the sole indicator of state:
  - Income/Expense has `+` / `-` prefixes and textual type labels.
  - Budgets have percentage text and status badges ("Normal", "Approaching limit", "Exceeded") in addition to progress bar colors.
- **Heading Hierarchy:** Each page has exactly one `<h1>` or `<h2>` page title, followed by structured `<h3>`/`<h4>` section cards.
- **Chart Accessibility:** Screen readers are provided with hidden accessible tables or readable text summaries representing the chart data.

---

## 8. Implementation Constraints & Asset Architecture
- **CSS:** Bootstrap 5.3 CDN CSS + one minimal custom CSS file (`static/css/styles.css`, $< 150$ lines) for minor spacing adjustments and table alignment.
- **JavaScript:** Vanilla JavaScript (`static/js/main.js`, $< 200$ lines) for modal confirmations, date defaults, and Chart.js initialization.
- **Chart.js:** Included via CDN (`https://cdn.jsdelivr.net/npm/chart.js`).
- **Templates:** Modular Jinja2 hierarchy:
  - `templates/base.html` (Shell, navbar, flash messages, script includes)
  - `templates/auth/login.html`, `templates/auth/register.html`
  - `templates/dashboard/index.html`
  - `templates/transactions/index.html`, `templates/transactions/form.html`
  - `templates/budgets/index.html`
  - `templates/reports/index.html`
  - `templates/categories/index.html`
