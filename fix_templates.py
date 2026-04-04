import re

with open('backend/app/main.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Replace templates.TemplateResponse("something.html", {"request": request, ...})
# with templates.TemplateResponse(request=request, name="something.html", context={"request": request, ...})

new_code = re.sub(
    r'templates\.TemplateResponse\(\s*([\'\"][^\'\"]+[\'\"])\s*,\s*(\{.*?\})\s*\)',
    r'templates.TemplateResponse(request=request, name=\1, context=\2)',
    code,
    flags=re.DOTALL
)

with open('backend/app/main.py', 'w', encoding='utf-8') as f:
    f.write(new_code)

print("Updated TemplateResponse calls.")
