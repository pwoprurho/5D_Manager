from fastapi import FastAPI, Depends, HTTPException, Request, Response, File, UploadFile, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from starlette.exceptions import HTTPException as StarletteHTTPException
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel
from typing import List, Optional
from cachetools import TTLCache
from functools import wraps
from . import models, database, auth
from .database import supabase
from .services.cost_engine import CostEngine
from .services.report_generator import ReportGenerator

# Terminology Migration: Work Package -> Project Phase
import os

app = FastAPI(title="5D Project Management System")
# Terminology Sync Completed

# Determine base directory for static and template files
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))

# Mount static files
static_path = os.path.join(ROOT_DIR, "static")
app.mount("/static", StaticFiles(directory=static_path), name="static")

# Setup templates
templates_path = os.path.join(ROOT_DIR, "templates")
templates = Jinja2Templates(directory=templates_path)

# Simple in-memory cache for API responses (5 minutes TTL, max 100 items)
api_cache = TTLCache(maxsize=100, ttl=300)

def cache_response(ttl=300):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create a cache key from function name and arguments
            key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            if key in api_cache:
                return api_cache[key]
            result = func(*args, **kwargs)
            api_cache[key] = result
            return result
        return wrapper
    return decorator

@app.on_event("startup")
def on_startup():
    pass

# ============================================================
# EXCEPTION HANDLERS
# ============================================================

@app.exception_handler(403)
async def custom_403_handler(request: Request, exc: StarletteHTTPException):
    content = """<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>403 - Access Restrict</title><link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap" rel="stylesheet"><link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet"><style>:root {--primary-red: #e31837;--deep-black: #0f172a;--glass: rgba(255, 255, 255, 0.05);}body {font-family: 'Outfit', sans-serif;background: radial-gradient(circle at center, #1e293b 0%, #0f172a 100%);color: white;display: flex;align-items: center;justify-content: center;height: 100vh;margin: 0;overflow: hidden;}.error-container {text-align: center;background: var(--glass);backdrop-filter: blur(20px);border: 1px solid rgba(255, 255, 255, 0.1);padding: 4rem;border-radius: 40px;box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);max-width: 500px;width: 90%;position: relative;}.error-code {font-size: 8rem;font-weight: 800;margin: 0;line-height: 1;background: linear-gradient(to bottom, #fff, #64748b);-webkit-background-clip: text;background-clip: text;-webkit-text-fill-color: transparent;opacity: 0.1;position: absolute;top: 50%;left: 50%;transform: translate(-50%, -50%);z-index: -1;}.error-icon {font-size: 4rem;color: #fbbf24;margin-bottom: 2rem;animation: shake 0.5s cubic-bezier(.36, .07, .19, .97) both;animation-iteration-count: 2;}@keyframes shake {10%,90%{transform: translate3d(-1px, 0, 0);}20%,80%{transform: translate3d(2px, 0, 0);}30%,50%,70%{transform: translate3d(-4px, 0, 0);}40%,60%{transform: translate3d(4px, 0, 0);}}h1 {font-size: 2rem;font-weight: 700;margin-bottom: 1rem;}p {color: #94a3b8;line-height: 1.6;margin-bottom: 2.5rem;}.btn-group {display: flex;gap: 1rem;justify-content: center;}.btn {display: inline-flex;align-items: center;gap: 0.75rem;padding: 1rem 1.5rem;border-radius: 12px;text-decoration: none;font-weight: 600;transition: all 0.3s;}.btn-red {background: var(--primary-red);color: white;box-shadow: 0 10px 15px -3px rgba(227, 24, 55, 0.3);}.btn-red:hover {background: #be123c;transform: translateY(-2px);}.btn-outline {border: 2px solid #334155;color: white;}.btn-outline:hover {background: rgba(255, 255, 255, 0.05);border-color: white;transform: translateY(-2px);}</style></head><body><div class="error-container"><div class="error-code">403</div><div class="error-icon"><i class="fas fa-shield-halved"></i></div><h1>Module Restricted</h1><p>This section of the application is still under construction and would be available after the election.</p><div class="btn-group"><a href="/" class="btn btn-outline"><i class="fas fa-house"></i> Home</a><a href="/signin" class="btn btn-red"><i class="fas fa-user-shield"></i> Re-Authenticate</a></div></div></body></html>"""
    return HTMLResponse(content=content, status_code=403)

@app.exception_handler(404)
async def custom_404_handler(request: Request, exc: StarletteHTTPException):
    content = """<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>404 - Discovery Failure</title><link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap" rel="stylesheet"><link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet"><style>:root {--primary-red: #e31837;--deep-black: #0f172a;--glass: rgba(255, 255, 255, 0.05);}body {font-family: 'Outfit', sans-serif;background: radial-gradient(circle at center, #1e293b 0%, #0f172a 100%);color: white;display: flex;align-items: center;justify-content: center;height: 100vh;margin: 0;overflow: hidden;}.error-container {text-align: center;background: var(--glass);backdrop-filter: blur(20px);border: 1px solid rgba(255, 255, 255, 0.1);padding: 4rem;border-radius: 40px;box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);max-width: 500px;width: 90%;position: relative;}.error-code {font-size: 8rem;font-weight: 800;margin: 0;line-height: 1;background: linear-gradient(to bottom, #fff, #64748b);-webkit-background-clip: text;background-clip: text;-webkit-text-fill-color: transparent;opacity: 0.1;position: absolute;top: 50%;left: 50%;transform: translate(-50%, -50%);z-index: -1;}.error-icon {font-size: 4rem;color: var(--primary-red);margin-bottom: 2rem;animation: pulse 2s infinite;}@keyframes pulse {0% {transform: scale(1);opacity: 1;}50% {transform: scale(1.1);opacity: 0.7;}100% {transform: scale(1);opacity: 1;}}h1 {font-size: 2rem;font-weight: 700;margin-bottom: 1rem;}p {color: #94a3b8;line-height: 1.6;margin-bottom: 2.5rem;}.btn-home {display: inline-flex;align-items: center;gap: 0.75rem;background: var(--primary-red);color: white;padding: 1rem 2rem;border-radius: 12px;text-decoration: none;font-weight: 600;transition: all 0.3s;box-shadow: 0 10px 15px -3px rgba(227, 24, 55, 0.3);}.btn-home:hover {background: #be123c;transform: translateY(-2px);box-shadow: 0 20px 25px -5px rgba(227, 24, 55, 0.4);}</style></head><body><div class="error-container"><div class="error-code">404</div><div class="error-icon"><i class="fas fa-map-location-dot"></i></div><h1>Terrain Not Found</h1><p>The coordinate you're attempting to reach does not exist in our primary database. It may be under development or purged.</p><a href="/" class="btn-home"><i class="fas fa-house"></i> Return to Command Center</a></div></body></html>"""
    return HTMLResponse(content=content, status_code=404)

