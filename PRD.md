# Product Requirements Document (PRD)
## Personal Finance & Expense Tracker Web Application

---

## 1. Document Overview
- **Project Name:** Personal Expense Tracker
- **Document Version:** 1.0.0
- **Document Status:** Approved / Baseline
- **Target Release:** College Project / Academic Demonstration
- **Role:** Senior Product Manager Specification

---

## 2. Project Objective
The objective of this project is to develop a practical, reliable, and functional personal finance tracking web application for college-level demonstration. The application empowers registered individuals to monitor their personal cash flows by recording income and expense transactions, organizing them into categories, defining monthly expense budgets with progress alerts, analyzing visual financial trends, and generating downloadable monthly summaries.

The system emphasizes high correctness, user data isolation, clear usability, and maintainable architectural design over unnecessary architectural complexity.

---

## 3. Target Users & Personas
- **Primary Persona: College Student / Young Professional**
  - Needs a straightforward, intuitive tool to log daily expenditures (e.g., food, books, rent, transit).
  - Wants clear visibility into monthly cash flow (income vs. expenses) and remaining balance.
  - Needs spending guardrails (budgets) to prevent month-end budget blowouts.
  - Requires simple exports (CSV) for personal archiving or academic project review.

---

## 4. Technology Stack & Constraints

### 4.1 Permitted Architecture & Libraries
To maintain strict adherence to project constraints and avoid over-engineering, only the following technologies are approved:

| Layer | Approved Technology |
|---|---|
| **Programming Language** | Python 3.10+ |
| **Backend Framework** | Flask |
| **Database ORM** | Flask-SQLAlchemy |
| **Authentication & Session** | Flask-Login |
| **Form & CSRF Protection** | Flask-WTF |
| **Database Engine** | SQLite 3 |
| **Template Engine** | Jinja2 |
| **UI Framework & Styling** | Bootstrap 5 (CSS & JS bundle) |
| **Client-Side Scripting** | Vanilla JavaScript (ES6+) |
| **Data Visualization** | Chart.js (via CDN) |
| **Environment Configuration** | python-dotenv |

### 4.2 Explicit Technical Constraints
- **Architecture:** Traditional Server-Side Rendered (SSR) Multi-Page Application (MPA).
- **Prohibited:** Single Page Application (SPA) frameworks (React, Vue, Angular), dedicated REST APIs, microservices, containerization/Docker tooling, asynchronous message brokers, background task queues, and external cloud dependencies.

---

## 5. Core Feature Specifications

### 5.1 User Authentication & Authorization
- **Registration (`/register`):**
  - User fields: `username` (unique, 3–30 characters), `email` (unique, valid email format), `password` (minimum 6 characters), and password confirmation.
  - On registration, automatically provision a default set of system categories for the new user.
  - Passwords must be hashed using a secure cryptographic algorithm (e.g., `werkzeug.security.generate_password_hash`).
- **Login (`/login`):**
  - Authenticate using username or email along with password.
  - Maintain session state via Flask-Login session cookies.
  - Provide a "Remember Me" session persistence option.
- **Logout (`/logout`):**
  - Invalidate session, clear session cookies, and redirect to login page.
- **Access Control:**
  - All application routes except `/login`, `/register`, and static assets require authentication (`@login_required`).
  - Strict multi-tenancy at database level: every query must filter by the authenticated `current_user.id`.

### 5.2 Category Management
- **Purpose:** Serve as the single source of truth for transaction classification and transaction type.
- **Attributes:**
  - `id`: Primary key
  - `user_id`: Foreign key referencing User
  - `name`: Category label (e.g., "Groceries", "Salary")
  - `category_type`: Enumeration `['INCOME', 'EXPENSE']`
- **Default System Categories:**
  - **Expense Defaults:** Food & Dining, Rent & Housing, Transportation, Utilities, Entertainment, Education, Healthcare, Miscellaneous.
  - **Income Defaults:** Salary, Freelance / Side Hustle, Stipend / Allowance, Investments, Gifts, Other Income.
