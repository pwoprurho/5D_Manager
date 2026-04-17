from backend.app.database import supabase

def check_schema():
    try:
        # Get a single row to see columns
        res = supabase.table("workpackage").select("*").limit(1).execute()
        if res.data:
            print("Columns found in workpackage:", res.data[0].keys())
        else:
            print("No data in workpackage table, cannot infer columns easily.")
            # Try to insert a dummy and see error? No.
            # Best way is to look at all tables info if possible, but Supabase python doesn't expose it easily.
    except Exception as e:
        print(f"Error checking schema: {e}")

if __name__ == "__main__":
    check_schema()
