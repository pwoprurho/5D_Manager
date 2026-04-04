import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test_store_workflow():
    # 1. Login
    login_data = {"username": "superadmin", "password": "password"}
    session = requests.Session()
    resp = session.post(f"{BASE_URL}/api/v1/auth/signin", data=login_data)
    if resp.status_code != 200:
        print(f"Login failed: {resp.text}")
        return

    # 2. Get Materials
    resp = session.get(f"{BASE_URL}/api/v1/store/materials")
    materials = resp.json()
    cement = next((m for m in materials if m['name'] == 'Cement'), None)
    if not cement:
        print("Cement not found in inventory")
        return
    initial_stock = cement['current_stock']
    print(f"Initial Cement Stock: {initial_stock}")

    # 3. Create Request
    req_data = {
        "project_id": 1,
        "material_id": cement['id'],
        "quantity_requested": 10.0
    }
    resp = session.post(f"{BASE_URL}/api/v1/store/request", json=req_data)
    if resp.status_code != 200:
        print(f"Request creation failed: {resp.text}")
        return
    request_id = resp.json()['id']
    print(f"Created Request ID: {request_id}")

    # 4. Approve Request
    resp = session.patch(f"{BASE_URL}/api/v1/store/request/{request_id}?status=approved")
    if resp.status_code != 200:
        print(f"Approval failed: {resp.text}")
        return
    print("Request approved")

    # 5. Issue Request (Should decrease stock)
    resp = session.patch(f"{BASE_URL}/api/v1/store/request/{request_id}?status=issued")
    if resp.status_code != 200:
        print(f"Issuance failed: {resp.text}")
        return
    print("Request issued")

    # 6. Verify Stock
    resp = session.get(f"{BASE_URL}/api/v1/store/materials")
    materials = resp.json()
    cement = next((m for m in materials if m['name'] == 'Cement'), None)
    new_stock = cement['current_stock']
    print(f"New Cement Stock: {new_stock}")

    if initial_stock - new_stock == 10.0:
        print("VERIFICATION SUCCESSFUL: Stock decreased correctly.")
    else:
        print(f"VERIFICATION FAILED: Stock difference is {initial_stock - new_stock}")

if __name__ == "__main__":
    test_store_workflow()
