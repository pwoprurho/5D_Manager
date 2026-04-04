-- ============================================================
-- 5D Project Management System - Supabase Schema (V3 - UUID Auth & Drops)
-- Run this in your Supabase SQL Editor (Dashboard > SQL Editor)
-- ============================================================

-- ============================================================
-- DROP EXISTING TABLES AND TYPES
-- ============================================================
DROP TABLE IF EXISTS projectassignment CASCADE;
DROP TABLE IF EXISTS material_request CASCADE;
DROP TABLE IF EXISTS material CASCADE;
DROP TABLE IF EXISTS siteupdate CASCADE;
DROP TABLE IF EXISTS workpackage CASCADE;
DROP TABLE IF EXISTS project CASCADE;
DROP TABLE IF EXISTS design CASCADE;
DROP TABLE IF EXISTS "user" CASCADE;

DROP TYPE IF EXISTS user_role CASCADE;
DROP TYPE IF EXISTS status_enum CASCADE;
DROP TYPE IF EXISTS wp_type CASCADE;
DROP TYPE IF EXISTS wp_priority CASCADE;

-- ============================================================
-- 1. ENUM TYPES
-- ============================================================
CREATE TYPE user_role AS ENUM ('staff', 'manager', 'director', 'admin');
CREATE TYPE status_enum AS ENUM ('not_started', 'in_progress', 'completed', 'inspected', 'approved', 'blocked', 'critical');
CREATE TYPE wp_type AS ENUM ('task', 'bug', 'milestone', 'phase');
CREATE TYPE wp_priority AS ENUM ('low', 'normal', 'high', 'immediate');

