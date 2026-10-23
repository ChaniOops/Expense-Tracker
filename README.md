# Expense Tracker

A lightweight, practical personal finance tracking web application built with Python, Flask, SQLite, and Bootstrap 5.

---

## 1. Prerequisites
- **Python 3.10+** (tested on Python 3.12)
- **Git**
- **Windows / macOS / Linux** (PowerShell or Bash)

---

## 2. Quickstart & Installation (Windows)

### 2.1 Clone Repository and Enter Workspace
```powershell
git clone https://github.com/ChaniOops/Expense-Tracker.git
cd Expense-Tracker
```

### 2.2 Create and Activate a Virtual Environment
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```
*(If running into execution policy restrictions, run: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`)*

### 2.3 Install Required Dependencies
```powershell
pip install -r requirements.txt
```

### 2.4 Configure Environment Variables
Copy `.env.example` to `.env`:
```powershell
Copy-Item .env.example .env
```
*(Customize `SECRET_KEY` in `.env` as appropriate)*

---

## 3. Database Initialization

Initialize the SQLite database and seed the shared default categories (`Food`, `Transport`, `Salary`, etc.):

```powershell
python run.py init-db
```
*Alternatively, you can run:*
```powershell
flask --app run.py init-db
```
The database will be created in `instance/expense_tracker.db` with all 4 tables and 15 default categories seeded idempotently.

---

## 4. Running the Application

Start the local Flask development server:
```powershell
python run.py
```
Open your web browser and navigate to:
```
http://127.0.0.1:5000
```

---

## 5. Running the Automated Test Suite

Execute the complete test suite using Python's built-in `unittest` runner:
```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

---

## 6. Architecture & Core Documentation
- **[PRD.md](file:///d:/Expense-Tracker/PRD.md):** Product Requirements Document.
- **[DESIGN.md](file:///d:/Expense-Tracker/DESIGN.md):** UI/UX Design System and layout specifications.
- **[ARCHITECTURE.md](file:///d:/Expense-Tracker/ARCHITECTURE.md):** System architecture, application factory, and data flows.
- **[DATABASE.md](file:///d:/Expense-Tracker/DATABASE.md):** Relational schema definitions, constraints, indexes, and ER diagram.
- **[AGENTS.md](file:///d:/Expense-Tracker/AGENTS.md):** Development guidelines and rules of engagement for AI coding agents.