- **Business Rules:**
  - Case-insensitive uniqueness for `(user_id, name, category_type)` (a user cannot have two expense categories named "Food").
  - Prevent deletion of categories associated with existing transactions unless transactions are reclassified or safely handled.
  - Users can create custom categories for either category type.

### 5.3 Transaction Management
- **Attributes:**
  - `id`: Primary key
  - `user_id`: Foreign key referencing User
  - `category_id`: Foreign key referencing Category (determines type)
  - `title`: Short descriptive name (e.g., "Monthly Bus Pass", max 100 characters)
  - `amount`: Positive numerical value stored as `Numeric(10, 2)` / `Decimal` (must be `> 0.00`)
  - `payment_method`: Dropdown choice (`Cash`, `Debit Card`, `Credit Card`, `Bank Transfer`, `UPI / Digital Wallet`, `Other`)
  - `description`: Optional text field for notes (max 255 characters)
  - `transaction_date`: Date picker field (`YYYY-MM-DD`), defaulting to current date
  - `created_at`: Timestamp
- **Derived Transaction Type:**
  - **Rule:** Transaction type (`INCOME` vs. `EXPENSE`) is strictly derived via `transaction.category.category_type`. No redundant `transaction_type` column will be stored in the transaction table.
- **Operations:**
  - **Create:** Modal or dedicated form with category selection grouped or filtered by type.
  - **Read / List (`/transactions`):** Paginated or clear tabular listing showing Date, Title, Category, Payment Method, Amount (color-coded: green for Income, red for Expense), and Actions.
  - **Search & Filtering:**
    - Filter by keyword search on `title` (case-insensitive substring match).
    - Filter by `category_id`.
    - Filter by transaction type (`INCOME` vs. `EXPENSE`).
    - Filter by date range (`start_date` to `end_date`).
    - Sort order toggle: Date (newest first / oldest first) and Amount (highest first / lowest first).
  - **Edit (`/transactions/<id>/edit`):** Pre-populated form. Ownership check enforced.
  - **Delete (`/transactions/<id>/delete`):** CSRF-protected POST request with explicit JavaScript confirmation dialog. Ownership check enforced.

### 5.4 Monthly Budgets
- **Purpose:** Enforce spending limits for specific expense categories within a specified calendar month.
- **Attributes:**
  - `id`: Primary key
  - `user_id`: Foreign key referencing User
  - `category_id`: Foreign key referencing Category (must have `category_type == 'EXPENSE'`)
  - `month`: Integer (1 to 12)
  - `year`: Integer (e.g., 2026)
  - `amount`: Budget limit stored as `Numeric(10, 2)` (must be `> 0.00`)
- **Business Rules & Calculations:**
  - Unique constraint on `(user_id, category_id, month, year)`. Duplicate budgets for the same category in the same month/year are rejected.
  - Budgets cannot be set on `INCOME` categories.
  - `amount_spent` = Sum of all expense transactions for `category_id` where transaction date falls within the designated calendar month and year.
  - `remaining_amount` = `amount - amount_spent`.
  - `percentage_used` = `(amount_spent / amount) * 100`.
- **UI Progress & Status Alerts:**
  - **Normal (`< 80%`):** Bootstrap progress bar in green (`bg-success`).
  - **Warning (`>= 80%` and `<= 100%`):** Bootstrap progress bar in yellow/orange (`bg-warning`) with alert text "Approaching limit".
  - **Exceeded (`> 100%`):** Bootstrap progress bar in red (`bg-danger`) with alert badge "Budget Exceeded" and negative remaining amount clearly shown.

### 5.5 Dashboard & Visual Analytics
- **Timeframe:** Current active calendar month (e.g., current month & year of system date).
- **Summary KPI Cards:**
  1. **Current Month Income:** Total of all `INCOME` transactions for the current calendar month.
  2. **Current Month Expenses:** Total of all `EXPENSE` transactions for the current calendar month.
  3. **Current Month Net Balance:** `Current Month Income - Current Month Expenses`.
  4. **Transaction Count:** Total number of transactions recorded in the current month.
