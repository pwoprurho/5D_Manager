# Vinicius Project Command: Technical Documentation

## 1. Executive Summary
Vinicius Project Command is a next-generation infrastructure management and monitoring system. Rooted in OpenProject-inspired workflows, it bridges the gap between architectural plans and physical construction monitoring through an advanced 5D project management suite.

---

## 2. System Architecture

### Frontend (User Interface)
- **Engine**: Vanilla JavaScript with native browser APIs.
- **Styling**: Vanilla CSS with a premium "Glassmorphism" theme.
- **Interactivity**: Dynamic dashboard with real-time stats and full work-package orchestration.

### Backend (Server)
- **Framework**: FastAPI (Python) for high-performance API routing.
- **ORM**: Pydantic Models synced directly with a Supabase SQL instance.
- **Authentication**: JWT-based secure sessions with role-based access control (RBAC).

### Tracking Capabilities
- **IFC Bundle Uploads**: Standardized tracking attachments on work packages tying physical nodes to project metrics.
- **Time Tracking**: Estimated and Spent hours logged via Work Package node verification.

---

## 3. Core Features

### 3D Architecture Lab
Allows users to describe system architectures (e.g., "AWS Cloud Setup") in natural language. The AI generates a symbolic 3D scene representing services, databases, and relationships.

### A.I. 3D Model Constructor
Transforms architectural drawings (images, PDFs) or text descriptions into 3D Wavefront OBJ models. These models represent building footprints and are automatically loaded into the project viewer.

### Work Packages (WP)
The project is divided into Work Packages linked to 3D BIM elements. WPs track:
- **Progress**: % completion updated by site staff.
- **Status**: Multi-tier approval (Not Started -> In Progress -> Completed -> Inspected -> Approved).
- **Financials**: Budget vs. Actual cost mapping (CPI/EAC calculation).

---

## 4. API Reference (Key Endpoints)

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/api/v1/plans/generate-3d` | POST | Generates 3D OBJ from image/text plans. |
| `/api/v1/architecture/interact` | POST | AI planning for 3D architecture visualization. |
| `/api/v1/architecture/generate` | POST | Final JSON blueprint generation for 3D viewer. |
| `/api/v1/projects/{id}/stats` | GET | Real-time CPI, EAC, and Burn Rate calculations. |

---

## 5. Security & Deployment

- **Environment**: Configured via `.env` with support for rotating Gemini API keys.
- **RBAC Roles**: 
  - `staff`: Submit updates and photos.
  - `manager`: Inspect work packages.
  - `director`: Project oversight and final approval.
  - `admin`: Full system access and user management.
- **Deployment**: uvicorn ASGI server with hot-reloading enabled for development.

---

## 6. Future Expansion: OCR & Multi-Format Integration
Planned support for `.pdf`, `.ifc`, and `.doc` formats with an AI-driven OCR pipeline to extract meta-data and architectural constraints before 3D transformation.
