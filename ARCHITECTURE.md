# System Architecture Document
## Personal Finance & Expense Tracker Web Application

---

## 1. Document Overview & Objective
- **Document Version:** 1.0.0
- **Document Status:** Approved / Baseline
- **Target Audience:** Developers, Software Evaluators, and Academic Assessors.
- **System Scope:** Multi-user personal finance tracker built as a server-side rendered (SSR) web application using Python and Flask.

---

## 2. Technology Stack & Constraints

| Layer / Concern | Technology | Justification & Rationale |
|---|---|---|
| **Language** | Python 3.10+ | Standard, readable, and widely supported in academic environments. |
| **Web Framework** | Flask | Lightweight, unopinionated, flexible WSGI microframework. |
| **ORM / Data Access** | Flask-SQLAlchemy (SQLAlchemy 2.x) | Object-relational mapping, connection management, query abstraction. |
| **Authentication & Session** | Flask-Login | Standard, battle-tested session management and route protection. |
| **Form Handling & CSRF** | Flask-WTF / WTForms | Robust form binding, field validation, and automatic CSRF tokens. |
| **Database Engine** | SQLite 3 (`instance/expense_tracker.db`) | Zero-configuration, zero-dependency, self-contained ACID relational database. |
| **Templating Engine** | Jinja2 | Integrated Flask templating with template inheritance and context security. |
| **UI Framework** | Bootstrap 5.3 (CDN) | Responsive grid, accessible controls, and clean modern aesthetics. |
| **Client Scripting** | Vanilla JavaScript (ES6+) | Native browser scripting; zero build steps or npm node_modules overhead. |
| **Data Visualization** | Chart.js 4.x (CDN) | Lightweight, accessible, canvas-based chart rendering library. |
| **Environment Configuration** | python-dotenv | Decoupled secrets and environment configuration via `.env`. |
| **Testing Framework** | `unittest` (Python standard library) | Built-in test runner with zero extra testing dependencies required. |

### Architectural Inclusions vs. Exclusions
- **Strictly Included:** Server-Side Rendered (SSR) Multi-Page Architecture (MPA) with Jinja2, server-side session cookies, and declarative SQL transactions.
- **Strictly Excluded:** Single Page Applications (React, Vue, Angular), dedicated REST APIs, FastAPI, GraphQL, Docker/container runtimes, Celery/task queues, external cloud databases, microservices, and third-party fintech or banking integrations.

---

## 3. Directory & Module Structure

The project employs the standard modular Flask Blueprint architecture:

```text
expense-tracker/
├── app/
│   ├── __init__.py              # Application factory (create_app), logging, and extensions
│   ├── extensions.py            # Centralized Flask extension instances (db, login_manager, csrf)
│   ├── models.py                # Declarative SQLAlchemy ORM models (User, Category, Transaction, Budget)
│   ├── auth/                    # Authentication Blueprint
│   │   ├── __init__.py          # Blueprint definition for 'auth'
│   │   ├── forms.py             # Registration and Login WTForms
│   │   └── routes.py            # Login, register, logout route controllers
│   ├── main/                    # Core / Dashboard Blueprint
│   │   ├── __init__.py          # Blueprint definition for 'main'
│   │   └── routes.py            # Dashboard index, recent activity, chart data providers
│   ├── transactions/            # Transaction Management Blueprint
│   │   ├── __init__.py          # Blueprint definition for 'transactions'
│   │   ├── forms.py             # Transaction WTForm (create/edit)
│   │   └── routes.py            # Transaction CRUD, search, filter, and sort controllers
│   ├── budgets/                 # Budget Management Blueprint
│   │   ├── __init__.py          # Blueprint definition for 'budgets'
│   │   ├── forms.py             # Budget WTForm (create/edit)
│   │   └── routes.py            # Budget CRUD and spending calculation controllers
│   ├── reports/                 # Reporting & Export Blueprint
│   │   ├── __init__.py          # Blueprint definition for 'reports'
│   │   └── routes.py            # Monthly report generation, category metrics, and CSV streaming
│   ├── templates/               # Jinja2 HTML templates
│   │   ├── base.html            # Core layout shell, navbar, flash messages, CDN scripts
│   │   ├── auth/                # login.html, register.html
│   │   ├── dashboard/           # index.html
│   │   ├── transactions/        # index.html, form.html
│   │   ├── budgets/             # index.html, form.html
│   │   ├── reports/             # index.html
│   │   ├── categories/          # index.html (category management)
│   │   └── errors/              # 400.html, 403.html, 404.html, 500.html
│   └── static/                  # Static assets
│       ├── css/
│       │   └── styles.css       # Clean, modest custom styles (<150 lines)
│       └── js/
│           └── main.js          # Chart.js initialization, delete modal trigger (<200 lines)
├── instance/                    # SQLite database file storage (expense_tracker.db)
├── tests/                       # Unit and integration test suite
│   ├── __init__.py
│   ├── test_auth.py
│   ├── test_transactions.py
│   ├── test_budgets.py
│   ├── test_reports.py
│   └── test_dashboard.py
├── .env.example                 # Template for required environment variables
├── .gitignore                   # Excludes venv/, instance/*.db, .env, __pycache__/
├── requirements.txt             # Python dependency manifest
├── run.py                       # Application execution entry point
├── README.md                    # Project documentation and quickstart instructions
├── PRD.md                       # Product Requirements Document
├── DESIGN.md                    # UI/UX Design Specification
└── ARCHITECTURE.md              # System Architecture Document (this file)
```

