# Vinicius Command System: Access Control & Workflow Guide

The Vinicius 5D Project Management Application implements a Strict Role-Based Access Control (RBAC) model. All interactions, such as linking 3D BIM elements, originating financial requests, and pushing updates, are segmented across five explicit tiers: **Admin**, **President**, **Director**, **Manager**, and **Staff**.

Below is the definitive workflow outlining how each distinct user tier is expected to interact with the application’s modules.

---

## 1. **ADMIN (`admin`)**
*The absolute system authority. Controls global infrastructure, access provisioning, and system corrections.*

### **Workflow Expectations:**
- **System Provisioning:** Admins are the only personnel authorized to access the Admin panel to create initial user accounts, handle password resets, and manually assign access roles. 
- **Universal Override:** Expected to step in and fix or override stuck workflows. This includes terminating orphaned Project Updates, forcing updates to the Kanban timeline if there are blocking discrepancies, or overriding material requests.
- **Configuration & Maintenance:** Responsible for backend operational integrity, ensuring that orphaned 3D IFC models in Supabase storage are purged or correctly re-linked if managers make structural tracking mistakes.

---

## 2. **PRESIDENT (`president`)**
*The highest executive tier. Structurally holds complete Administrative privileges (equivalent to Admin mapped identically on the backend).*

### **Workflow Expectations:**
- **Full Backend Authority:** Can structurally invoke any endpoints across all modules, financials, and 3D orchestrations without restriction. 
- **Hidden Curated Interface:** To prevent accidental structural damage or unwanted overriding, their user interface deliberately hides manual override interaction elements (like forceful `delete` buttons on the Kanban UI or 3D viewer) that standard Admins utilize to prune orphaned data.
- **Personnel Management:** Fully capable of interacting with the Admin users panel to provision or manage personnel.

---

## 3. **DIRECTOR (`director`)**
*The executive oversight tier. Focuses on high-level orchestration, financial approval, and 3D discrepancy spotting without executing day-to-day site operations.*

### **Workflow Expectations:**
- **Executive Orchestration (3D Viewer):** Directors heavily utilize the **Project Updates Visualizer**. They are expected to cross-reference the 3D Web-IFC render against the reported Kanban metrics to guarantee that the theoretical architecture aligns perfectly with real-world progression.
- **Financial Gateway (Material Requisitions):** Directors function as the financial checkpoint. While they do not *create* supply requests, they are solely responsible (alongside Admins) for reviewing, approving, or denying Material Requisitions mapped to specific project updates, ensuring budgets are maintained in NGN (₦).
- **Site Telemetry Review:** Expected to audit the Dashboard and Site Updates to detect bottlenecks across the entire project portfolio.

---

## 4. **MANAGER (`manager`)**
*The operational architect and site lead. The Manager drives the momentum of the project, coordinates the 3D model, and structures the workflow for the Staff.*

### **Workflow Expectations:**
- **BIM Coordination:** Expected to upload raw `.ifc` Architectural/Structural designs into the system and map a specific `design_id` to its respective Project.
- **Updating Architecture:** Managers select specific 3D model elements (using their geometry GUIDs) via the 3D Viewer and explicitly bind them to new **Project Updates**. They assign budgets (₦), target dates, and priorities to these individual nodes.
- **Originating Requisitions:** If the Staff need concrete, rebar, or materials to complete a Project Update, the Manager is the *only* tier designated to create the **Material Requisition** (which is then pushed to the Director for approval).
- **Kanban Sequencing:** Managers dynamically drag and drop Project Updates on the Kanban board to reorganize sprint goals when priorities shift or external blockers arise.

---

## 5. **STAFF (`staff`)**
*The field execution tier. Focuses heavily on the Kanban execution, on-site reality, and direct telemetry reporting.*

### **Workflow Expectations:**
- **Task Execution:** Staff access the **Kanban Board** to visualize current tasks. Their primary workflow consists of reviewing Project Updates that have been set to `not_started`, and advancing them to `in_progress` when physical work initiates.
- **Telemetry Uploads:** Staff are expected to utilize the **Site Updates** panel to submit progress photos, text telemetry, and exact completion percentages directly from the field. 
- **Flagging Blockers:** When a physical blockade halts progress (e.g., weather constraints, missing materials), a Staff member is expected to slide the relevant Project Update into the `blocked` column queue to alert the Manager and Director immediately.
- **Restricted Access:** Staff *cannot* manage personnel, upload architecture models, alter overall 5D budgets, or approve material requisitions.
