import os
import re

ADMIN_THERAPIST = [
    "appointments.py", "booking.py",
    "treatments.py", "assessments.py", "posture.py",
    "billing.py", "documents.py"
]

ADMIN_ONLY = [
    "audit.py", "analytics.py", "recycle_bin.py"
]

base_dir = "app/api/v1"

def patch_file(filename, is_admin_only):
    filepath = os.path.join(base_dir, filename)
    if not os.path.exists(filepath):
        print(f"Skipping {filepath}")
        return
        
    with open(filepath, "r") as f:
        content = f.read()
        
    if "require_admin" in content or "require_roles" in content:
        print(f"Already patched {filepath}")
        return
        
    # Import
    if is_admin_only:
        import_stmt = "from app.core.dependencies import require_admin\n"
        router_stmt = "router = APIRouter(dependencies=[Depends(require_admin)])"
    else:
        import_stmt = "from app.core.dependencies import require_roles\nfrom app.enums.user import UserRole\n"
        router_stmt = "router = APIRouter(dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.THERAPIST))])"
        
    # Add imports after first from fastapi import
    content = re.sub(r'(from fastapi import [^\n]+)', r'\1\n' + import_stmt, content, count=1)
    
    # Replace router
    content = content.replace("router = APIRouter()", router_stmt)
    
    with open(filepath, "w") as f:
        f.write(content)
        
    print(f"Patched {filepath}")

for f in ADMIN_THERAPIST:
    patch_file(f, False)

for f in ADMIN_ONLY:
    patch_file(f, True)

