import sys
modules = [
    "fastapi",
    "uvicorn",
    "pydantic",
    "pydantic_settings",
    "supabase",
    "ifcopenshell",
    "cachetools",
    "starlette",
    "jinja2",
    "requests",
    "numpy",
    "shapely"
]

missing = []
for mod in modules:
    try:
        if mod == "pydantic_settings":
             import pydantic_settings
        else:
             __import__(mod)
        print(f"✅ {mod}")
    except ImportError:
        print(f"❌ {mod}")
        missing.append(mod)

if missing:
    sys.exit(1)
sys.exit(0)