@app.exception_handler(500)
async def custom_500_handler(request: Request, exc: Exception):
    content = """<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>500 - System Failure</title><link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap" rel="stylesheet"><link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet"><style>:root {--primary-red: #e31837;--deep-black: #0f172a;--glass: rgba(255, 255, 255, 0.05);}body {font-family: 'Outfit', sans-serif;background: radial-gradient(circle at center, #1e293b 0%, #0f172a 100%);color: white;display: flex;align-items: center;justify-content: center;height: 100vh;margin: 0;overflow: hidden;}.error-container {text-align: center;background: var(--glass);backdrop-filter: blur(20px);border: 1px solid rgba(255, 255, 255, 0.1);padding: 4rem;border-radius: 40px;box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);max-width: 500px;width: 90%;position: relative;}.error-code {font-size: 8rem;font-weight: 800;margin: 0;line-height: 1;background: linear-gradient(to bottom, #fff, #64748b);-webkit-background-clip: text;background-clip: text;-webkit-text-fill-color: transparent;opacity: 0.1;position: absolute;top: 50%;left: 50%;transform: translate(-50%, -50%);z-index: -1;}.error-icon {font-size: 4rem;color: var(--primary-red);margin-bottom: 2rem;animation: flicker 0.15s infinite;}@keyframes flicker {0% {opacity: 1;}10% {opacity: 0.5;}20% {opacity: 1;}30% {opacity: 0.8;}100% {opacity: 1;}}h1 {font-size: 2rem;font-weight: 700;margin-bottom: 1rem;}p {color: #94a3b8;line-height: 1.6;margin-bottom: 2.5rem;}.btn-retry {display: inline-flex;align-items: center;gap: 0.75rem;background: white;color: black;padding: 1rem 2rem;border-radius: 12px;text-decoration: none;font-weight: 700;transition: all 0.3s;box-shadow: 0 10px 15px -3px rgba(255, 255, 255, 0.1);}.btn-retry:hover {background: #e2e8f0;transform: scale(1.05);}</style></head><body><div class="error-container"><div class="error-code">500</div><div class="error-icon"><i class="fas fa-microchip-slash"></i></div><h1>Critical Core Failure</h1><p>The system encountered an unhandled exception while processing your intelligence request. Our engineering team has been alerted.</p><a href="javascript:location.reload()" class="btn-retry"><i class="fas fa-rotate-right"></i> Reboot Interface</a></div></body></html>"""
    return HTMLResponse(content=content, status_code=500)

# ============================================================
# PAGE ROUTES (Server-rendered Jinja2 templates)
# ============================================================

@app.get("/", response_class=HTMLResponse)
async def home(request: Request, user: models.User = Depends(auth.get_current_user)):
    if not user:
        return RedirectResponse(url="/signin", status_code=303)
    return templates.TemplateResponse(request=request, name="dashboard.html", context={"request": request, "user": user})

@app.get("/signin", response_class=HTMLResponse)
async def signin_page(request: Request):
    response = templates.TemplateResponse(request=request, name="signin.html", context={"request": request})
    response.delete_cookie("access_token")
    return response
@app.post("/signin")
async def signin_form(request: Request):
    form = await request.form()
    username = form.get("username") or form.get("email")
    password = form.get("password")

    if not username or not password:
        return templates.TemplateResponse(request=request, name="signin.html", context={
            "request": request,
            "error": "Please provide username/email and password"
        })

    # If username is provided, support username->email lookup in user table
    email = username
    if "@" not in email:
        user_res = supabase.table("user").select("email").eq("username", username).single().execute()
        if not user_res.data:
            return templates.TemplateResponse(request=request, name="signin.html", context={
                "request": request,
                "error": "User not found"
            })
        email = user_res.data.get("email")

    try:
        auth_response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        if not auth_response or not auth_response.session:
            return templates.TemplateResponse(request=request, name="signin.html", context={
                "request": request,
                "error": "Invalid credentials"
            })

        access_token = auth_response.session.access_token
        refresh_token = auth_response.session.refresh_token
        expires_in = getattr(auth_response.session, 'expires_in', 3600)

        redirect_response = RedirectResponse(url="/", status_code=303)
        redirect_response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True, max_age=expires_in, path="/")
        redirect_response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, max_age=86400*7, path="/")
        return redirect_response

    except Exception as e:
        return templates.TemplateResponse(request=request, name="signin.html", context={
            "request": request,
            "error": str(e)
        })

@app.post("/register")
async def register_form(request: Request):
    form = await request.form()
    username = form.get("username")
    email = form.get("email")
    password = form.get("password")

    if not username or not email or not password:
        return templates.TemplateResponse(request=request, name="register.html", context={
            "request": request,
            "error": "Please fill all fields"
        })

    try:
        existing = supabase.table("user").select("*").or_(f"username.eq.{username},email.eq.{email}").execute()
        if existing.data:
            return templates.TemplateResponse(request=request, name="register.html", context={
                "request": request,
                "error": "Username or email already exists"
            })

        auth_response = supabase.auth.sign_up({
            "email": email,
            "password": password,
            "options": {"data": {"username": username, "role": "staff"}}
        })

        if not auth_response or not auth_response.user:
            return templates.TemplateResponse(request=request, name="register.html", context={
                "request": request,
                "error": "Registration failed"
            })

        user_data = {
            "id": auth_response.user.id,
            "username": username,
            "email": email,
            "role": "staff",
            "is_active": True
        }

        result = supabase.table("user").insert(user_data).execute()
        if not result.data:
            return templates.TemplateResponse(request=request, name="register.html", context={
                "request": request,
                "error": "Failed to create profile"
            })

        return RedirectResponse(url="/signin", status_code=303)

    except Exception as e:
        return templates.TemplateResponse(request=request, name="register.html", context={
            "error": str(e)
        })

