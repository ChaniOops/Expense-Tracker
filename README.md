# Expense Tracker

A lightweight, robust personal finance tracking web application built with Python, Flask, SQLite, and Bootstrap 5.

---

## 1. Project Purpose & Features

The Expense Tracker provides personal financial management with strict multi-tenant isolation, decimal-safe monetary arithmetic, and real-time visualization.

### Key Features
- **User Authentication:** Secure registration, login with persistent remember-me cookies, password hashing via Werkzeug (`scrypt`), CSRF-protected logout, route guarding via `@login_required`, and show/hide password visibility toggles.
- **Transaction Management:** Full CRUD operations for income and expenses. Dynamic category-type derivation, multi-parameter search/filtering (keyword, category, type, date range), allowlisted sorting, and CSRF-protected deletion modals.
- **Financial Dashboard:** Real-time KPI summaries (Total Income, Total Expenses, Net Balance, Logged Transactions), recent transactions ledger, current-month budget summary, and Chart.js analytics (category expense doughnut chart and 6-month cash flow bar chart).
- **Monthly Budgets & Alerts:** Category-level spending limits with dynamic expenditure aggregation from the `transactions` table. Three-tier visual threshold states:
  - **Normal:** `< 80%` of budget used (green progress bar).
  - **Warning:** `80% – 100%` of budget used (amber progress bar, "⚠️ Approaching Limit").
  - **Exceeded:** `> 100%` of budget used (red progress bar, "🚨 Budget Exceeded!", highlighting overspent amount).
- **Monthly Reports & CSV Export:** Monthly financial statements with income/expense summaries, descending category expense breakdowns with share percentages, largest single expense callout, and RFC 4180-compliant CSV export with spreadsheet formula injection protection.
- **Indian Rupee (INR - ₹) Currency Convention:** All financial values across forms, cards, tables, charts, and reports are formatted in Indian Rupees using Indian numeral grouping (e.g. `₹1,25,000.00`). Database values remain pure numeric decimals.

---

## 2. Technology Stack & Prerequisites

- **Python Version:** Python 3.10+ (tested and verified on Python 3.12)
- **Framework:** Flask 3.0+
- **Database & ORM:** SQLite 3 with Flask-SQLAlchemy 3.1+ (foreign key constraints enforced via `PRAGMA foreign_keys = ON`)
- **Authentication:** Flask-Login
- **Security:** Flask-WTF (CSRF protection)
- **Frontend:** Jinja2 templates, Bootstrap 5.3 (CDN), Chart.js (CDN), Vanilla JavaScript (ES6+)
- **Testing:** Python `unittest` standard library

---

## 3. Quickstart & Installation (Windows)

### 3.1 Clone Repository and Enter Workspace
```powershell
git clone https://github.com/ChaniOops/Expense-Tracker.git
cd Expense-Tracker
```

### 3.2 Create and Activate Virtual Environment
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```
*(If running into PowerShell execution policy restrictions, execute: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`)*

### 3.3 Install Dependencies
```powershell
pip install -r requirements.txt
```

### 3.4 Configure Environment Variables
Copy `.env.example` to `.env`:
```powershell
Copy-Item .env.example .env
```
Ensure `.env` contains:
```env
FLASK_APP=run.py
FLASK_DEBUG=1
SECRET_KEY=change-this-to-a-secure-random-secret-key
DATABASE_URL=sqlite:///expense_tracker.db
```

---

## 4. Database Initialization & Seeding

Initialize the SQLite database schema and seed the 15 default expense and income categories:

```powershell
python run.py init-db
```
*Or using the Flask CLI:*
```powershell
flask --app run.py init-db
```

The database will be initialized in `instance/expense_tracker.db` with all 4 tables and idempotent category seeding.

---

## 5. Running the Application

Start the local Flask development server:
```powershell
python run.py
```
Open your browser and navigate to:
```
http://127.0.0.1:5000
```

---

## 6. Default Routes and Navigation

| Route | Method | Access | Purpose |
|---|---|---|---|
| `/` | `GET` | Authenticated | Main Dashboard (KPI cards, charts, budget overview, recent ledger) |
| `/transactions` | `GET` | Authenticated | Transaction list with search, category/type/date filters, and sorting |
| `/transactions/new` | `GET, POST` | Authenticated | Create a new income or expense transaction |
| `/transactions/<id>/edit` | `GET, POST` | Authenticated | Edit an existing transaction owned by current user |
| `/transactions/<id>/delete` | `POST` | Authenticated | Delete a transaction (CSRF-protected POST only) |
| `/budgets` | `GET` | Authenticated | Monthly budget list, period selection, and threshold status |
| `/budgets/new` | `GET, POST` | Authenticated | Create a category spending limit for a specific month/year |
| `/budgets/<id>/edit` | `GET, POST` | Authenticated | Edit a category budget limit or period |
| `/budgets/<id>/delete` | `POST` | Authenticated | Delete a budget (CSRF-protected POST only) |
| `/reports` | `GET` | Authenticated | Monthly financial report, category breakdown, largest expense |
| `/reports/export` | `GET` | Authenticated | Export selected month's transactions to RFC 4180 CSV |
| `/login` | `GET, POST` | Public | User sign-in with show/hide password toggle |
| `/register` | `GET, POST` | Public | User registration with confirmation and password toggles |
| `/logout` | `POST` | Authenticated | CSRF-protected user logout |