- **Data Visualizations (Chart.js):**
  1. **Category Expense Breakdown (Doughnut / Pie Chart):**
     - Aggregates expense totals by category for the current month.
     - Displays legends and category share percentages on hover.
     - Shows a clean empty state fallback ("No expenses recorded this month") when total expense is zero.
  2. **6-Month Cash Flow Trend (Bar Chart):**
     - Grouped or stacked bar chart spanning the last six consecutive calendar months (e.g., May to October).
     - Compares monthly total Income vs. monthly total Expenses side-by-side per month.
- **Recent Activity Table:**
  - Displays the 5 most recent transactions with quick links to view all transactions.

### 5.6 Monthly Reports & Data Export
- **Report Generator (`/reports`):**
  - Month and Year selector dropdowns (defaulting to current month/year).
  - "Generate Report" action button.
- **Report Content:**
  - **Executive Summary:** Total Income, Total Expenses, Net Savings/Balance, Savings Rate (`(Net / Income) * 100` if income > 0), and Transaction Count.
  - **Expense Insights:** Category-wise breakdown table with percentage distribution, plus callout of the **Largest Single Expense** of the month.
  - **Detailed Ledger:** Full listing of all transactions in the selected period.
  - **Budget vs. Actual:** Performance summary of all categories with active budgets in that month.
- **CSV Data Export:**
  - Dedicated "Export as CSV" button.
  - Streamed dynamic CSV file named `expense_report_<YYYY>_<MM>.csv`.
  - Export columns: `Date`, `Title`, `Type`, `Category`, `Payment Method`, `Amount`, `Description`.
  - Strictly filtered to the selected month, year, and authenticated user.

---

## 6. Data Integrity & Business Rules
1. **Currency & Monetary Precision:** All financial figures must use `Numeric(10, 2)` (or SQLite `DECIMAL`/`FLOAT` mapped via Python `Decimal`) to avoid floating-point rounding errors.
2. **Positive Value Constraint:** Form inputs and database validations must reject non-positive amounts (`amount <= 0`).
3. **Derived Transaction Types:** Transactions do not hold a `type` string; their type is dynamically evaluated based on the related `Category.category_type`.
4. **Tenant Data Boundary:** No SQL query may execute without `user_id == current_user.id`. Direct URL manipulation (`/transactions/999/edit`) must return an HTTP 403 Forbidden or HTTP 404 Not Found if the resource does not belong to the active user.
5. **Date Filtering Strictness:** Monthly aggregates must compute between `YYYY-MM-01 00:00:00` and the last day of that calendar month inclusive.
6. **Graceful Empty States:** Dashboards, charts, reports, and transaction lists must render user-friendly informational notices when no records exist, without UI collapse or JavaScript errors.

---

## 7. User Experience & Design Guidelines
- **Look & Feel:** Clean, professional, modest aesthetic using standard Bootstrap 5 components and utility classes. Suitable for academic evaluation.
- **Navigation:** Fixed or responsive top navbar with Brand title, Dashboard, Transactions, Budgets, Reports, Category Settings, and User Profile / Logout menu.
- **Responsiveness:** Fluid grid layout that transitions gracefully from multi-column desktop views to single-column mobile views.
- **Flash Feedback:** System feedback for user actions via standard Bootstrap alert banners (e.g., `success`, `danger`, `warning`, `info`).
- **Destructive Actions:** Deletion of any record (transaction, budget, category) must require a confirmation step before execution.
- **Form Usability:** Clear inline field labels, helpful placeholder text, and explicit validation feedback directly under invalid inputs.

---