-- ============================================================
-- 2. USERS TABLE (Linked to Supabase Auth)
-- ============================================================
CREATE TABLE "user" (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    username VARCHAR(255) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    role user_role NOT NULL DEFAULT 'staff',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================
-- 3. DESIGNS TABLE (SHARED BIM MODELS)
-- ============================================================
CREATE TABLE design (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    model_url TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- ============================================================
-- 4. PROJECTS TABLE
-- ============================================================
CREATE TABLE project (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    design_id INTEGER REFERENCES design(id) ON DELETE SET NULL,
    bim_model_url TEXT, -- Legacy support (deprecated)
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- ============================================================
-- 4. WORK PACKAGES TABLE
-- ============================================================
CREATE TABLE workpackage (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    bim_element_id VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    status status_enum NOT NULL DEFAULT 'not_started',
    progress_pct INTEGER NOT NULL DEFAULT 0 CHECK (progress_pct >= 0 AND progress_pct <= 100),
    budget_amount NUMERIC(12, 2) NOT NULL DEFAULT 0,
    actual_cost NUMERIC(12, 2) NOT NULL DEFAULT 0,
    verified_by_id UUID REFERENCES "user"(id) ON DELETE SET NULL,
    approved_by_id UUID REFERENCES "user"(id) ON DELETE SET NULL,
    type wp_type NOT NULL DEFAULT 'task',
    priority wp_priority NOT NULL DEFAULT 'normal',
    start_date TIMESTAMP WITH TIME ZONE,
    due_date TIMESTAMP WITH TIME ZONE,
    parent_id INTEGER REFERENCES workpackage(id) ON DELETE SET NULL,
    assignee_id UUID REFERENCES "user"(id) ON DELETE SET NULL,
    estimated_hours NUMERIC(12, 2) NOT NULL DEFAULT 0,
    spent_hours NUMERIC(12, 2) NOT NULL DEFAULT 0
);

-- ============================================================
-- 5. SITE UPDATES TABLE
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
-- 6. STORE MANAGEMENT TABLES
-- ============================================================
CREATE TABLE material (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    unit VARCHAR(50) NOT NULL,
    current_stock DOUBLE PRECISION NOT NULL DEFAULT 0,
    unit_cost NUMERIC(12, 2) NOT NULL DEFAULT 0
);

CREATE TABLE material_request (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    work_package_id INTEGER REFERENCES workpackage(id) ON DELETE SET NULL,
    requester_id UUID NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    material_id INTEGER NOT NULL REFERENCES material(id) ON DELETE CASCADE,
    quantity_requested DOUBLE PRECISION NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    request_date TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- ============================================================
-- 7. PROJECT ASSIGNMENTS
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
-- 8. RLS POLICIES
-- ============================================================
ALTER TABLE "user" ENABLE ROW LEVEL SECURITY;
ALTER TABLE project ENABLE ROW LEVEL SECURITY;
ALTER TABLE workpackage ENABLE ROW LEVEL SECURITY;
ALTER TABLE siteupdate ENABLE ROW LEVEL SECURITY;

-- Allow full access for authenticated users (the app uses its own Auth mapping for now)
CREATE POLICY "Allow all for authenticated" ON "user" FOR ALL USING (true);
CREATE POLICY "Allow all for authenticated" ON project FOR ALL USING (true);
CREATE POLICY "Allow all for authenticated" ON workpackage FOR ALL USING (true);
CREATE POLICY "Allow all for authenticated" ON siteupdate FOR ALL USING (true);

-- ============================================================
-- 9. STORAGE BUCKETS (Images and 3D Models)
-- ============================================================
-- Note: 'ON CONFLICT DO NOTHING' prevents errors if buckets already exist
INSERT INTO storage.buckets (id, name, public) 
VALUES ('site-photos', 'site-photos', true) 
ON CONFLICT (id) DO NOTHING;

INSERT INTO storage.buckets (id, name, public) 
VALUES ('3d-models', '3d-models', true) 
ON CONFLICT (id) DO NOTHING;

-- Policies for site-photos
DROP POLICY IF EXISTS "Authenticated users can upload photos" ON storage.objects;
CREATE POLICY "Authenticated users can upload photos" ON storage.objects FOR INSERT WITH CHECK (bucket_id = 'site-photos' AND auth.role() = 'authenticated');

DROP POLICY IF EXISTS "Public read access for site photos" ON storage.objects;
CREATE POLICY "Public read access for site photos" ON storage.objects FOR SELECT USING (bucket_id = 'site-photos');

DROP POLICY IF EXISTS "Authenticated users can update own photos" ON storage.objects;
CREATE POLICY "Authenticated users can update own photos" ON storage.objects FOR UPDATE USING (bucket_id = 'site-photos' AND auth.uid()::text = (storage.foldername(name))[1]);

DROP POLICY IF EXISTS "Authenticated users can delete own photos" ON storage.objects;
CREATE POLICY "Authenticated users can delete own photos" ON storage.objects FOR DELETE USING (bucket_id = 'site-photos' AND auth.uid()::text = (storage.foldername(name))[1]);

-- Policies for 3d-models
DROP POLICY IF EXISTS "Authenticated users can upload 3d models" ON storage.objects;
CREATE POLICY "Authenticated users can upload 3d models" ON storage.objects FOR INSERT WITH CHECK (bucket_id = '3d-models' AND auth.role() = 'authenticated');

DROP POLICY IF EXISTS "Public read access for 3d models" ON storage.objects;
CREATE POLICY "Public read access for 3d models" ON storage.objects FOR SELECT USING (bucket_id = '3d-models');

DROP POLICY IF EXISTS "Authenticated users can update own 3d models" ON storage.objects;
CREATE POLICY "Authenticated users can update own 3d models" ON storage.objects FOR UPDATE USING (bucket_id = '3d-models' AND auth.uid()::text = (storage.foldername(name))[1]);

DROP POLICY IF EXISTS "Authenticated users can delete own 3d models" ON storage.objects;
CREATE POLICY "Authenticated users can delete own 3d models" ON storage.objects FOR DELETE USING (bucket_id = '3d-models' AND auth.uid()::text = (storage.foldername(name))[1]);

-- ============================================================
-- 10. TRIGGER FOR NEW USER AUTOMATIC INSERTION
-- ============================================================
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public."user" (id, email, username, role)
  VALUES (
    NEW.id,
    NEW.email,
    SPLIT_PART(NEW.email, '@', 1),
    'staff' -- Default role 
  );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE PROCEDURE public.handle_new_user();