---

## 7. Database Architecture: Four Core Models

In accordance with [`DATABASE.md`](file:///d:/Expense-Tracker/DATABASE.md), the application uses strictly four tables:

1. **`User` (`users` table):**
   - Stores user credentials and profile information.
   - Enforces unique email addresses (normalized to lowercase).
   - Manages password hashes via `werkzeug.security`.
   - Has cascading relationships to `Transaction` and `Budget` (`cascade="all, delete-orphan"`).
2. **`Category` (`categories` table):**
   - Shared lookup table storing system categories.
   - Enforces unique `(name, type)` and type check `IN ('income', 'expense')`.
   - Pre-seeded with 9 expense categories (`Food`, `Transport`, `Shopping`, `Entertainment`, `Education`, `Bills`, `Healthcare`, `Travel`, `Other`) and 6 income categories (`Salary`, `Freelance`, `Scholarship`, `Allowance`, `Investment`, `Other`).
3. **`Transaction` (`transactions` table):**
   - Records individual user cash flows with positive `Numeric(10, 2)` amounts.
   - Associated with `user_id` (CASCADE) and `category_id` (RESTRICT).
   - Transaction direction (`income` vs `expense`) is derived dynamically via `category.type`.
4. **`Budget` (`budgets` table):**
   - Represents category spending targets for a specific `(month, year)` period.
   - Enforces unique `(user_id, category_id, month, year)`.
   - Budgets are strictly restricted to categories where `type == 'expense'`.
   - Actual expenditure is calculated dynamically from transactions to prevent stale data.

---

## 8. Currency & Formatting Convention

- **Currency Unit:** Indian Rupee (`₹`, INR).
- **Number Grouping:** Indian numbering system formatted as `₹1,25,000.00` via the custom `format_inr` filter.
- **Database Storage:** All amounts are stored as standard `NUMERIC(10, 2)` / Python `Decimal` values. No currency symbols are stored in the database or exported in raw CSV figures.

---

## 9. Running the Automated Test Suite

Execute the entire automated test suite (89 passing tests):

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

### Test Suite Structure
- `tests/test_foundation.py`: Schema constraints, foreign key enforcement, cascade deletions, category seeding.
- `tests/test_auth.py`: Registration validation, password hashing, login/logout, route protection, CSRF security.
- `tests/test_currency_and_password.py`: INR formatting rules and password toggle UI elements.
- `tests/test_transactions.py`: Transaction CRUD, derived types, multi-parameter filters, allowlisted sorting, IDOR isolation.
- `tests/test_dashboard.py`: Current-month KPI calculations, boundary exclusions, recent records, Chart.js dataset formats.
- `tests/test_budgets.py`: Budget CRUD, dynamic spending derivation, 80%/100% threshold visual alerts, unique constraints.
- `tests/test_reports.py`: Monthly report summaries, category breakdowns, largest expense tie-breakers, CSV export, formula injection sanitization.
- `tests/test_e2e_journey.py`: Full end-to-end user lifecycle integration test (10 steps).

---

## 10. Known Limitations & Project Boundaries

- **Single Currency:** The application exclusively operates in Indian Rupees (`₹`); currency conversion and multi-currency exchange rates are out of scope.
- **Manual Data Entry:** In accordance with the academic capstone specification, transactions are entered manually; third-party banking APIs and automated SMS scrapers are intentionally omitted.
- **Synchronous Architecture:** SQLite and Flask handle all requests synchronously; asynchronous job workers (Celery/Redis) and containerization are excluded per project requirements.

---

## 11. Specifications & Source of Truth Documents
- **[PRD.md](file:///d:/Expense-Tracker/PRD.md):** Product Requirements Document.
- **[DESIGN.md](file:///d:/Expense-Tracker/DESIGN.md):** UI/UX Design System and layout specifications.
- **[ARCHITECTURE.md](file:///d:/Expense-Tracker/ARCHITECTURE.md):** System architecture, application factory, and data flows.
- **[DATABASE.md](file:///d:/Expense-Tracker/DATABASE.md):** Relational schema definitions, constraints, indexes, and ER diagram.
- **[AGENTS.md](file:///d:/Expense-Tracker/AGENTS.md):** Development guidelines and rules of engagement for AI coding agents.