@app.post("/signin")
async def signin(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    try:
        user_data = auth.authenticate_user(form_data.username, form_data.password)
        if not user_data:
            return templates.TemplateResponse(request=request, name="signin.html", context={
                "error": "TERMINAL_AUTH_FAILURE: Incorrect credentials"
            })
        
        user_obj = auth.get_user_by_email(form_data.username)
        if not user_obj:
            return templates.TemplateResponse(request=request, name="signin.html", context={
                "error": "PROTOCOL_ERROR: Identity not found"
            })
            
        response = RedirectResponse(url="/dashboard", status_code=303)
        token = auth.create_access_token(data={"sub": user_obj.email})
        response.set_cookie(key="access_token", value=f"Bearer {token}", httponly=True)
        return response
    except Exception as e:
        return templates.TemplateResponse(request=request, name="signin.html", context={
            "error": f"SYSTEM_HALT: {str(e)}"
        })

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse(request=request, name="register.html", context={})

@app.post("/register")
async def register(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    username: str = Form(...),
    role: str = Form("staff")
):
    try:
        user = auth.register_user(email, password, username, role)
        if not user:
            return templates.TemplateResponse(request=request, name="register.html", context={
                "error": "PROVISIONING_FAILED: Email already registered"
            })
        return RedirectResponse(url="/signin", status_code=303)
    except Exception as e:
        return templates.TemplateResponse(request=request, name="register.html", context={
            "error": f"INIT_FAILURE: {str(e)}"
        })

@app.get("/projects", response_class=HTMLResponse)
async def projects_page(request: Request):
    user = await auth.get_current_user(request)
    if not user: return RedirectResponse(url="/signin", status_code=303)
    return templates.TemplateResponse(request=request, name="projects.html", context={"user": user})

@app.get("/designs", response_class=HTMLResponse)
async def designs_page(request: Request):
    user = await auth.get_current_user(request)
    if not user: return RedirectResponse(url="/signin", status_code=303)
    return templates.TemplateResponse(request=request, name="designs.html", context={"user": user})

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return RedirectResponse(url="/static/assets/logo.png")

@app.get("/project-updates", response_class=HTMLResponse)
async def project_updates_base_page(request: Request):
    user = await auth.get_current_user(request)
    if not user: return RedirectResponse(url="/signin", status_code=303)
    return templates.TemplateResponse(request=request, name="project_updates.html", context={"user": user})

@app.get("/site-updates", response_class=HTMLResponse)
async def site_updates_page(request: Request):
    user = await auth.get_current_user(request)
    if not user: return RedirectResponse(url="/signin", status_code=303)
    return templates.TemplateResponse(request=request, name="site_updates.html", context={"user": user})

@app.get("/store", response_class=HTMLResponse)
async def store_page(request: Request):
    user = await auth.get_current_user(request)
    if not user: return RedirectResponse(url="/signin", status_code=303)
    return templates.TemplateResponse(request=request, name="store.html", context={"user": user})

@app.get("/admin/users", response_class=HTMLResponse)
async def admin_users_page(request: Request):
    user = await auth.get_current_user(request)
    if not user or user.role != models.UserRole.admin:
        return RedirectResponse(url="/dashboard", status_code=303)
    return templates.TemplateResponse(request=request, name="admin_users.html", context={"user": user})

# Contextual Project Pages
@app.get("/projects/{project_id}/project-updates", response_class=HTMLResponse)
async def project_updates_page(request: Request, project_id: int):
    """Render Project Update Terminal (formerly Project Phases)."""
    user = await auth.get_current_user(request)
    if not user:
        return RedirectResponse(url="/signin", status_code=303)
    return templates.TemplateResponse(
        request=request, name="project_updates.html", 
        context={"project_id": project_id, "user": user}
    )

@app.get("/projects/{project_id}/kanban", response_class=HTMLResponse)
async def project_kanban_page(request: Request, project_id: int):
    user = await auth.get_current_user(request)
    if not user: return RedirectResponse(url="/signin", status_code=303)
    return templates.TemplateResponse(request=request, name="kanban.html", context={"user": user, "project_id": project_id})

@app.get("/projects/{project_id}/gantt", response_class=HTMLResponse)
async def project_gantt_page(request: Request, project_id: int):
    user = await auth.get_current_user(request)
    if not user: return RedirectResponse(url="/signin", status_code=303)
    return templates.TemplateResponse(request=request, name="gantt.html", context={"user": user, "project_id": project_id})


# ============================================================
# AUTH ENDPOINTS
# ============================================================

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    role: models.UserRole = models.UserRole.staff

class WPUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[models.StatusEnum] = None
    progress_pct: Optional[int] = None
    type: Optional[models.WPType] = None
    priority: Optional[models.WPPriority] = None
    start_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    parent_id: Optional[int] = None
    budget_amount: Optional[Decimal] = None
    actual_cost: Optional[Decimal] = None
    assignee_id: Optional[str] = None
    estimated_hours: Optional[Decimal] = None
    spent_hours: Optional[Decimal] = None

@app.post("/api/v1/auth/signin")
async def signin(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends()
):
    try:
        email = form_data.username
        # If it's a username (no @), fetch the email from our public.user table
        if "@" not in email:
            user_res = supabase.table("user").select("email").eq("username", form_data.username).single().execute()
            if not user_res.data:
                raise HTTPException(status_code=400, detail="User not found")
            email = user_res.data["email"]
            
        # Sign in with Supabase Auth
        auth_response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": form_data.password
        })
        
        if not auth_response or not auth_response.session:
            raise HTTPException(status_code=400, detail="Invalid credentials")
            
        access_token = auth_response.session.access_token
        refresh_token = auth_response.session.refresh_token
        expires_in = getattr(auth_response.session, 'expires_in', 3600)
        
        response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True, max_age=expires_in, path="/")
        response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, max_age=86400*7, path="/")
        return {"access_token": access_token, "token_type": "bearer"}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))



@app.post("/api/v1/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return {"message": "Logged out"}

@app.post("/api/v1/auth/refresh")
async def refresh_session(request: Request, response: Response):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token")
    try:
        auth_response = supabase.auth.refresh_session(refresh_token)
        if not auth_response or not auth_response.session:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        
        access_token = auth_response.session.access_token
        new_refresh_token = auth_response.session.refresh_token
        expires_in = getattr(auth_response.session, 'expires_in', 3600)
        
        response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True, max_age=expires_in, path="/")
        response.set_cookie(key="refresh_token", value=new_refresh_token, httponly=True, max_age=86400*7, path="/")
        return {"message": "Token refreshed"}
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

@app.post("/api/v1/auth/register")
async def register_user(
    reg: RegisterRequest
):
    """Create a new user account via Supabase Auth and link to public.user table."""
    try:
        # 1. Check if user exists in our public table
        existing = supabase.table("user").select("*").or_(f"username.eq.{reg.username},email.eq.{reg.email}").execute()
        if existing.data:
            raise HTTPException(status_code=400, detail="Username or email already exists")
            
        # 2. Register with Supabase Auth
        auth_response = supabase.auth.sign_up({
            "email": reg.email,
            "password": reg.password,
            "options": {"data": {"username": reg.username, "role": reg.role}}
        })
        
        if not auth_response or not auth_response.user:
            raise HTTPException(status_code=400, detail="Registration failed")
            
        # 3. Create entry in our public.user table
        user_data = {
            "id": auth_response.user.id,
            "username": reg.username,
            "email": reg.email,
            "role": reg.role,
            "is_active": True
        }
        
        result = supabase.table("user").insert(user_data).execute()
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to create profile")
            
        return {"message": f"User '{reg.username}' registered successfully", "id": auth_response.user.id}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/users/", response_model=list[models.User])
def list_users(
    admin: models.User = Depends(auth.check_role([models.UserRole.admin, models.UserRole.president]))
):
    result = supabase.table("user").select("*").execute()
    return result.data


@app.patch("/api/v1/users/{user_id}/toggle-active")
def toggle_user_active(
    user_id: str,
    admin: models.User = Depends(auth.check_role([models.UserRole.admin, models.UserRole.president]))
):
    """Toggle a user's active status. Admin only. Cannot disable yourself."""
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot disable your own account")
    
    # Get current status
    user_res = supabase.table("user").select("is_active").eq("id", user_id).single().execute()
    if not user_res.data:
        raise HTTPException(status_code=404, detail="User not found")
        
    new_status = not user_res.data["is_active"]
    supabase.table("user").update({"is_active": new_status}).eq("id", user_id).execute()
    
    return {"message": f"User status updated", "is_active": new_status}



@app.get("/api/v1")
async def api_root():
    return {"message": "5D Project Management System API v1"}

# ============================================================
# REPORT ENDPOINTS
# ============================================================

