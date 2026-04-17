-- ============================================================
-- 5D Project Management System - Supabase Schema (V12 - Orchestration Optimized)
-- Run this in your Supabase SQL Editor (Dashboard > SQL Editor)
-- ============================================================

-- DROP ALL (Full Reset)
DROP TABLE IF EXISTS projectassignment CASCADE;
DROP TABLE IF EXISTS material_request CASCADE;
DROP TABLE IF EXISTS project_inventory CASCADE;
DROP TABLE IF EXISTS material CASCADE;
DROP TABLE IF EXISTS siteupdate CASCADE;
DROP TABLE IF EXISTS workpackage CASCADE;
DROP TABLE IF EXISTS stage CASCADE;
DROP TABLE IF EXISTS project CASCADE;
DROP TABLE IF EXISTS design CASCADE;
DROP TABLE IF EXISTS "user" CASCADE;

DROP TYPE IF EXISTS user_role CASCADE;
DROP TYPE IF EXISTS status_enum CASCADE;
DROP TYPE IF EXISTS wp_type CASCADE;
DROP TYPE IF EXISTS wp_priority CASCADE;
DROP TYPE IF EXISTS material_request_status CASCADE;
DROP TYPE IF EXISTS logging_period CASCADE;

-- ============================================================
-- 1. ENUM TYPES
-- ============================================================
CREATE TYPE user_role AS ENUM ('engineer', 'manager', 'director', 'admin');
CREATE TYPE status_enum AS ENUM ('not_started', 'in_progress', 'completed', 'inspected', 'approved', 'blocked', 'critical');
CREATE TYPE wp_type AS ENUM ('task', 'bug', 'milestone', 'phase');
CREATE TYPE wp_priority AS ENUM ('low', 'normal', 'high', 'immediate');
CREATE TYPE material_request_status AS ENUM ('pending', 'approved', 'issued', 'rejected');
CREATE TYPE logging_period AS ENUM ('daily', 'weekly', 'bi_weekly', 'monthly', 'periodic');