---

## 4. Flask Application Design & Lifecycle

### 4.1 Application Factory Pattern (`create_app`)
The application is constructed via the application factory function located in `app/__init__.py`. This allows clean instantiation for both production execution and isolated test configurations:

```python
# Conceptual factory pattern in app/__init__.py
def create_app(config_class=None):
    app = Flask(__name__, instance_relative_config=True)
    # 1. Load configuration from environment variables via python-dotenv
    # 2. Initialize extensions (db, login_manager, csrf) with app
    # 3. Register Blueprints (auth, main, transactions, budgets, reports)
    # 4. Register custom Jinja filters (currency formatting, date formatting)
    # 5. Register global error handlers (403, 404, 500)
    # 6. Enable SQLite foreign key support on connect
    return app
```

### 4.2 Centralized Extension Registry (`app/extensions.py`)
To prevent circular import dependencies between models, routes, and the application factory, extensions are instantiated unbound in `app/extensions.py`:
- `db = SQLAlchemy()`
- `login_manager = LoginManager()`
- `csrf = CSRFProtect()`

Extensions are bound to the Flask instance inside `create_app()` via `extension.init_app(app)`.

### 4.3 SQLite Foreign Key Enforcement
By default, SQLite does not enforce foreign key referential integrity unless explicitly commanded per connection. The application factory configures an event listener on the SQLAlchemy engine:
```python
from sqlalchemy import event
from sqlalchemy.engine import Engine

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
```

### 4.4 Default Category Seeding Strategy
Categories function as the classification backbone for transactions and budgets:
- When a new user registers, the authentication service seeds an initial set of default categories (`INCOME` and `EXPENSE`) associated with the user's `user_id`.
- Default Expense Categories: `Food & Dining`, `Rent & Housing`, `Transportation`, `Utilities`, `Entertainment`, `Education`, `Healthcare`, `Miscellaneous`.
- Default Income Categories: `Salary`, `Freelance / Side Hustle`, `Stipend / Allowance`, `Investments`, `Gifts`, `Other Income`.
- Users can create custom categories via `/categories`. A category cannot be deleted if associated transactions exist.

---

## 5. Database Schema & Data Models

The system architecture utilizes **four primary relational tables**:

```
+--------------------+            +------------------------+
|       users        |            |       categories       |
+--------------------+            +------------------------+
| id (PK)            | 1        * | id (PK)                |
| username (Unique)  |------------| user_id (FK -> users)  |
| email (Unique)     |            | name                   |
| password_hash      |            | category_type (Enum)   |
| created_at         |            | created_at             |
+--------------------+            +------------------------+
          | 1                                 | 1
          |                                   |
          | *                                 | *
+-------------------------+       +------------------------+
|      transactions       |       |        budgets         |
+-------------------------+       +------------------------+
| id (PK)                 |       | id (PK)                |
| user_id (FK -> users)   |       | user_id (FK -> users)  |
| category_id (FK -> cat) |       | category_id (FK -> cat)|
| title                   |       | month (1-12)           |
| amount (Numeric(10,2))  |       | year (e.g. 2026)       |
| payment_method          |       | amount (Numeric(10,2)) |
| description (Optional)  |       | created_at             |
| transaction_date (Date) |       +------------------------+
| created_at              |
+-------------------------+
```

### 5.1 Model Responsibilities

1. **`User` (`app.models.User`):**
   - Implements `UserMixin` for Flask-Login compatibility.
   - Stores user authentication credentials securely.
   - Houses password hashing and verification helper methods (`set_password`, `check_password`).
   - Declares one-to-many relationships to `Category`, `Transaction`, and `Budget`.