@app.get("/api/v1/projects/{project_id}/report/pdf")
async def generate_pdf_report(project_id: int, user: models.User = Depends(auth.get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    project_res = supabase.table("project").select("*").eq("id", project_id).single().execute()
    if not project_res.data:
        raise HTTPException(status_code=404, detail="Project not found")
        
    project = project_res.data
    wps = supabase.table("workpackage").select("*").eq("project_id", project_id).execute().data or []
    
    wp_ids = [w.get("id") for w in wps] if wps else []
    updates = []
    if wp_ids:
        updates = supabase.table("siteupdate").select("*").in_("work_package_id", wp_ids).order("timestamp", desc=True).limit(5).execute().data or []
    
    actual_cost = float(sum(w.get("actual_cost", 0) or 0 for w in wps))
    budget_cost = float(sum(w.get("budget_amount", 0) or 0 for w in wps))
    total_progress = sum(w.get("progress_pct", 0) or 0 for w in wps)
    avg_prog = (total_progress / len(wps)) if wps else 0
    earned_value = budget_cost * (avg_prog / 100)
    cpi = earned_value / actual_cost if actual_cost > 0 else 1.0
    eac = budget_cost / cpi if cpi > 0 else budget_cost
    
    stats = {
        "progress_pct": avg_prog,
        "cpi": cpi,
        "eac": eac
    }
    
    from .services.report_generator import generate_project_report
    import tempfile
    
    tmp_path = os.path.join(tempfile.gettempdir(), f"report_{project_id}.pdf")
    generate_project_report(project, stats, wps, updates, tmp_path)
    
    from fastapi.responses import FileResponse
    return FileResponse(tmp_path, media_type="application/pdf", filename=f"Project_{project_id}_Weekly_Report.pdf")

# ============================================================
# DESIGN ENDPOINTS (SHARED BIM MODELS)
# ============================================================

@app.get("/api/v1/designs/", response_model=List[models.Design])
def get_designs(user: models.User = Depends(auth.get_current_user)):
    result = supabase.table("design").select("*").order("created_at", desc=True).execute()
    return [models.Design(**d) for d in result.data]

@app.post("/api/v1/designs/", response_model=models.Design)
async def create_design(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    file: UploadFile = File(...),
    user: models.User = Depends(auth.check_role([models.UserRole.admin, models.UserRole.director, models.UserRole.president]))
):
    if not file.filename.lower().endswith(('.ifc', '.gltf', '.glb')):
        raise HTTPException(status_code=400, detail="Unsupported model format. Use .ifc, .gltf, or .glb")
    
    from .services.supabase_client import upload_file
    file_bytes = await file.read()
    model_url = upload_file(file_bytes, file.filename, "designs")
    
    design_data = {
        "name": name,
        "description": description,
        "model_url": model_url
    }
    result = supabase.table("design").insert(design_data).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create design")
        
    api_cache.clear()
    return models.Design(**result.data[0])

@app.patch("/api/v1/designs/{design_id}", response_model=models.Design)
async def update_design(
    design_id: int,
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    user: models.User = Depends(auth.check_role([models.UserRole.admin, models.UserRole.director, models.UserRole.president]))
):
    """Allows updating design metadata and optionally replacing the BIM model file."""
    # 1. Verify existence
    existing = supabase.table("design").select("*").eq("id", design_id).single().execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Design not found")
        
    update_data = {}
    if name is not None:
        update_data["name"] = name
    if description is not None:
        update_data["description"] = description
        
    # 2. Handle file replacement
    if file:
        if not file.filename.lower().endswith(('.ifc', '.gltf', '.glb')):
            raise HTTPException(status_code=400, detail="Unsupported model format")
            
        from .services.supabase_client import upload_file
        file_bytes = await file.read()
        model_url = upload_file(file_bytes, file.filename, "designs")
        update_data["model_url"] = model_url
        
    if not update_data:
        return models.Design(**existing.data)
        
    # 3. Update in DB
    result = supabase.table("design").update(update_data).eq("id", design_id).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Update operation failed")
        
    api_cache.clear()
    return models.Design(**result.data[0])

@app.get("/api/v1/designs/{design_id}/projects")
def get_design_projects(design_id: int, user: models.User = Depends(auth.get_current_user)):
    """List all projects associated with a specific design."""
    result = supabase.table("project").select("*").eq("design_id", design_id).execute()
    return [models.Project(**p) for p in result.data]

@app.delete("/api/v1/designs/{design_id}")
def delete_design(design_id: int, user: models.User = Depends(auth.check_role([models.UserRole.admin, models.UserRole.president]))):
    supabase.table("design").delete().eq("id", design_id).execute()
    api_cache.clear()
    return {"message": "Design deleted"}

@app.get("/api/v1/designs/{design_id}/elements")
async def get_design_elements(design_id: int, user: models.User = Depends(auth.get_current_user)):
    """Retrieve detailed elements from the design's IFC model."""
    result = supabase.table("design").select("*").eq("id", design_id).single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Design not found")
    
    model_url = result.data.get("model_url")
    if not model_url or not model_url.lower().endswith(".ifc"):
        return []
        
    try:
        import httpx
        from .services.ifc_parser import get_bim_elements_from_bytes
        async with httpx.AsyncClient() as client:
            model_resp = await client.get(model_url)
            if model_resp.status_code == 200:
                elements = get_bim_elements_from_bytes(model_resp.content, "model.ifc")
                return elements
    except Exception as e:
        print(f"BIM element extraction error: {e}")
        
    return []

# ============================================================
# PROJECT ENDPOINTS
# ============================================================

@app.post("/api/v1/projects/", response_model=models.Project)
async def create_project(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    design_id: Optional[int] = Form(None),
    bim_model_url: Optional[str] = Form(None),
    user: models.User = Depends(auth.check_role([models.UserRole.admin, models.UserRole.director, models.UserRole.president]))
):
    project_data = {
        "name": name,
        "description": description,
        "design_id": design_id,
        "bim_model_url": bim_model_url
    }
    result = supabase.table("project").insert(project_data).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create project")
    
    api_cache.clear()
    api_cache.clear()
    return models.Project(**result.data[0])

@app.patch("/api/v1/projects/{project_id}", response_model=models.Project)
async def update_project(
    project_id: int,
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    design_id: Optional[int] = Form(None),
    bim_model_url: Optional[str] = Form(None),
    user: models.User = Depends(auth.check_role([models.UserRole.admin, models.UserRole.director, models.UserRole.president]))
):
    """Updates project metadata. Required to attach/detach designs."""
    update_data = {}
    if name is not None: update_data["name"] = name
    if description is not None: update_data["description"] = description
    if design_id is not None: 
        update_data["design_id"] = design_id if design_id > 0 else None
    if bim_model_url is not None: update_data["bim_model_url"] = bim_model_url

    res = supabase.table("project").update(update_data).eq("id", project_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Project not found")

    api_cache.clear()
    return models.Project(**res.data[0])

@app.post("/api/v1/projects/{project_id}/upload-bim")
async def upload_bim_model(
    project_id: int,
    file: UploadFile = File(...),
    user: models.User = Depends(auth.check_role([models.UserRole.admin, models.UserRole.director, models.UserRole.president]))
):
    """Upload an IFC BIM model directly to a project."""
    # Validate project exists
    project_res = supabase.table("project").select("*").eq("id", project_id).single().execute()
    if not project_res.data:
        raise HTTPException(status_code=404, detail="Project not found")

    if not file.filename.lower().endswith('.ifc'):
        raise HTTPException(status_code=400, detail="Only .ifc files are allowed for BIM models")

    try:
        from .services.supabase_client import upload_file
        file_bytes = await file.read()
        model_url = upload_file(file_bytes, file.filename, f"projects/{project_id}/bim")
        
        # Update project record
        supabase.table("project").update({"bim_model_url": model_url}).eq("id", project_id).execute()
        
        api_cache.clear()
        return {"message": "BIM model uploaded securely", "url": model_url}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"BIM upload failed: {str(e)}")


@app.get("/api/v1/projects/", response_model=list[models.Project])
def read_projects(
    user: models.User = Depends(auth.get_current_user)
):
    """Return projects filtered by user assignment. Directors/admins see all."""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Directors and admins see all projects
    if user.role in [models.UserRole.director, models.UserRole.admin]:
        result = supabase.table("project").select("*").execute()
        return result.data
    
    # Staff and managers only see assigned projects
    assignment_res = supabase.table("projectassignment").select("project_id").eq("user_id", user.id).execute()
    project_ids = [a["project_id"] for a in assignment_res.data]
    
    if not project_ids:
        return []
    
    result = supabase.table("project").select("*").in_("id", project_ids).execute()
    return result.data

@app.get("/api/v1/projects/{project_id}", response_model=models.Project)
def get_project(project_id: int, user: models.User = Depends(auth.get_current_user)):
    """Fetch detail for a specific project."""
    res = supabase.table("project").select("*").eq("id", project_id).single().execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Project not found")
    return models.Project(**res.data)


# --- Project Assignment Endpoints ---

class AssignRequest(BaseModel):
    user_id: str  # UUID
    assigned_role: str = "member"

@app.post("/api/v1/projects/{project_id}/assign")
def assign_user_to_project(
    project_id: int,
    req: AssignRequest,
    user: models.User = Depends(auth.check_role([models.UserRole.admin, models.UserRole.director, models.UserRole.president]))
):
    """Assign a user to a project. Director/Admin only."""
    # Validate project exists
    proj_res = supabase.table("project").select("name").eq("id", project_id).single().execute()
    if not proj_res.data:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Validate target user exists
    user_res = supabase.table("user").select("username").eq("id", req.user_id).single().execute()
    if not user_res.data:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if already assigned
    existing = supabase.table("projectassignment").select("*").eq("project_id", project_id).eq("user_id", req.user_id).execute()
    
    if existing.data:
        # Update role if already assigned
        supabase.table("projectassignment").update({"assigned_role": req.assigned_role}).eq("project_id", project_id).eq("user_id", req.user_id).execute()
        return {"message": f"Updated {user_res.data['username']}'s role on '{proj_res.data['name']}' to '{req.assigned_role}'"}
    
    assignment_data = {
        "project_id": project_id,
        "user_id": req.user_id,
        "assigned_role": req.assigned_role
    }
    supabase.table("projectassignment").insert(assignment_data).execute()
    api_cache.clear()
    return {"message": f"Assigned {user_res.data['username']} to '{proj_res.data['name']}' as {req.assigned_role}"}


@app.delete("/api/v1/projects/{project_id}/unassign/{target_user_id}")
def unassign_user_from_project(
    project_id: int,
    target_user_id: str,
    user: models.User = Depends(auth.check_role([models.UserRole.admin, models.UserRole.director, models.UserRole.president]))
):
    """Remove a user's assignment from a project. Director/Admin only."""
    assignment_res = supabase.table("projectassignment").delete().eq("project_id", project_id).eq("user_id", target_user_id).execute()
    
    if not assignment_res.data:
        raise HTTPException(status_code=404, detail="Assignment not found")
    
    api_cache.clear()
    return {"message": "User unassigned from project"}


@app.get("/api/v1/projects/{project_id}/team")
def get_project_team(
    project_id: int,
    user: models.User = Depends(auth.check_role([models.UserRole.admin, models.UserRole.director, models.UserRole.president]))
):
    """List all users assigned to a project."""
    assignments = supabase.table("projectassignment").select("*, user(*)").eq("project_id", project_id).execute()
    
    result = []
    for a in assignments.data:
        u = a.get("user")
        if u:
            result.append({
                "assignment_id": a["id"],
                "user_id": u["id"],
                "username": u["username"],
                "email": u["email"],
                "role": u["role"],
                "assigned_role": a["assigned_role"],
                "assigned_at": a["assigned_at"]
            })
    return result


@app.get("/api/v1/users/{user_id}/assignments")
def get_user_assignments(
    user_id: str,
    user: models.User = Depends(auth.check_role([models.UserRole.admin, models.UserRole.director, models.UserRole.president]))
):
    """List all projects assigned to a specific user."""
    assignments = supabase.table("projectassignment").select("*, project(*)").eq("user_id", user_id).execute()
    
    result = []
    for a in assignments.data:
        p = a.get("project")
        if p:
            result.append({
                "project_id": p["id"],
                "project_name": p["name"],
                "assigned_role": a["assigned_role"],
                "assigned_at": a["assigned_at"]
            })
    return result



@app.get("/api/v1/projects/{project_id}/stats")
@cache_response(ttl=300)
def get_project_stats(project_id: int):
    # Fetch project
    project_res = supabase.table("project").select("*").eq("id", project_id).single().execute()
    if not project_res.data:
        raise HTTPException(status_code=404, detail="Project not found")
    project_data = project_res.data
    
    # Fetch work packages
    wp_res = supabase.table("workpackage").select("*").eq("project_id", project_id).execute()
    wps = wp_res.data
    
    total_bac = sum(Decimal(str(wp["budget_amount"])) for wp in wps)
    total_ac = sum(Decimal(str(wp["actual_cost"])) for wp in wps)
    avg_progress = sum(wp["progress_pct"] for wp in wps) / len(wps) if wps else 0
    
    ev = CostEngine.calculate_earned_value(total_bac, int(avg_progress))
    cpi = CostEngine.calculate_cpi(ev, total_ac)
    eac = CostEngine.calculate_eac(total_bac, cpi)
    
    # Supabase returns ISO strings for timestamps
    created_at = datetime.fromisoformat(project_data["created_at"].replace("Z", "+00:00"))
    burn_rate = CostEngine.calculate_burn_rate(total_ac, created_at)
    
    # Summary of statuses
    status_counts = {}
    for status in models.StatusEnum:
        status_counts[status.value] = sum(1 for wp in wps if wp["status"] == status.value)
        
    return {
        "project_name": project_data["name"],
        "progress_pct": avg_progress,
        "earned_value": float(ev),
        "actual_cost": float(total_ac),
        "cpi": cpi,
        "eac": float(eac),
        "burn_rate": float(burn_rate),
        "status_summary": status_counts
    }


# ============================================================
# PROJECT UPDATE ENDPOINTS
# ============================================================

@app.post("/api/v1/project-updates/")
def create_project_update(
    wp: models.WorkPackage,
    user: models.User = Depends(auth.check_role([models.UserRole.admin, models.UserRole.director, models.UserRole.manager, models.UserRole.president]))
):
    wp_data = wp.dict(exclude={"id"})
    
    # Handle Decimal/Enum conversions if needed for Supabase
    if "budget_amount" in wp_data:
        wp_data["budget_amount"] = float(wp_data["budget_amount"])
    if "actual_cost" in wp_data:
        wp_data["actual_cost"] = float(wp_data["actual_cost"])
    if "estimated_hours" in wp_data:
        wp_data["estimated_hours"] = float(wp_data["estimated_hours"])
    if "spent_hours" in wp_data:
        wp_data["spent_hours"] = float(wp_data["spent_hours"])
    if "status" in wp_data:
        wp_data["status"] = wp_data["status"].value
    if "type" in wp_data:
        wp_data["type"] = wp_data["type"].value
    if "priority" in wp_data:
        wp_data["priority"] = wp_data["priority"].value
    if "start_date" in wp_data and wp_data["start_date"]:
        wp_data["start_date"] = wp_data["start_date"].isoformat()
    if "due_date" in wp_data and wp_data["due_date"]:
        wp_data["due_date"] = wp_data["due_date"].isoformat()
        
    result = supabase.table("workpackage").insert(wp_data).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create project update")
        
    return models.WorkPackage(**result.data[0])


@app.get("/api/v1/project-updates/{update_id}")
def get_project_update(update_id: int):
    result = supabase.table("workpackage").select("*").eq("id", update_id).single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Project update not found")
    return result.data


@app.get("/api/v1/projects/{project_id}/project-updates")
def get_project_updates(project_id: int):
    """List all updates (tasks) for a project."""
    result = supabase.table("workpackage").select("*").eq("project_id", project_id).execute()
    return result.data


@app.patch("/api/v1/project-updates/{update_id}", response_model=models.WorkPackage)
def update_project_update(
    update_id: int,
    update_data: WPUpdate,
    user: models.User = Depends(auth.check_role([models.UserRole.admin, models.UserRole.director, models.UserRole.manager, models.UserRole.president, models.UserRole.staff]))
):
    """Partial update for a project update."""
    data = update_data.dict(exclude_unset=True)
    
    # Handle Decimal conversion for Supabase
    if "budget_amount" in data and data["budget_amount"] is not None:
        data["budget_amount"] = float(data["budget_amount"])
    if "actual_cost" in data and data["actual_cost"] is not None:
        data["actual_cost"] = float(data["actual_cost"])
    if "estimated_hours" in data and data["estimated_hours"] is not None:
        data["estimated_hours"] = float(data["estimated_hours"])
    if "spent_hours" in data and data["spent_hours"] is not None:
        data["spent_hours"] = float(data["spent_hours"])
    if "status" in data and data["status"]:
        data["status"] = data["status"].value
    if "type" in data and data["type"]:
        data["type"] = data["type"].value
    if "priority" in data and data["priority"]:
        data["priority"] = data["priority"].value
    if "start_date" in data and data["start_date"]:
        data["start_date"] = data["start_date"].isoformat()
    if "due_date" in data and data["due_date"]:
        data["due_date"] = data["due_date"].isoformat()
        
    result = supabase.table("workpackage").update(data).eq("id", update_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Project update not found")
        
    return models.WorkPackage(**result.data[0])


@app.delete("/api/v1/project-updates/{update_id}")
def delete_project_update(
    update_id: int,
    user: models.User = Depends(auth.check_role([models.UserRole.admin, models.UserRole.director, models.UserRole.manager, models.UserRole.president]))
):
    result = supabase.table("workpackage").delete().eq("id", update_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Project update not found")
    return {"message": "Project update deleted successfully"}


@app.get("/api/v1/projects/{project_id}/bim-elements")
async def get_project_bim_elements(project_id: int):
    """
    Downloads and parses the project's linked central BIM model.
    """
    proj_res = supabase.table("project").select("design_id").eq("id", project_id).single().execute()
    if not proj_res.data or not proj_res.data.get("design_id"):
        return {"elements": [], "model_url": None}
    
    design_res = supabase.table("design").select("model_url").eq("id", proj_res.data["design_id"]).single().execute()
    if not design_res.data:
        return {"elements": [], "model_url": None}
    
    model_url = design_res.data["model_url"]
    
    # MISSION CRITICAL: Resolve public URL for Supabase storage if needed
    if model_url and not model_url.startswith("http"):
        storage_res = supabase.storage.from_("designs").get_public_url(model_url)
        model_url = storage_res
    
    # Parse IFC elements from the model file
    elements = []
    if model_url and model_url.lower().endswith('.ifc'):
        try:
            import requests as req
            from .services.ifc_parser import get_bim_elements_from_bytes
            dl = req.get(model_url, timeout=30)
            if dl.status_code == 200:
                elements = get_bim_elements_from_bytes(dl.content, "model.ifc")
        except Exception as parse_err:
            print(f"BIM element parsing skipped: {parse_err}")
    
    return {"elements": elements, "model_url": model_url}


@app.get("/api/v1/projects/{project_id}/kanban")
def get_kanban_data(project_id: int):
    """Returns project phases grouped by status for Kanban board."""
    result = supabase.table("workpackage").select("*").eq("project_id", project_id).execute()
    wps = result.data
    
    # Initialize columns
    board = {status.value: [] for status in models.StatusEnum}
    for wp in wps:
        board[wp["status"]].append(wp)
    
    return board


@app.get("/api/v1/projects/{project_id}/performance")
async def get_project_performance(project_id: int):
    """Calculates CPI, SPI, and EAC for a project using CostEngine."""
    try:
        wps_res = supabase.table("workpackage").select("*").eq("project_id", project_id).execute()
        wps = wps_res.data
        
        if not wps:
            return {"cpi": 1.0, "spi": 1.0, "eac": 0, "bac": 0, "ev": 0, "ac": 0}
            
        bac = sum(Decimal(str(wp.get("budget_amount", 0))) for wp in wps)
        ac = sum(Decimal(str(wp.get("actual_cost", 0))) for wp in wps)
        
        # Calculate EV = sum(BAC_wp * %_wp)
        total_ev = sum(
            CostEngine.calculate_earned_value(
                Decimal(str(wp.get("budget_amount", 0))), 
                wp.get("progress_pct", 0)
            ) for wp in wps
        )
        
        cpi = CostEngine.calculate_cpi(total_ev, ac)
        
        # SPI = EV / PV. Estimating PV based on elapsed time vs schedule if dates exist
        # For simplicity, default to 1.0 if not fully implemented
        spi = 1.0 
        
        eac = CostEngine.calculate_eac(bac, cpi)
        
        return {
            "cpi": round(cpi, 2),
            "spi": round(spi, 2),
            "eac": float(eac),
            "bac": float(bac),
            "ev": float(total_ev),
            "ac": float(ac)
        }
    except Exception as e:
        print(f"Performance calculation error: {e}")
        return {"cpi": 1.0, "spi": 1.0, "eac": 0, "bac": 0, "ev": 0, "ac": 0}


@app.get("/api/v1/projects/{project_id}/report")
async def generate_project_report(project_id: int):
    """Generates a professional PDF status report."""
    try:
        # 1. Fetch Project
        proj_res = supabase.table("project").select("name").eq("id", project_id).single().execute()
        if not proj_res.data:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # 2. Performance data
        perf = await get_project_performance(project_id)
        
        # 3. Work packages
        wps_res = supabase.table("workpackage").select("*").eq("project_id", project_id).execute()
        wps = wps_res.data
        
        # 4. Site updates
        # (Need to fetch via WP IDs)
        wp_ids = [wp["id"] for wp in wps]
        updates_res = supabase.table("siteupdate").select("*").in_("work_package_id", wp_ids).execute()
        updates = updates_res.data or []
        
        # 5. Generate Report
        gen = ReportGenerator(proj_res.data["name"])
        report_url = gen.generate_weekly_status(perf, wps, updates)
        
        return {"report_url": report_url}
    except Exception as e:
        print(f"Report error: {e}")
        raise HTTPException(status_code=500, detail="Report generation failed")


@app.get("/api/v1/projects/{project_id}/gantt")
def get_gantt_data(project_id: int):
    """Returns work packages formatted for Gantt libraries."""
    result = supabase.table("workpackage").select("*").eq("project_id", project_id).execute()
    wps = result.data
    
    gantt_tasks = []
    for wp in wps:
        # Pydantic validation handles date parsing
        wp_obj = models.WorkPackage(**wp)
        start = wp_obj.start_date or datetime.utcnow()
        end = wp_obj.due_date or datetime.utcnow()
        
        gantt_tasks.append({
            "id": str(wp_obj.id),
            "name": wp_obj.name,
            "start": start.strftime("%Y-%m-%d"),
            "end": end.strftime("%Y-%m-%d"),
            "progress": wp_obj.progress_pct,
            "dependencies": str(wp_obj.parent_id) if wp_obj.parent_id else "",
            "custom_class": f"priority-{wp_obj.priority.value}"
        })
    
    return gantt_tasks


# ============================================================
# WORKFLOW & ROLE-BASED ENDPOINTS
# ============================================================

@app.post("/api/v1/project-updates/{update_id}/submit")
async def submit_phase_update(
    update_id: int,
    progress: int = Form(...), 
    notes: str = Form(""),
    materials_used: str = Form(""),
    cost_incurred: float = Form(0.0),
    photo: Optional[UploadFile] = File(None),
    user: models.User = Depends(auth.check_role([models.UserRole.admin, models.UserRole.director, models.UserRole.manager, models.UserRole.president, models.UserRole.staff]))
):
    """Staff submission of work performed with optional photo evidence."""
    status_val = models.StatusEnum.completed if progress >= 100 else models.StatusEnum.in_progress
    
    # 1. Fetch WP for context (project_id)
    wp_current = supabase.table("workpackage").select("project_id, actual_cost").eq("id", update_id).single().execute()
    if not wp_current.data:
        raise HTTPException(status_code=404, detail="Work package not found")
    project_id = wp_current.data["project_id"]
    current_cost = float(wp_current.data.get("actual_cost") or 0)
    new_cost = current_cost + cost_incurred

    # 2. Handle Photo Upload
    photo_url = None
    if photo:
        try:
            from .services.supabase_client import upload_photo
            file_bytes = await photo.read()
            photo_url = upload_photo(file_bytes, photo.filename, project_id, update_id)
        except Exception as e:
            print(f"Submission Photo Upload Failed: {str(e)}")
            # We continue even if photo fails, but ideally we'd log this

    # 3. Update work package
    wp_res = supabase.table("workpackage").update({
        "progress_pct": progress,
        "status": status_val,
        "actual_cost": new_cost
    }).eq("id", update_id).execute()
    
    # 4. Create site update record
    update_data = {
        "work_package_id": update_id,
        "submitted_by_id": user.id,
        "notes": notes,
        "photo_url": photo_url,
        "timestamp": datetime.utcnow().isoformat(),
        "materials_used": materials_used,
        "cost_incurred": cost_incurred
    }
    supabase.table("siteupdate").insert(update_data).execute()
    
    api_cache.clear()
    return {"message": "Update submitted successfully", "status": status_val, "photo_url": photo_url}


@app.post("/api/v1/project-updates/{update_id}/verify")
async def verify_phase(update_id: int, user: models.User = Depends(auth.check_role([models.UserRole.admin, models.UserRole.director, models.UserRole.manager, models.UserRole.president]))):
    result = supabase.table("workpackage").update({"status": "inspected", "verified_by_id": user.id}).eq("id", update_id).execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Work package not found")
        
    return {"message": "Work verified by manager", "status": models.StatusEnum.inspected}

@app.post("/api/v1/project-updates/{update_id}/approve")
async def approve_phase(update_id: int, user: models.User = Depends(auth.check_role([models.UserRole.admin, models.UserRole.director, models.UserRole.president]))):
    result = supabase.table("workpackage").update({"status": "approved", "approved_by_id": user.id}).eq("id", update_id).execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Work package not found")
        
    return {"message": "Work approved by director", "status": models.StatusEnum.approved}


# ============================================================
# SITE UPDATES & PHOTO UPLOAD
# ============================================================

@app.get("/api/v1/site-updates/")
@cache_response(ttl=300)
def read_site_updates(
    project_id: Optional[int] = None
):
    query = supabase.table("siteupdate").select("*, workpackage!inner(*)")
    if project_id:
        query = query.eq("workpackage.project_id", project_id)
        
    result = query.order("timestamp", desc=True).execute()
    return result.data


@app.get("/api/v1/projects/{project_id}/elements")
@cache_response(ttl=3600)
async def get_project_bim_elements(project_id: int, user: models.User = Depends(auth.get_current_user)):
    """Fetch and parse the linked BIM model for a project to return element metadata."""
    # 1. Get project model/design
    proj_res = supabase.table("project").select("bim_model_url, design_id").eq("id", project_id).single().execute()
    if not proj_res.data:
        return [] # No model linked
        
    model_url = proj_res.data.get("bim_model_url")
    design_id = proj_res.data.get("design_id")
    
    if design_id:
        design_res = supabase.table("design").select("model_url").eq("id", design_id).single().execute()
        if design_res.data:
            model_url = design_res.data.get("model_url")
            
    if not model_url:
        return []

    filename = os.path.basename(model_url).split('?')[0] # Strip SAS tokens if any
    
    # 2. Extract elements (Download and Parse)
    try:
        import requests
        from .services.ifc_parser import get_bim_elements_from_bytes
        
        # Download from storage
        resp = requests.get(model_url)
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail="Unable to retrieve BIM model from storage")
            
        elements = get_bim_elements_from_bytes(resp.content, "model.ifc")
        
        # Add filename to each element for UI context
        for e in elements:
            e["model_filename"] = filename
            
        return elements
        
    except Exception as e:
        print(f"BIM Discovery Error: {str(e)}")
        # If library not yet installed, return empty list for now to prevent UI crash
        return []


@app.post("/api/v1/site-updates/{wp_id}/upload-photo")
async def upload_site_photo(
    wp_id: int,
    photo: UploadFile = File(...),
    notes: str = Form(""),
    gps_lat: Optional[float] = Form(None),
    gps_long: Optional[float] = Form(None),
    material_id: Optional[int] = Form(None),
    quantity_used: Optional[float] = Form(None),
    user: models.User = Depends(auth.check_role([
        models.UserRole.staff, models.UserRole.manager, models.UserRole.director, models.UserRole.admin, models.UserRole.president
    ]))
):
    """Upload a site photo and create a site update record."""
    # Validate WP exists and get context
    wp_res = supabase.table("workpackage").select("project_id, actual_cost").eq("id", wp_id).single().execute()
    if not wp_res.data:
        raise HTTPException(status_code=404, detail="Work package not found")
    project_id = wp_res.data["project_id"]
    
    try:
        from .services.supabase_client import upload_photo
        file_bytes = await photo.read()
        photo_url = upload_photo(file_bytes, photo.filename, project_id, wp_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Photo upload failed: {str(e)}")
    
    # 3. Handle Material Usage and Costing
    mat_summary = ""
    cost_calc = 0.0
    
    if material_id and quantity_used and quantity_used > 0:
        try:
            mat_res = supabase.table("material").select("*").eq("id", material_id).single().execute()
            if mat_res.data:
                m = mat_res.data
                mat_summary = f"{m['name']}: {quantity_used} {m['unit']}"
                cost_calc = float(m['unit_cost']) * quantity_used
                
                # Update Inventory Stock
                new_stock = m['current_stock'] - quantity_used
                supabase.table("material").update({"current_stock": new_stock}).eq("id", material_id).execute()
                
                # Update WP Actual Cost (AC) locally for this update
                current_ac = float(wp_res.data.get("actual_cost") or 0)
                supabase.table("workpackage").update({"actual_cost": current_ac + cost_calc}).eq("id", wp_id).execute()
        except Exception as e:
            print(f"Material processing warning: {e}")

    update_data = {
        "work_package_id": wp_id,
        "submitted_by_id": user.id,
        "notes": notes,
        "photo_url": photo_url,
        "gps_lat": gps_lat,
        "gps_long": gps_long,
        "materials_used": mat_summary,
        "cost_incurred": cost_calc,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    result = supabase.table("siteupdate").insert(update_data).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create site update record")
    
    api_cache.clear()
    return {"message": "Photo uploaded successfully", "photo_url": photo_url, "update_id": result.data[0]["id"]}


# ============================================================
# STORE MANAGEMENT API
# ============================================================

@app.on_event("startup")
def seed_materials():
    """Seed initial materials if none exist using Supabase client."""
    try:
        count_res = supabase.table("material").select("id", count="exact").execute()
        if count_res.count == 0:
            materials = [
                {"name": "Cement", "unit": "bags", "current_stock": 500, "unit_cost": 15.50},
                {"name": "Steel Reinforcement", "unit": "tons", "current_stock": 20, "unit_cost": 1200.00},
                {"name": "Coarse Aggregate", "unit": "m3", "current_stock": 100, "unit_cost": 45.00},
                {"name": "Fine Aggregate", "unit": "m3", "current_stock": 120, "unit_cost": 35.00},
                {"name": "Bricks", "unit": "pcs", "current_stock": 10000, "unit_cost": 0.50},
            ]
            supabase.table("material").insert(materials).execute()
            print("Materials seeded successfully via Supabase client.")
    except Exception as e:
        print(f"Warning: Could not seed materials (Supabase might be unreachable): {e}")
@app.get("/api/v1/store/materials", response_model=List[models.Material])
@cache_response(ttl=300)
def get_materials():
    result = supabase.table("material").select("*").execute()
    return result.data

@app.post("/api/v1/store/materials", response_model=models.Material)
def create_material(
    material: models.Material,
    user: models.User = Depends(auth.check_role([models.UserRole.admin, models.UserRole.director, models.UserRole.manager, models.UserRole.president]))
):
    mat_data = material.dict(exclude={"id"})
    if "unit_cost" in mat_data:
        mat_data["unit_cost"] = float(mat_data["unit_cost"])
    
    result = supabase.table("material").insert(mat_data).execute()
    return models.Material(**result.data[0])


@app.put("/api/v1/store/materials/{material_id}", response_model=models.Material)
def update_material(
    material_id: int,
    material_data: models.Material,
    user: models.User = Depends(auth.check_role([models.UserRole.admin, models.UserRole.director, models.UserRole.manager, models.UserRole.president]))
):
    mat_dict = material_data.dict(exclude={"id"}, exclude_unset=True)
    if "unit_cost" in mat_dict:
        mat_dict["unit_cost"] = float(mat_dict["unit_cost"])
        
    result = supabase.table("material").update(mat_dict).eq("id", material_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Material not found")
            
    return models.Material(**result.data[0])

@app.delete("/api/v1/store/materials/{material_id}")
def delete_material(
    material_id: int,
    user: models.User = Depends(auth.check_role([models.UserRole.admin, models.UserRole.president]))
):
    result = supabase.table("material").delete().eq("id", material_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Material not found")
    
    return {"message": "Material deleted successfully"}


@app.get("/api/v1/store/requests", response_model=List[models.MaterialRequest])
def get_material_requests(
    project_id: Optional[int] = None
):
    query = supabase.table("material_request").select("*")
    if project_id:
        query = query.eq("project_id", project_id)
    result = query.order("request_date", desc=True).execute()
    return result.data

@app.post("/api/v1/store/request")
def create_material_request(
    request: models.MaterialRequest,
    user: models.User = Depends(auth.check_role([
        models.UserRole.manager
    ]))
):
    req_data = request.dict(exclude={"id", "requester_id"})
    req_data["requester_id"] = user.id
    req_data["status"] = models.MaterialRequestStatus.pending
    
    # Supabase uses httpx and json.dumps, which cannot serialize datetimes out-of-the-box.
    for k, v in req_data.items():
        if isinstance(v, datetime):
            req_data[k] = v.isoformat()
    
    result = supabase.table("material_request").insert(req_data).execute()
    api_cache.clear()
    return result.data[0]

@app.patch("/api/v1/store/request/{request_id}")
def update_material_request_status(
    request_id: int,
    status: models.MaterialRequestStatus,
    user: models.User = Depends(auth.check_role([
        models.UserRole.admin, models.UserRole.director
    ]))
):
    # 1. Fetch current request
    req_res = supabase.table("material_request").select("*").eq("id", request_id).single().execute()
    if not req_res.data:
        raise HTTPException(status_code=404, detail="Request not found")
    mat_req = req_res.data
    
    # 2. If issuing, decrease stock
    if status == models.MaterialRequestStatus.issued and mat_req["status"] != models.MaterialRequestStatus.issued:
        mat_res = supabase.table("material").select("*").eq("id", mat_req["material_id"]).single().execute()
        if not mat_res.data or mat_res.data["current_stock"] < mat_req["quantity_requested"]:
            raise HTTPException(status_code=400, detail="Insufficient stock")
            
        new_stock = mat_res.data["current_stock"] - mat_req["quantity_requested"]
        supabase.table("material").update({"current_stock": new_stock}).eq("id", mat_req["material_id"]).execute()
    
    supabase.table("material_request").update({"status": status.value}).eq("id", request_id).execute()
    return {"message": f"Request {status.value} successfully"}


@app.delete("/api/v1/store/request/{request_id}")
def delete_material_request(
    request_id: int,
    user: models.User = Depends(auth.check_role([models.UserRole.admin, models.UserRole.director, models.UserRole.manager, models.UserRole.president]))
):
    result = supabase.table("material_request").delete().eq("id", request_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Request not found")
    return {"message": "Material request deleted successfully"}



