import ifcopenshell
import os
import tempfile
from typing import List, Dict

def extract_ifc_elements(file_path: str) -> List[Dict]:
    """
    Parses an IFC file and extracts building elements with their GUIDs and Names.
    Focused on structural and significant architectural components.
    """
    if not os.path.exists(file_path):
        return []
        
    try:
        model = ifcopenshell.open(file_path)
        elements = []
        
        # Core building element types to extract
        target_types = [
            "IfcWall", "IfcWallStandardCase", "IfcColumn", "IfcBeam", 
            "IfcSlab", "IfcWindow", "IfcDoor", "IfcMember", "IfcPlate",
            "IfcFurnishingElement", "IfcFlowTerminal", "IfcStair", "IfcRailing"
        ]
        
        for type_name in target_types:
            try:
                for element in model.by_type(type_name):
                    # Extract identifying metadata
                    elements.append({
                        "guid": element.GlobalId,
                        "name": str(element.Name) if element.Name else f"{type_name}_{element.id()}",
                        "type": type_name,
                        "id": element.id()
                    })
            except Exception as e:
                print(f"Warning: Failed to extract type {type_name}: {e}")
                
        return elements
        
    except Exception as e:
        print(f"Critical IFC Parsing Error: {e}")
        return []

def get_bim_elements_from_bytes(file_bytes: bytes, filename: str) -> List[Dict]:
    """Helper to parse IFC data directly from raw bytes using a temporary file."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".ifc") as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name
        
    try:
        return extract_ifc_elements(tmp_path)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
