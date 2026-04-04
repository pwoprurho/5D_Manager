# Technical Repository Scoping: Vinicius Project Command (5D Infrastructure Management)

## 1. Project Overview
**Vinicius Project Command** is a high-performance 5D infrastructure management platform. It integrates traditional project management workflows (Work Packages, Gantt, Kanban) with advanced 3D BIM (Building Information Modeling) visualization and AI-assisted architectural tools.

### Key Metrics
- **Backend Framework**: FastAPI (Python 3.10+)
- **Database/Auth**: Supabase (PostgreSQL + Supabase Auth)
- **Frontend Engine**: Vanilla JS, Three.js (3D Viewer)
- **Design Aesthetic**: Glassmorphism (Vanilla CSS)

---

## 2. System Architecture

### Backend (`/backend/app`)
- **`main.py`**: The heart of the API, containing RESTful endpoints for projects, work packages, site updates, and store management.
- **`models.py`**: Pydantic data models for Users, Projects, Work Packages, Materials, and Assignments.
- **`auth.py`**: Authentication logic leveraging Supabase token verification and role-based access control (RBAC).
- **`database.py`**: Supabase client initialization.
- **`services/`**:
  - `cost_engine.py`: Handles PM calculations (CPI, EV, EAC, Burn Rate).
  - `ifc_parser.py`: Extracts building elements from Industry Foundation Classes (IFC) BIM models.
  - `subjects/architecture.py`: Contains prompts for generating 3D symbolic architecture maps via Gemini.

### Frontend (`/templates`, `/static`)
- **Templates**: Server-side rendered (Jinja2) components including the multi-functional dashboard, work package manager, and AEC-grade model viewer.
- **Logic (`static/script.js`)**: A large-scale client-side script handling Three.js rendering, AJAX communications, and dynamic UI updates.
- **Design (`static/style.css`)**: Implements a sleek dark mode with glassmorphism and modern typography (Outfit).

---

## 3. Database Schema (`supabase_schema.sql`)
The repository uses a PostgreSQL schema on Supabase with the following core entities:
- **`user`**: Stores profiles linked to Supabase Auth UUIDs.
- **`design`**: Houses global BIM/GLTF models.
- **`project`**: Specific instances of construction/infrastructure assignments.
- **`workpackage`**: Tasks tied to specific 3D model elements (BIM GUIDs).
- **`siteupdate`**: Progress tracking records with photo and GPS capabilities.
- **`material` & `material_request`**: Inventory management and logistics system.

---

## 4. Workflows

### 5D Tracking Loop
1.  **Design Upload**: Admin uploads an IFC model.
2.  **Project Creation**: A project is initialized using the design.
3.  **Work Packaging**: Managers assign tasks to specific BIM elements.
4.  **Field Reporting**: Staff submits updates with photos and cost incurred.
5.  **Monitoring**: Directors view real-time CPI/EAC metrics via the dashboard.

### Deployment
- **Local Development**: Using `uvicorn` and `.env` for secrets.
- **Production**: Configured for Render via `render.yaml` and `Procfile` using Gunicorn + Uvicorn workers.

---

## 5. Known Gaps & Discrepancies
- **Missing modules**: `report_generator.py` is referenced but missing from current repo state.
- **Legacy references**: Mentions of an "election" in error handlers and a separate `simulation` folder suggesting a previous or dual use-case for the codebase.
- **Repository Naming**: The folder is named `outbound-caller-python`, but internal code points to `Vinicius Command`.
