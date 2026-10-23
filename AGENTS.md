# AGENTS.md — Development Guidelines for AI Coding Agents
## Personal Finance & Expense Tracker Web Application

---

## 1. Authority & Sources of Truth
All AI coding agents working on this repository must strictly adhere to the project specifications in the following order of precedence:
1. **[PRD.md](file:///d:/Expense-Tracker/PRD.md):** Defines feature requirements, business rules, and project boundaries.
2. **[DATABASE.md](file:///d:/Expense-Tracker/DATABASE.md):** The authoritative definition of tables, constraints, types, keys, and indexes.
3. **[ARCHITECTURE.md](file:///d:/Expense-Tracker/ARCHITECTURE.md):** Defines system structure, application factory, blueprints, and data flows.
4. **[DESIGN.md](file:///d:/Expense-Tracker/DESIGN.md):** Defines UI/UX patterns, Bootstrap styling, responsive behavior, and accessibility.

> [!IMPORTANT]
> If any requirements conflict across documents, **do not guess or silently invent a workaround**. Flag the contradiction explicitly and seek clarification from the user before proceeding.

---

## 2. Strict Technology Boundaries
Only the approved technology stack is permitted:
- **Core:** Python 3.10+, Flask, SQLite 3
- **Flask Extensions:** Flask-SQLAlchemy, Flask-Login, Flask-WTF (CSRF), python-dotenv
- **Frontend / Templating:** Jinja2, Bootstrap 5.3 (CDN), Vanilla JavaScript (ES6+), Chart.js (CDN)
- **Testing:** `unittest` (Python standard library)

### Explicit Prohibitions
- **NO** frontend frameworks (React, Vue, Angular, Svelte, Tailwind CSS).
- **NO** dedicated REST APIs, FastAPI, or GraphQL endpoints.
- **NO** asynchronous task workers (Celery, Redis, RQ).
- **NO** containerization tools (Docker, Podman, Kubernetes).
- **NO** third-party financial aggregators, AI features, or external payment gateways.
- **NO** unapproved pip packages.

---

## 3. Code Architecture & Quality Standards
- **Inspection First:** Always inspect existing files and directory structure before proposing or modifying code.
- **Modularity:** Follow the Application Factory (`create_app`) and Blueprint layout (`auth`, `main`, `transactions`, `budgets`, `reports`).
- **Readability Over Cleverness:** Write idiomatic, beginner-friendly Python with clear variable names and explicit function responsibilities. Avoid generic abstractions or deep inheritance hierarchies.
- **Reuse Before Creating:** Utilize existing models, WTForms, Jinja base templates, and helper utilities.
- **No Unnecessary Files:** Do not create scratch files, demo scripts, or unrequested modules inside the application workspace.
- **Preserve Existing Functionality:** Do not refactor or rewrite working code unless directly required by the active task.

---

## 4. Database Schema & Data Integrity Rules
- **Exactly 4 Application Tables:** `users`, `categories`, `transactions`, `budgets`. Never add extra tables without authorization.
- **Shared Lookup Categories:** Categories are shared reference data (`categories` table has no `user_id`). Users select from pre-seeded categories.
- **Derived Transaction Types:** Transactions **must not** store a `type` column. Type (`income` vs. `expense`) is strictly derived via `transaction.category.type`.
- **Decimal Precision:** All monetary amounts must use `db.Numeric(10, 2, asdecimal=True)` and Python `decimal.Decimal`. Never use floating-point types for currency.
- **Positive Values:** Form validation and database check constraints must enforce `amount > 0.00`.
- **Foreign Key Enforcement:** Ensure SQLite foreign keys are active via the engine connection event: `PRAGMA foreign_keys=ON`.
- **Idempotent Seeding:** Seeding functions must verify existing records before inserting default categories.
- **Transaction Rollbacks:** Always wrap database operations in `try...except` blocks and issue `db.session.rollback()` upon errors.

---

## 5. Authentication & Strict Multi-Tenant Isolation
- **Authentication Engine:** Use Flask-Login with secure session cookies.
- **Password Security:** Use `werkzeug.security.generate_password_hash` and `check_password_hash`. Never store or log plaintext passwords.
- **Route Guarding:** Protect all private endpoints with `@login_required`.
- **Scoping by Authenticated User:** Every query retrieving or mutating transactions or budgets must be scoped by `current_user.id`:
  ```python
  # CORRECT: Scoped query
  tx = Transaction.query.filter_by(id=tx_id, user_id=current_user.id).first_or_404()

  # PROHIBITED: Unscoped query susceptible to IDOR
  tx = Transaction.query.get_or_404(tx_id)
  ```
- **Ownership Verification:** Before executing an edit or delete, verify that `record.user_id == current_user.id`. Return HTTP 404 or 403 on violations.

---

## 6. Security, Validation & Input Sanitization
- **Server-Side Validation:** Always validate inputs using Flask-WTF forms on the server, regardless of client-side HTML5 attributes.
- **CSRF Tokens:** All mutating forms (POST requests) must include `{{ form.csrf_token }}`. Deletion modals must submit via POST with CSRF tokens.
- **Secret Management:** Never hardcode secrets in source code. Load `SECRET_KEY` and configuration via `python-dotenv` from `.env`. Ensure `.env` is listed in `.gitignore`.
- **Safe CSV Generation:** In CSV exports, prefix any cell value beginning with `=`, `+`, `-`, or `@` with a single quote (`'`) to neutralize spreadsheet formula injection.
- **No Raw SQL:** Use SQLAlchemy ORM queries and parameterized expressions to prevent SQL injection.

---

## 7. Frontend, UX & Charting Guidelines
- **Bootstrap 5 & Jinja2:** Use native Bootstrap components (`container`, `row`, `col`, `card`, `table`, `modal`, `alert`). Keep custom CSS in `static/css/styles.css` minimal.
- **Chart.js via Safe Attributes:** Pass chart data safely from Flask to HTML using JSON data attributes (`data-labels='{{ labels | tojson }}'`) rather than inline JavaScript string concatenation.
- **Financial Semantics:**
  - Income / Positive balance: Green (`text-success`, `+` prefix, `Income` badge).
  - Expense / Negative balance: Red (`text-danger`, `-` prefix, `Expense` badge).
  - Budgets: Green ($< 80\%$), Amber ($80\% - 100\%$), Red with warning ($> 100\%$).
- **State Handling:** Provide clear UI feedback for loading, form validation errors (`is-invalid`), flash alerts, and empty states when tables or charts have zero records.
- **Destructive Confirmation:** Deleting any transaction or budget must prompt for user confirmation via a modal or confirmation dialog before sending the POST request.

---

## 8. Development & Implementation Workflow
For every assigned task or prompt, follow this 7-step sequence:
1. **Inspect:** Read relevant project documents and inspect the target codebase.
2. **Identify:** Pinpoint the exact files, routes, models, or templates to modify.
3. **Minimal Complete Change:** Make the smallest complete modification that satisfies the prompt without introducing unrequested features.
4. **Schema Compliance:** Confirm all data mutations strictly adhere to `DATABASE.md`.
5. **Verify & Test:** Run automated unit tests (`python -m unittest discover tests`) or manual verification commands.
6. **Error Correction:** Fix any syntax, lint, or runtime regressions immediately.
7. **Report Truthfully:** Summarize files updated, functionality added, and actual test results. Never claim a test passed without running it.

---

## 9. Scope Control & Discipline
- **Milestone Adherence:** Only build what the current prompt requests. Do not prematurely build future features.
- **No Scope Creep:** Never introduce speculative helper utilities, experimental libraries, or "nice-to-have" features not in the specifications.
- **Document Integrity:** Never edit requirement documents to cover up implementation shortcuts or bugs.
- **Clarification Over Invention:** If an edge case is ambiguous, ask the user before writing code.

---

## 10. Definition of Done (DoD)
A task or milestone is officially complete only when:
- [ ] All requirements specified in the prompt are implemented.
- [ ] Input validation, CSRF protection, and user authorization checks are in place.
- [ ] No regression has occurred in existing functionality.
- [ ] Automated tests or manual verification scripts execute successfully and pass.
- [ ] Any known constraints or assumptions are clearly documented for the user.