2. **`Category` (`app.models.Category`):**
   - Defines transaction classification and transaction type (`category_type`: `'INCOME'` or `'EXPENSE'`).
   - Scoped to `user_id` with a unique constraint on `(user_id, name, category_type)`.
   - Single source of truth for transaction direction (Income vs. Expense).

3. **`Transaction` (`app.models.Transaction`):**
   - Represents an atomic financial movement.
   - `amount` is stored as `Numeric(10, 2)` (Python `Decimal`) and strictly enforced to be positive ($> 0$).
   - Transaction type is derived at runtime via `transaction.category.category_type`. **No redundant `transaction_type` column is stored.**
   - References `user_id` and `category_id`.

4. **`Budget` (`app.models.Budget`):**
   - Establishes a monthly spending threshold for a specific **expense** category.
   - Constrained to `category_type == 'EXPENSE'`.
   - Unique constraint on `(user_id, category_id, month, year)`.
   - Computes `amount_spent`, `remaining_amount`, and `percentage_used` dynamically based on transactions in that month.

---

## 6. Authentication, Authorization & Tenant Isolation

### 6.1 Session Management
- **Flask-Login** manages user sessions via cryptographically signed session cookies (`app.secret_key`).
- User loader callback retrieves the active user by ID:
  ```python
  @login_manager.user_loader
  def load_user(user_id):
      return User.query.get(int(user_id))
  ```
- Unauthenticated requests to protected views redirect to `auth.login` with a clear flash notice.

### 6.2 Strict User Isolation Boundary
To prevent Insecure Direct Object References (IDOR), **no query or mutation may trust a raw client-submitted ID alone**:
- Any read query must include `.filter_by(user_id=current_user.id)`.
- Any record lookup by ID must verify ownership before execution:
  ```python
  record = Transaction.query.filter_by(id=transaction_id, user_id=current_user.id).first_or_404()
  ```
- If a user attempts to view, edit, or delete another user's record ID, the system returns a standard HTTP 404 (Resource Not Found) or 403 (Forbidden), revealing zero information about the existence of foreign records.

---

## 7. Routes and Blueprints Architecture

| Blueprint | Route / Pattern | HTTP Method | Route Function | Description / Purpose |
|---|---|---|---|---|
| **auth** | `/register` | GET, POST | `register()` | User registration & default category seeding |
| **auth** | `/login` | GET, POST | `login()` | User authentication & session establishment |
| **auth** | `/logout` | POST | `logout()` | Clears session cookie and redirects to `/login` |
| **main** | `/` | GET | `dashboard()` | Main dashboard with 4 KPI cards, 2 charts, recent transactions |
| **transactions** | `/transactions` | GET | `index()` | Searchable, filterable, sortable transaction ledger |
| **transactions** | `/transactions/new` | GET, POST | `create()` | Create a new income or expense transaction |
| **transactions** | `/transactions/<int:id>/edit` | GET, POST | `edit()` | Edit an existing transaction (ownership verified) |
| **transactions** | `/transactions/<int:id>/delete` | POST | `delete()` | Delete a transaction (CSRF & ownership verified) |
| **budgets** | `/budgets` | GET, POST | `index()` | View monthly budgets and submit new budget limits |
| **budgets** | `/budgets/<int:id>/edit` | GET, POST | `edit()` | Update an existing budget threshold |
| **budgets** | `/budgets/<int:id>/delete` | POST | `delete()` | Delete a budget (CSRF & ownership verified) |
| **reports** | `/reports` | GET | `index()` | Monthly financial statement, breakdown, largest expense |
| **reports** | `/reports/export` | GET | `export_csv()` | Stream CSV export for the selected month/year |
| **categories** | `/categories` | GET, POST | `index()` | Manage custom categories and view default categories |
| **categories** | `/categories/<int:id>/delete`| POST | `delete()` | Delete category (blocked if transactions exist) |

*Note: All mutating endpoints (POST) enforce CSRF token validation and redirect with PRG (Post/Redirect/Get) patterns to prevent duplicate submissions.*

---

## 8. Frontend Architecture & Data Visualization

### 8.1 Server-Side Rendering (SSR) & Jinja2
- Template inheritance via `templates/base.html`.
- Custom Jinja filters:
  - `| currency`: Formats `Decimal('1250.5')` to `$1,250.50`.
  - `| date_format`: Formats Python `datetime.date` objects consistently.
- Form inputs rendered with WTForms helper macros to standardize Bootstrap validation classes (`form-control`, `is-invalid`, `invalid-feedback`).

