import re

MAIN_PY = r"c:\Users\Administrator\outbound-caller-python\backend\app\main.py"

with open(MAIN_PY, "r", encoding="utf-8") as f:
    content = f.read()

# Replace phase_id with update_id in submit_phase_update
content = re.sub(r'(async def submit_phase_update\([^\)]*?)phase_id(\s*:\s*int)', r'\1update_id\2', content)
# Replace phase_id inside the function
# We know the function goes until verify_phase.
# To be absolutely safe, let's just replace phase_id with update_id globally inside the endpoint logics 
# where we know it refers to the update_id.

content = content.replace('phase_id', 'update_id')

with open(MAIN_PY, "w", encoding="utf-8") as f:
    f.write(content)