-- ============================================================
-- 2. USERS
-- ============================================================
CREATE TABLE "user" (
    id UUID PRIMARY KEY,
    username VARCHAR(255) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    role user_role NOT NULL DEFAULT 'engineer',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================
-- 3. DESIGNS
-- ============================================================
CREATE TABLE design (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    model_url TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- ============================================================
-- 4. PROJECTS
-- ============================================================
CREATE TABLE project (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    design_id INTEGER REFERENCES design(id) ON DELETE SET NULL,
    bim_model_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- ============================================================
-- 5. PROJECT ASSIGNMENTS
-- ============================================================
CREATE TABLE projectassignment (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    assigned_role VARCHAR(50) NOT NULL DEFAULT 'member',
    assigned_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(project_id, user_id)
);

-- ============================================================
-- 6. STAGES (Phase Tracking)
-- ============================================================
CREATE TABLE stage (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    status status_enum NOT NULL DEFAULT 'not_started',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- ============================================================
-- 7. MATERIALS (Master Registry)
-- ============================================================
CREATE TABLE material (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    unit VARCHAR(50) NOT NULL,
    current_stock DOUBLE PRECISION NOT NULL DEFAULT 0,
    unit_cost NUMERIC(12, 2) NOT NULL DEFAULT 0,
    low_stock_threshold DOUBLE PRECISION NOT NULL DEFAULT 10,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- ============================================================
-- 8. PROJECT INVENTORY (Site Warehouses)
-- ============================================================
CREATE TABLE project_inventory (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    material_id INTEGER NOT NULL REFERENCES material(id) ON DELETE CASCADE,
    quantity DOUBLE PRECISION NOT NULL DEFAULT 0,
    unit_cost NUMERIC(12, 2) NOT NULL DEFAULT 0,
    low_stock_threshold DOUBLE PRECISION NOT NULL DEFAULT 10,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(project_id, material_id)
);

-- ============================================================
-- 9. WORK PACKAGES
-- ============================================================
CREATE TABLE workpackage (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    stage_id INTEGER REFERENCES stage(id) ON DELETE SET NULL,
    bim_element_id VARCHAR(255) NOT NULL DEFAULT 'NONE',
    name VARCHAR(255) NOT NULL,
    status status_enum NOT NULL DEFAULT 'not_started',
    progress_pct INTEGER NOT NULL DEFAULT 0 CHECK (progress_pct >= 0 AND progress_pct <= 100),
    budget_amount NUMERIC(12, 2) NOT NULL DEFAULT 0,
    actual_cost NUMERIC(12, 2) NOT NULL DEFAULT 0,
    verified_by_id UUID REFERENCES "user"(id) ON DELETE SET NULL,
    approved_by_id UUID REFERENCES "user"(id) ON DELETE SET NULL,
    type wp_type NOT NULL DEFAULT 'task',
    priority wp_priority NOT NULL DEFAULT 'normal',
    logging_period logging_period NOT NULL DEFAULT 'daily',
    start_date TIMESTAMP WITH TIME ZONE,
    due_date TIMESTAMP WITH TIME ZONE,
    parent_id INTEGER REFERENCES workpackage(id) ON DELETE SET NULL,
    assignee_id UUID REFERENCES "user"(id) ON DELETE SET NULL,
    estimated_hours NUMERIC(12, 2) NOT NULL DEFAULT 0,
    spent_hours NUMERIC(12, 2) NOT NULL DEFAULT 0
);

-- ============================================================
-- 10. MATERIAL REQUESTS
-- ============================================================
CREATE TABLE material_request (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    work_package_id INTEGER REFERENCES workpackage(id) ON DELETE SET NULL,
    requester_id UUID REFERENCES "user"(id) ON DELETE SET NULL,
    material_id INTEGER NOT NULL REFERENCES material(id) ON DELETE CASCADE,
    quantity_requested DOUBLE PRECISION NOT NULL,
    status material_request_status NOT NULL DEFAULT 'pending',
    request_date TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- ============================================================
-- 11. SITE UPDATES (Telemetry)
-- ============================================================
CREATE TABLE siteupdate (
    id SERIAL PRIMARY KEY,
    work_package_id INTEGER NOT NULL REFERENCES workpackage(id) ON DELETE CASCADE,
    submitted_by_id UUID NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    notes TEXT,
    photo_url TEXT,
    gps_lat DOUBLE PRECISION,
    gps_long DOUBLE PRECISION,
    weather_info TEXT,
    materials_used TEXT,
    cost_incurred NUMERIC(12, 2) NOT NULL DEFAULT 0
);

-- ============================================================
-- 12. ROW LEVEL SECURITY
-- ============================================================
ALTER TABLE "user" ENABLE ROW LEVEL SECURITY;
ALTER TABLE project ENABLE ROW LEVEL SECURITY;
ALTER TABLE projectassignment ENABLE ROW LEVEL SECURITY;
ALTER TABLE stage ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_inventory ENABLE ROW LEVEL SECURITY;
ALTER TABLE workpackage ENABLE ROW LEVEL SECURITY;
ALTER TABLE siteupdate ENABLE ROW LEVEL SECURITY;
ALTER TABLE material ENABLE ROW LEVEL SECURITY;
ALTER TABLE material_request ENABLE ROW LEVEL SECURITY;

CREATE POLICY "authenticated_access" ON "user" FOR ALL TO authenticated USING (true);
CREATE POLICY "authenticated_access" ON project FOR ALL TO authenticated USING (true);
CREATE POLICY "authenticated_access" ON projectassignment FOR ALL TO authenticated USING (true);
CREATE POLICY "authenticated_access" ON stage FOR ALL TO authenticated USING (true);
CREATE POLICY "authenticated_access" ON project_inventory FOR ALL TO authenticated USING (true);
CREATE POLICY "authenticated_access" ON workpackage FOR ALL TO authenticated USING (true);
CREATE POLICY "authenticated_access" ON siteupdate FOR ALL TO authenticated USING (true);
CREATE POLICY "authenticated_access" ON material FOR ALL TO authenticated USING (true);
CREATE POLICY "authenticated_access" ON material_request FOR ALL TO authenticated USING (true);

-- ============================================================
-- 13. STORAGE BUCKETS
-- ============================================================
INSERT INTO storage.buckets (id, name, public)
VALUES ('site-photos', 'site-photos', true), 
       ('project-resources', 'project-resources', true), 
       ('designs', 'designs', true)
ON CONFLICT (id) DO NOTHING;

DROP POLICY IF EXISTS "Public access for buckets" ON storage.objects;
CREATE POLICY "Public access for buckets" ON storage.objects FOR ALL USING (true);