### 8.2 Safe Chart Data Serialization (Chart.js)
Chart data is generated in Flask route handlers and serialized directly into HTML data attributes or standard `<script type="application/json">` elements to completely eliminate Cross-Site Scripting (XSS) risks:

```html
<!-- Safe data injection pattern in templates/dashboard/index.html -->
<div id="chart-data"
     data-category-labels='{{ category_labels | tojson }}'
     data-category-amounts='{{ category_amounts | tojson }}'
     data-monthly-labels='{{ monthly_labels | tojson }}'
     data-monthly-income='{{ monthly_income | tojson }}'
     data-monthly-expense='{{ monthly_expense | tojson }}'>
</div>
```

`static/js/main.js` reads these structured JSON attributes, initializes the Chart.js instances, and gracefully falls back to empty-state placeholders when data arrays are empty.

---

## 9. Security, Validation & Reliability

1. **Password Hashing:**
   - Werkzeug's `generate_password_hash` using salted PBKDF2:SHA256 or Scrypt. Plaintext passwords never enter logs or database tables.
2. **CSRF Mitigation:**
   - Flask-WTF protects all mutating POST requests. Every form contains `{{ form.csrf_token }}`. Deletion modal forms include hidden CSRF tokens.
3. **Server-Side Validation:**
   - WTForms ensures amounts are positive decimals (`NumberRange(min=0.01)`), required strings are trimmed, emails conform to valid syntax, and dates are valid calendar dates.
4. **CSV Injection (Formula Injection) Mitigation:**
   - In `export_csv()`, any cell value beginning with `=`, `+`, `-`, or `@` is prefixed with a single quote (`'`) to neutralize automatic formula execution in spreadsheet applications (Microsoft Excel, LibreOffice).
5. **Database Transaction Safety:**
   - Route mutations wrap operations in try/except blocks with explicit `db.session.rollback()` on exceptions to keep the database session clean.
6. **Environment Variable Protection:**
   - `SECRET_KEY`, database paths, and debug flags are loaded from `.env`. The repository includes `.env.example`, while `.gitignore` strictly prevents `.env` and `instance/*.db` from being checked into version control.

---

## 10. Testing Architecture

Testing is implemented using Python’s standard library **`unittest`** module for zero-dependency execution across environments.

### Test Structure (`tests/`)
- **`test_auth.py`:**
  - Registration with valid/invalid data; duplicate username/email rejection.
  - Login/logout session persistence and password hash verification.
  - Automatic category seeding upon successful registration.
- **`test_transactions.py`:**
  - CRUD operations on income and expense transactions.
  - Positive amount validation enforcement.
  - Dynamic derivation of transaction type from category.
  - Filter logic (date range, category, search term, sort order).
- **`test_budgets.py`:**
  - Budget creation on expense categories; rejection on income categories.
  - Duplicate budget constraint for the same month/year/category.
  - Spent calculation, remaining amount, and percentage threshold flags (80%, 100%).
- **`test_reports.py`:**
  - Monthly report aggregation, net balance, and largest expense detection.
  - CSV export streaming, correct headers, and formula injection sanitization.
- **`test_dashboard.py`:**
  - Current-month KPI calculations and 6-month aggregate history.
- **Tenant Isolation Tests:**
  - Direct IDOR penetration tests verifying User A cannot read, edit, or delete User B's records.

---

## 11. Architectural Decision Records (ADRs)

### ADR 1: Server-Side Rendering (Flask + Jinja2) vs. SPA (React)
- **Decision:** Use Flask with Jinja2 and Bootstrap 5.
- **Rationale:** Aligns with project requirements, avoids complex client-side build pipelines, simplifies CSRF and authentication, and ensures immediate maintainability for a college capstone project.

### ADR 2: Derived Transaction Types via Category
- **Decision:** Do not store a `transaction_type` column on the `transactions` table.
- **Rationale:** Storing type in both `Category` and `Transaction` introduces data redundancy and anomaly risks (e.g., an "Expense" transaction assigned to a "Salary" income category). Deriving type ensures single-source-of-truth consistency.

### ADR 3: Dynamic Budgets with Composite Uniqueness
- **Decision:** Enforce composite uniqueness on `(user_id, category_id, month, year)`.
- **Rationale:** Prevents ambiguous or conflicting budgets for the same expense bucket in a single calendar month.

### ADR 4: SQLite with Explicit Foreign Key Pragma
- **Decision:** Use SQLite 3 with engine connection listener enabling `PRAGMA foreign_keys=ON`.
- **Rationale:** Lightweight zero-configuration local database that behaves like a production relational database, enforcing referential integrity without database server overhead.
