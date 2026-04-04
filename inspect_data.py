import os
import sys
from dotenv import load_dotenv

# Ensure we can find the backend app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from backend.app.database import supabase

def inspect_data():
    print("--- PROJECT DATA ---")
    try:
        projects = supabase.table("project").select("id, name, bim_model_url").execute()
        for p in projects.data:
            print(f"Project [{p['id']}]: {p['name']}")
            print(f"  BIM URL: {p['bim_model_url']}")
    except Exception as e:
        print(f"Error projects: {e}")

    print("\n--- DESIGN DATA ---")
    try:
        designs = supabase.table("design").select("id, name, model_url").execute()
        for d in designs.data:
            print(f"Design [{d['id']}]: {d['name']}")
            print(f"  Model URL: {d['model_url']}")
    except Exception as e:
        print(f"Error designs: {e}")

    print("\n--- WORK PACKAGE DATA (Sample) ---")
    try:
        wps = supabase.table("workpackage").select("id, name, bim_element_id, project_id").limit(5).execute()
        for wp in wps.data:
            print(f"WP [{wp['id']}] in Project {wp['project_id']}: {wp['name']}")
            print(f"  BIM GUID: {wp['bim_element_id']}")
    except Exception as e:
        print(f"Error wps: {e}")

if __name__ == "__main__":
    inspect_data()
