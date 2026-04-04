import requests
import os
import sys
from io import BytesIO

# Ensure we can find the backend app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from backend.app.services.ifc_parser import get_bim_elements_from_bytes
from backend.app.database import supabase

def test_extraction(project_id=1):
    print(f"Fetching BIM model for project {project_id}...")
    res = supabase.table("project").select("bim_model_url").eq("id", project_id).single().execute()
    url = res.data.get("bim_model_url")
    
    if not url:
        print("No model linked.")
        return

    print(f"Downloading {url}...")
    resp = requests.get(url)
    if resp.status_code != 200:
        print("Download failed.")
        return
    
    print("Extracting elements...")
    elements = get_bim_elements_from_bytes(resp.content, "model.ifc")
    print(f"Found {len(elements)} elements.")
    
    # Print first 5
    for e in elements[:5]:
        print(f" - {e['name']} (GUID: {e['guid']}) - TYPE: {e['type']}")

if __name__ == "__main__":
    test_extraction()
