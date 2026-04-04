def test_read_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Operational Dashboard" in response.text  # Check if dashboard template is rendered

def get_auth_headers(client):
    # Login as admin to get token for tests
    resp = client.post("/api/v1/auth/signin", data={"username":"admin", "password":"admin123"})
    token = resp.json().get("access_token")
    return {"Authorization": f"Bearer {token}"}

def test_create_project(client):
    headers = get_auth_headers(client)
    response = client.post(
        "/api/v1/projects/",
        json={"name": "Test Project", "description": "A project for testing"},
        headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Project"
    assert "id" in data

def test_read_projects(client):
    headers = get_auth_headers(client)
    # First create a project
    client.post(
        "/api/v1/projects/",
        json={"name": "Project 1"},
        headers=headers
    )
    
    response = client.get("/api/v1/projects/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["name"] == "Project 1"

def test_full_workflow_and_stats(client, session):
    headers = get_auth_headers(client)
    # 1. Setup - Create Project and Work Package
    proj_resp = client.post("/api/v1/projects/", json={"name": "Build House"}, headers=headers)
    proj_id = proj_resp.json()["id"]
    
    # Create WP using the API
    wp_resp = client.post(
        "/api/v1/work-packages/",
        json={"project_id": proj_id, "bim_element_id": "IFC_123", "name": "Foundation", "budget_amount": 10000, "actual_cost": 8000},
        headers=headers
    )
    assert wp_resp.status_code == 200
    wp_id = wp_resp.json()["id"]

    # 2. Staff Submission (Uses Form Data)
    # We need a staff user for this to be "realistic", but admin can also do it per auth.check_role
    resp = client.post(
        f"/api/v1/work-packages/{wp_id}/submit",
        data={"progress": 100, "notes": "Done"},
        headers=headers
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"

    # 3. Manager Verification
    resp = client.post(f"/api/v1/work-packages/{wp_id}/verify", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "inspected"

    # 4. Director Approval
    resp = client.post(f"/api/v1/work-packages/{wp_id}/approve", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"

    # 5. Verify Stats (Cost Engine)
    stats_resp = client.get(f"/api/v1/projects/{proj_id}/stats")
    assert stats_resp.status_code == 200
    stats = stats_resp.json()
    assert stats["cpi"] > 1.0  # EV (10000) / AC (8000) = 1.25
    assert stats["actual_cost"] == 8000
