import sys
import os

# Add the backend path to sys.path so we can import the service
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

try:
    from app.services.ifc_parser import extract_ifc_elements
    print("SUCCESS: IFC Parser service imported.")
except ImportError as e:
    print(f"ERROR: Could not import IFC Parser (is ifcopenshell installed?): {e}")
    sys.exit(1)

# Sample file to test
SAMPLE_FILE = r"C:\Users\Administrator\Desktop\IfcSampleFiles-main\Ifc2s3_Duplex_Electrical.ifc"

if not os.path.exists(SAMPLE_FILE):
    print(f"ERROR: Sample file not found at {SAMPLE_FILE}")
    sys.exit(1)

print(f"Starting parse of {SAMPLE_FILE}...")
elements = extract_ifc_elements(SAMPLE_FILE)

if elements:
    print(f"SUCCESS: Extracted {len(elements)} elements.")
    print("Preview of first 5 elements:")
    for e in elements[:5]:
        print(f" - [{e.get('type')}] {e.get('name')} (GUID: {e.get('guid')})")
else:
    print("FAILURE: No elements extracted.")