## 8. Security & Reliability
- **Password Security:** Salted and hashed passwords using Werkzeug's default recommended PBKDF2/SHA256 or Scrypt algorithms.
- **CSRF Protection:** All mutating requests (POST) must validate a CSRF token provided by Flask-WTF.
- **Input Sanitization & Server-Side Validation:** All form submissions are strictly validated on the server using WTForms validators (`DataRequired`, `NumberRange(min=0.01)`, `Length`, `Email`).
- **Secrets Management:** Application secret key, database URI, and configuration parameters must be loaded via `.env` using `python-dotenv`. A `.env.example` file must be provided, and `.env` must be ignored in `.gitignore`.
- **Defensive Error Handling:** Proper HTTP 404 and 500 error pages, avoiding raw stack trace leaks to the client.

---

## 9. Out of Scope (Explicit Exclusions)
The following features are strictly prohibited from this project scope:
- Integration with real bank APIs or Open Banking interfaces (e.g., Plaid, Yodlee).
- Payment gateways, credit card processing, or real-money transfers (e.g., Stripe, PayPal).
- AI/ML features (e.g., LLM receipt scanning, automated categorization, predictive forecasting).
- Multi-currency conversions, exchange rate APIs, or live currency feeds.
- Investment tracking (stocks, mutual funds, cryptocurrency portfolios).
- Recurring automated transactions or background job schedulers (e.g., Celery, APScheduler).
- External notification channels (e.g., Twilio SMS, automated email push notifications).
- Microservices, Docker containers, Kubernetes, or complex cloud infrastructure.

---

## 10. Testable Acceptance Criteria

### AC 1: User Authentication
- [ ] Users can register with unique credentials and receive an error on duplicate email/username.
- [ ] New user registration automatically seeds default income and expense categories.
- [ ] Registered users can log in, establish an active session, and log out.
- [ ] Unauthenticated requests to protected pages redirect immediately to `/login`.
- [ ] User A cannot see, edit, or delete any record created by User B.

### AC 2: Category Management
- [ ] Users can view default categories separated by type (Income vs. Expense).
- [ ] Users can create a custom category under Income or Expense.
- [ ] Creating a duplicate category name within the same type for the same user is rejected with a clear error.
- [ ] Categories tied to active transactions cannot be deleted without user warning/prevention.

### AC 3: Transaction Management
- [ ] Users can create an income or expense transaction with required fields (`title`, `amount > 0`, `category_id`, `payment_method`, `transaction_date`).
- [ ] Transaction type is automatically determined by the category selected.
- [ ] Users can edit all fields of an existing transaction they own.
- [ ] Users can delete a transaction they own after confirming the prompt.
- [ ] The transactions table allows searching by title, filtering by category, type, and date range, and sorting by date and amount.

### AC 4: Dashboard & Charts
- [ ] Current month card figures (Income, Expenses, Net Balance, Count) match the exact sum of transactions for the current calendar month.
- [ ] Doughnut chart renders the correct category expense proportions for the current month.
- [ ] Bar chart displays income and expense bars side-by-side for the last 6 calendar months.
- [ ] When no transactions exist, charts render clear empty state placeholders rather than crashing.

### AC 5: Monthly Budgets
- [ ] Users can set a monthly budget on any expense category for a selected month/year.
- [ ] Setting a budget on an income category is prohibited.
- [ ] Adding a second budget for the same category in the same month/year is rejected.
- [ ] Progress bars accurately calculate `(spent / budget) * 100`.
- [ ] Progress bar turns warning yellow at 80% to 100%, and danger red with "Exceeded" indicator when spending surpasses 100%.

### AC 6: Monthly Reports & CSV Export
- [ ] Selecting a month and year updates the report summary, category breakdown, and ledger.
- [ ] The largest single expense is accurately identified and highlighted.
- [ ] Clicking "Export as CSV" downloads a CSV file containing only the authenticated user's transactions for the selected month/year.
- [ ] The exported CSV opens correctly in spreadsheet viewers (e.g., Microsoft Excel, Google Sheets) with correct column headers and formatting.
