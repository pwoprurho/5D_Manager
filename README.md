# 🏗️ Vinicius Project Command: 5D Infrastructure Management

![Version](https://img.shields.io/badge/version-1.2.0-red)
![Frontend](https://img.shields.io/badge/UI-Vanilla%20JS-blue)
![Backend](https://img.shields.io/badge/Backend-FastAPI-green)

**Vinicius Project Command** is a high-fidelity orchestration platform designed for streamlined infrastructure oversight. It focuses on the core pillars of project management: time, cost, and documentation, providing a tactical interface for multi-tier oversight.

---

## 🛰️ System Architecture

A simplified, robust pipeline for infrastructure telemetry:
- **Collection**: Direct ingestion of project updates and financial records.
- **Processing**: Automated calculation of project health metrics (CPI/EAC).
- **Visualization**: Real-time Gantt timelines and tactical dashboards.
- **Reporting**: Automated PDF generation for weekly project audits.

---

## 🚀 Key Modules

### 1. **Tactical Gantt Orchestrator**
High-fidelity chronological tracking.
- **Interactive Timelines**: Built with Frappe Gantt for smooth schedule visualization.
- **Daily Target Logic**: Automatic status markers for "On Track", "Behind", and "Overdue" tasks.
- **Task Telemetry**: Direct clickable access to historical logs for every work package.

### 2. **Financial Cost Engine**
Real-time economic oversight for complex projects.
- **Performance Indices**: Automated tracking of CPI (Cost Performance Index).
- **Forecast Analytics**: EAC (Estimate at Completion) calculations based on current burn rates.
- **Budget Tracking**: Granular material cost assignment and inventory monitoring.

### 3. **Infrastructure Registry**
Unified database for site personnel and resources.
- **Personnel Governance**: Role-based access control for Directors, Managers, and Engineers.
- **Resource Store**: Managed inventory catalog with localized cost tracking.
- **Document Uploader**: Secure links for blueprints, CAD imagery, and PDF documentation.

---

## 🛠️ Technical Stack

- **Backend**: Python 3.10+, FastAPI (Asynchronous Performance).
- **Database**: Supabase (PostgreSQL with Real-time synchronization).
- **UI Architecture**: Vanilla JS (Dynamic Components), Jinja2 Templates, CSS Glassmorphism.
- **Deployment**: Production-ready for Render/Gunicorn.

---

## 🚦 Operational Protocol (Local Deployment)

To initialize the **Vinicius Command Terminal** on a local node, follow these sequential protocols:

1. **Environment Preparation**
   ```bash
   python -m venv venv
   .\venv\Scripts\activate
   ```

2. **Dependency Ingestion**
   ```bash
   pip install -r requirements.txt
   ```

3. **Database Provisioning (Optional)**
   ```bash
   python seed_users.py
   ```

4. **Terminal Activation**
   ```powershell
   .\venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --port 8000
   ```

5. **Access Node**: [http://localhost:8000](http://localhost:8000)

---

## 🛡️ Security Hardware
- **Auth Hardening**: Supabase GoTrue integration with role-based dependencies.
- **Rate Limiting**: Integrated SlowAPI tracking for authentication protection.
- **CSRF & HSTS**: Industrial-grade header protection for tactical routes.
