from fastapi import FastAPI, Depends, HTTPException, Request, Response, File, UploadFile, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from datetime import datetime, timezone
from decimal import Decimal
from pydantic import BaseModel, Field
from typing import List, Optional
from cachetools import TTLCache
from functools import wraps
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from . import models, database, auth
from .database import supabase, with_retry, async_with_retry
from .services.cost_engine import CostEngine
from .services.report_generator import ReportGenerator
import asyncio
import os
import re
import io
import logging
import mimetypes
try:
    from PIL import Image
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False

try:
    from pypdf import PdfReader, PdfWriter
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False

# Industrial logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vinicius")

# ============================================================
# APP INITIALIZATION & SECURITY MIDDLEWARE
# ============================================================

# Rate Limiter: 3 auth attempts per 20 hours per IP
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="5D Project Management System")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ============================================================
# SECURITY HARDENING MIDDLEWARE
# ============================================================

from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        # HSTS - Force HTTPS (365 days)
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        # Content Security Policy - Mitigate XSS and Data Injection
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdnjs.cloudflare.com https://cdn.jsdelivr.net https://*.supabase.co; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com; "
            "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com; "
            "img-src 'self' data: https://*.supabase.co https://*.supabase.in; "
            "frame-ancestors 'none'; "
            "upgrade-insecure-requests"
        )
        # Clickjacking Protection
        response.headers["X-Frame-Options"] = "DENY"
        # MIME Sniffing Protection
        response.headers["X-Content-Type-Options"] = "nosniff"
        # XSS Protection for older browsers
        response.headers["X-XSS-Protection"] = "1; mode=block"
        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

app.add_middleware(SecurityHeadersMiddleware)

# CORS Middleware — restricted same-origin policy
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("ALLOWED_ORIGIN", "*")],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["*"],
)

# GZip Middleware — compression for efficient telemetry uplinks
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Max upload size: 100MB (Optimized for portfolio documentation and site telemetry)
MAX_UPLOAD_BYTES = 100 * 1024 * 1024

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

def serialize_for_supabase(data: dict) -> dict:
    """Helper to convert Pydantic dict values into Supabase-compatible JSON."""
    from enum import Enum
    output = {}
    for k, v in data.items():
        if isinstance(v, datetime):
            output[k] = v.isoformat()
        elif isinstance(v, Decimal):
            output[k] = float(v)
        elif isinstance(v, Enum):
            output[k] = v.value
        else:
            output[k] = v
    return output

async def check_project_access(user: models.User, project_id: int):
    """Tactical Clearance Gate: Ensures user is authorized for the given project node."""
    if user.role in [models.UserRole.admin, models.UserRole.director]:
        return True
    
    res = await async_with_retry(lambda: supabase.table("projectassignment")
        .select("id")
        .eq("project_id", project_id)
        .eq("user_id", user.id)
        .execute())
    
    if not res.data:
        raise HTTPException(status_code=403, detail="Unauthorized: Site access not registered in tactical registry.")
    return True

def cache_response(ttl=300):
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            if key in api_cache:
                return api_cache[key]
            result = await func(*args, **kwargs)
            api_cache[key] = result
            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            if key in api_cache:
                return api_cache[key]
            result = func(*args, **kwargs)
            api_cache[key] = result
            return result

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator

@app.on_event("startup")
def on_startup():
    """Industrial startup sequence: sync database link and verify telemetry registry."""
    logger.info("Supabase Infrastructure — Command node operational.")
    
    # Diagnostic Telemetry
    opt_status = "Operational" if HAS_PYPDF else "Library Missing (pip install pypdf)"
    img_status = "Operational" if HAS_PILLOW else "Library Missing (pip install Pillow)"
    logger.info(f"System Gates — PDF Optimizer: {opt_status}")
    logger.info(f"System Gates — Image Optimizer: {img_status}")

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
async def home(request: Request):
    user = await auth.get_current_user(request)
    if user:
        return RedirectResponse(url="/dashboard", status_code=303)
    return templates.TemplateResponse(request=request, name="index.html", context={"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, user: models.User = Depends(auth.get_current_user)):
    if not user:
        return RedirectResponse(url="/signin", status_code=303)
    return templates.TemplateResponse(request=request, name="dashboard.html", context={"request": request, "user": user})

@app.get("/logout")
async def logout(request: Request):
    response = RedirectResponse(url="/signin", status_code=302)
    response.delete_cookie("access_token")
    return response

@app.get("/signin", response_class=HTMLResponse)
async def signin_page(request: Request):
    response = templates.TemplateResponse(request=request, name="signin.html", context={"request": request})
    response.delete_cookie("access_token")
    return response
@app.post("/signin")
@limiter.limit("300/20hours")
async def signin_form(request: Request):
    form = await request.form()
    username = form.get("username") or form.get("email")
    password = form.get("password")

    if not username or not password:
        return templates.TemplateResponse(request=request, name="signin.html", context={
            "request": request,
            "error": "Please provide username/email and password"
        })

    # Resolve username to email via Supabase Auth (zero-trust: no public.user dependency)
    email = username.strip()
    if "@" not in email:
        # Look up email from Supabase Auth admin API or public.user as fallback
        found_email = None
        
        try:
            user_res = with_retry(lambda: supabase.table("user").select("email").eq("username", email).maybe_single().execute())
            if user_res and user_res.data:
                found_email = user_res.data.get("email")
        except Exception:
            pass
        
        # Fallback: search Supabase Auth users by metadata
        if not found_email:
            try:
                resp = supabase.auth.admin.list_users()
                auth_users = resp.users if hasattr(resp, 'users') else (resp if isinstance(resp, list) else [])
                for au in auth_users:
                    meta = au.user_metadata or {}
                    if meta.get("username", "").lower() == email.lower():
                        found_email = au.email
                        break
            except Exception:
                pass
        
        if not found_email:
            return templates.TemplateResponse(request=request, name="signin.html", context={
                "request": request,
                "error": "Invalid credentials"
            })
        email = found_email

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

        redirect_response = RedirectResponse(url="/dashboard", status_code=303)
        # Security Hardened Cookies: httponly, secure, samesite=strict
        redirect_response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True, max_age=expires_in, path="/", samesite="strict", secure=True)
        redirect_response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, max_age=86400*7, path="/", samesite="strict", secure=True)
        return redirect_response

    except Exception as e:
        print(f"Signin error: {e}")
        return templates.TemplateResponse(request=request, name="signin.html", context={
            "request": request,
            "error": "Authentication failed. Please check your credentials."
        })

# ============================================================
# ONBOARDING & MANUAL HUB
# ============================================================

@app.get("/register", response_class=HTMLResponse)
async def manual_page(request: Request):
    """Operational Manual & Workflow Guide Hub."""
    return templates.TemplateResponse(request=request, name="register.html", context={"request": request})

@app.get("/download", response_class=HTMLResponse)
async def download_page(request: Request):
    """Download and Installation portal for the Vinicius Command PWA."""
    return templates.TemplateResponse(request=request, name="download.html", context={"request": request})

@app.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request):
    """Initial user enrollment interface."""
    return templates.TemplateResponse(request=request, name="signup.html", context={"request": request})

@app.post("/signup")
@limiter.limit("5/hours")
async def signup_submit(request: Request):
    """Process new operational node enrollment."""
    form = await request.form()
    email = form.get("email")
    password = form.get("password")
    username = form.get("username")
    role = form.get("role", "engineer")

    if not email or not password or not username:
        return templates.TemplateResponse(request=request, name="signup.html", context={
            "request": request, "error": "All operational fields are mandatory."
        })

    try:
        # 1. Supabase Auth Enrollment (Administrative Ingest to bypass Domain Restrictions)
        auth_res = supabase.auth.admin.create_user({
            "email": email,
            "password": password,
            "email_confirm": True,
            "user_metadata": {
                "username": username,
                "role": role
            }
        })
        
        if not auth_res or not auth_res.user:
            return templates.TemplateResponse(request=request, name="signup.html", context={
                "request": request, "error": "Enrollment Rejected: Administrative Protocol Conflict."
            })

        # 2. Sync to Public Registry
        with_retry(lambda: supabase.table("user").upsert({
            "id": auth_res.user.id,
            "email": email,
            "username": username,
            "role": role,
            "is_active": True
        }).execute())

        # 3. Auto-Sign-In and Redirect to Manual
        return templates.TemplateResponse(request=request, name="register.html", context={
            "request": request,
            "success": "Enrollment Successful. Please review the Operational Manual below."
        })

    except Exception as e:
        print(f"Enrollment Error: {e}")
        return templates.TemplateResponse(request=request, name="signup.html", context={
            "request": request, "error": f"Synchronization Failure: {str(e)}"
        })

@app.get("/reset-password", response_class=HTMLResponse)
async def reset_password_page(request: Request):
    return templates.TemplateResponse(request=request, name="reset_password.html", context={})

@app.post("/reset-password")
@limiter.limit("200/20hours")
async def reset_password_submit(request: Request):
    """Password reset via Supabase email recovery flow."""
    form = await request.form()
    email = form.get("email")
    
    if not email:
        return templates.TemplateResponse(request=request, name="reset_password.html", context={"error": "Email is required"})
    
    try:
        # Use Supabase's built-in password recovery (sends reset email)
        supabase.auth.reset_password_email(email)
        return templates.TemplateResponse(request=request, name="signin.html", context={
            "request": request,
            "error": "If an account exists with that email, a password reset link has been sent."
        })
    except Exception as e:
        print(f"Password reset error: {e}")
        return templates.TemplateResponse(request=request, name="reset_password.html", context={"error": "Recovery synchronization failed."})

@app.get("/update-password", response_class=HTMLResponse)
async def update_password_page(request: Request):
    """The landing page for Supabase email recovery links."""
    return templates.TemplateResponse(request=request, name="update_password.html", context={"request": request})


class UpdatePasswordRequest(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    new_password: str

@app.post("/update-password")
async def update_password_submit(req: UpdatePasswordRequest):
    """Securely execute password update using recovery session."""
    try:
        # Establish temporary session from recovery token
        supabase.auth.set_session(req.access_token, req.refresh_token or "")
        
        # Execute tactical password update
        supabase.auth.update_user({"password": req.new_password})
        
        return {"status": "success", "message": "Passphrase updated successfully"}
    except Exception as e:
        print(f"Password reset confirmation error: {e}")
        raise HTTPException(status_code=400, detail="Invalid or expired recovery session.")

@app.get("/settings", response_class=HTMLResponse)
async def settings_get(request: Request, user: models.User = Depends(auth.get_current_user)):
    return templates.TemplateResponse(request=request, name="settings.html", context={"user": user})

@app.post("/settings", response_class=HTMLResponse)
async def settings_post(
    request: Request,
    new_password: str = Form(...),
    user: models.User = Depends(auth.get_current_user)
):
    try:
        token = request.cookies.get("access_token")
        if token and token.startswith("Bearer "):
            token = token.split(" ")[1]
            
        supabase.auth.set_session(token, "") 
        supabase.auth.update_user({"password": new_password})
        
        return templates.TemplateResponse(request=request, name="settings.html", context={
            "user": user, 
            "success": "Security Passphrase has been successfully updated!"
        })
    except Exception as e:
        print(f"Failed to update password: {e}")
        return templates.TemplateResponse(request=request, name="settings.html", context={
            "user": user,
            "error": "Failed to update security credentials."
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

@app.get("/site_updates", response_class=HTMLResponse)
async def legacy_site_updates_redirect(request: Request):
    return RedirectResponse(url="/site-updates")

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
    if not user or user.role not in [models.UserRole.admin, models.UserRole.director]:
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

@app.get("/download", response_class=HTMLResponse)
async def download_page(request: Request):
    user = await auth.get_current_user(request)
    return templates.TemplateResponse("download.html", {"request": request, "user": user})

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
    email: str
    username: str
    password: str
    role: models.UserRole

class UpdatePasswordRequest(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    new_password: str

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

class SiteUpdatePatch(BaseModel):
    notes: Optional[str] = None
    progress_captured: Optional[int] = Field(None, ge=0, le=100)
    cost_incurred: Optional[float] = None

@app.post("/api/v1/auth/signin")
@limiter.limit("3/20hours")
async def signin(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends()
):
    try:
        email = form_data.username
        if "@" not in email:
            user_res = supabase.table("user").select("email").eq("username", form_data.username).single().execute()
            if not user_res.data:
                raise HTTPException(status_code=400, detail="Invalid credentials")
            email = user_res.data["email"]
            
        auth_response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": form_data.password
        })
        
        if not auth_response or not auth_response.session:
            raise HTTPException(status_code=400, detail="Invalid credentials")
            
        access_token = auth_response.session.access_token
        refresh_token = auth_response.session.refresh_token
        expires_in = getattr(auth_response.session, 'expires_in', 3600)
        
        response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True, max_age=expires_in, path="/", samesite="strict", secure=True)
        response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, max_age=86400*7, path="/", samesite="strict", secure=True)
        return {"access_token": access_token, "token_type": "bearer"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"API signin error: {e}")
        raise HTTPException(status_code=400, detail="Authentication failed")



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
        
        response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True, max_age=expires_in, path="/", samesite="strict", secure=True)
        response.set_cookie(key="refresh_token", value=new_refresh_token, httponly=True, max_age=86400*7, path="/", samesite="strict", secure=True)
        return {"message": "Token refreshed"}
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

@app.post("/api/v1/auth/register")
async def register_user(
    reg: RegisterRequest,
    admin: models.User = Depends(auth.check_role([models.UserRole.admin, models.UserRole.director]))
):
    """Admin/Director creates user accounts via Supabase Admin API (same as seed_users.py)."""
    try:
        # 1. Check if user exists
        existing = supabase.table("user").select("id").or_(f"username.eq.{reg.username},email.eq.{reg.email}").execute()
        if existing.data:
            raise HTTPException(status_code=400, detail="Username or email already in use.")
            
        # 2. Create via Admin API (same pattern as seed_users.py)
        auth_response = supabase.auth.admin.create_user({
            "email": reg.email,
            "password": reg.password,
            "email_confirm": True,
            "user_metadata": {"username": reg.username, "role": reg.role.value}
        })
        
        if not auth_response or not auth_response.user:
            raise HTTPException(status_code=400, detail="Registration failed")
            
        # 3. Sync to public.user table (upsert like seed_users.py)
        user_data = {
            "id": auth_response.user.id,
            "username": reg.username,
            "email": reg.email,
            "role": reg.role.value,
            "is_active": True
        }
        supabase.table("user").upsert(user_data).execute()
            
        return {"message": f"User '{reg.username}' registered successfully", "id": auth_response.user.id}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Registration error: {e}")
        raise HTTPException(status_code=400, detail="Registration failed. Please try again.")


@app.get("/api/v1/users/", response_model=list[models.User])
def list_users(
    user: models.User = Depends(auth.check_role([models.UserRole.admin, models.UserRole.director, models.UserRole.manager]))
):
    result = with_retry(lambda: supabase.table("user").select("*").execute())
    return result.data


@app.patch("/api/v1/users/{user_id}/toggle-active")
def toggle_user_active(
    user_id: str,
    admin: models.User = Depends(auth.check_role([models.UserRole.admin, models.UserRole.director]))
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
    user: models.User = Depends(auth.check_role([models.UserRole.admin, models.UserRole.director]))
):
    if not file.filename.lower().endswith(('.gltf', '.glb', '.pdf', '.jpg', '.jpeg', '.png', '.pptx', '.mp4', '.webm', '.ogg')):
        raise HTTPException(status_code=400, detail="Unsupported format. Use 3D models, documents, or video formats")
    
    from .services.supabase_client import upload_file
    file_bytes = await file.read()
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"File too large. Maximum size is 100MB.")
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
    user: models.User = Depends(auth.check_role([models.UserRole.admin, models.UserRole.director]))
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
        if not file.filename.lower().endswith(('.gltf', '.glb', '.pdf', '.jpg', '.jpeg', '.png', '.pptx', '.mp4', '.webm', '.ogg')):
            raise HTTPException(status_code=400, detail="Unsupported format")
            
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
def delete_design(design_id: int, user: models.User = Depends(auth.check_role([models.UserRole.admin, models.UserRole.director]))):
    supabase.table("design").delete().eq("id", design_id).execute()
    api_cache.clear()
    return {"message": "Design deleted"}


# ============================================================
# PROJECT ENDPOINTS
# ============================================================

@app.get("/api/v1/projects/{project_id}", response_model=models.Project)
async def get_project_node(project_id: int, user: models.User = Depends(auth.get_current_user)):
    """Retrieve high-fidelity telemetry for a specific project node with authorization check."""
    # 1. Authorization Gate
    if user.role not in [models.UserRole.admin, models.UserRole.director]:
        assignment_res = await async_with_retry(lambda: supabase.table("projectassignment").select("id").eq("project_id", project_id).eq("user_id", user.id).execute())
        if not assignment_res.data:
            raise HTTPException(status_code=403, detail="Unauthorized: You represent no authorized interest in this site node.")
            
    res = await async_with_retry(lambda: supabase.table("project").select("*").eq("id", project_id).single().execute())
    if not res.data:
        raise HTTPException(status_code=404, detail="Project node not found")
    return models.Project(**res.data)


@app.post("/api/v1/projects/", response_model=models.Project)
async def create_project(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    files: List[UploadFile] = File(None),
    assignee_id: Optional[str] = Form(None),
    materials_data: Optional[str] = Form(None), # JSON: [{"id": 1, "cost": 10.5}, ...]
    user: models.User = Depends(auth.check_role([models.UserRole.admin, models.UserRole.director, models.UserRole.manager]))
):
    """Director/PM creates project with direct resource upload."""
    
    # 0. Registry Integrity: Ensure assignee exists before authorizing infrastructure persistence
    if assignee_id and len(assignee_id.strip()) > 30:
        try:
            check = with_retry(lambda: supabase.table("user").select("id").eq("id", assignee_id).maybe_single().execute())
            if not check.data:
                logger.error(f"Registry Rejection: Operative ID {assignee_id} not found in personnel directory.")
                raise HTTPException(status_code=400, detail=f"Invalid Assignment: Operative ID {assignee_id} does not exist in the tactical node.")
        except HTTPException: raise
        except Exception as e:
            logger.error(f"Registry Validation Failure: {e}")
            raise HTTPException(status_code=500, detail="Tactical Personnel Verification Failed.")

    model_urls = []
    if files:
        for file in files:
            try:
                from .services.supabase_client import upload_file
                
                # Mission Critical: Sanitize filename to prevent cloud storage 400 errors
                clean_filename = re.sub(r'[^a-zA-Z0-9._-]', '_', file.filename)
                
                file_bytes = await file.read()
                
                # File Optimization Sequence
                if file.content_type == 'application/pdf':
                    try:
                        import io
                        from pypdf import PdfWriter, PdfReader
                        
                        pdf_io = io.BytesIO()
                        reader = PdfReader(io.BytesIO(file_bytes))
                        
                        # Aggressive visual reconstruction for PDF optimization
                        if HAS_PILLOW:
                            extracted_images = []
                            for i, page in enumerate(reader.pages):
                                for image_obj in page.images:
                                    try:
                                        img = Image.open(io.BytesIO(image_obj.data))
                                        if img.mode != 'RGB': img = img.convert('RGB')
                                        extracted_images.append(img)
                                    except: continue
                            
                            if extracted_images:
                                extracted_images[0].save(pdf_io, format='PDF', save_all=True, append_images=extracted_images[1:], quality=70)
                                file_bytes = pdf_io.getvalue()
                                logger.info(f"Visual Reconstruction Complete: {len(file_bytes)/1024/1024:.1f}MB (Text-Free)")
                            else:
                                writer = PdfWriter()
                                for page in reader.pages:
                                    page.compress_content_streams()
                                    writer.add_page(page)
                                writer.remove_unreferenced_objects()
                                out = io.BytesIO()
                                writer.write(out)
                                file_bytes = out.getvalue()
                        else:
                            writer = PdfWriter()
                            for page in reader.pages:
                                page.compress_content_streams()
                                writer.add_page(page)
                            out = io.BytesIO()
                            writer.write(out)
                            file_bytes = out.getvalue()
                    except Exception as pdf_err:
                        logger.warning(f"PDF Optimization Bypass for {file.filename}: {pdf_err}")

                url = upload_file(file_bytes, clean_filename, "infrastructure/blueprints")
                model_urls.append(url)
            except Exception as e:
                err_msg = str(e)
                logger.error(f"Storage Sync Error for {file.filename}: {err_msg}")
    
    model_url = ",".join(model_urls) if model_urls else None

    # Prepare project metadata
    project_data = {
        "name": name.upper(),
        "description": description,
        "bim_model_url": model_url
    }
    
    logger.info(f"Registry Synchronizer — Attempting persistence for SITE_{name.upper()}...")
    try:
        result = with_retry(lambda: supabase.table("project").insert(project_data).execute())
        if not result.data:
            logger.error("Registry Rejection: Persistence returned empty data node.")
            raise HTTPException(status_code=500, detail="Failed to initialize project station")
        
        project_node = result.data[0]
        logger.info(f"Registry Success — Node {project_node['id']} established.")

        # Handle site manager assignment logic
        if assignee_id and len(assignee_id.strip()) > 30: # Basic UUID sanity check
            logger.info(f"Assigning Operative {assignee_id} to Site {project_node['id']}...")
            assignment_data = {
                "project_id": project_node["id"],
                "user_id": assignee_id,
                "assigned_role": "project_manager"
            }
            with_retry(lambda: supabase.table("projectassignment").insert(assignment_data).execute())
            logger.info("Assignment Synchronized Successfully.")

        # 2b. Initialize Project Warehouse (Attachments)
        if materials_data:
            try:
                import json
                mats = json.loads(materials_data)
                logger.info(f"Initializing Site Store for {name.upper()} with {len(mats)} resources...")
                inventory_entries = []
                for m in mats:
                    inventory_entries.append({
                        "project_id": project_node["id"],
                        "material_id": m["id"],
                        "unit_cost": float(m["cost"]),
                        "quantity": 0.0, # Start at 0, require requisition
                        "low_stock_threshold": 10.0
                    })
                if inventory_entries:
                    with_retry(lambda: supabase.table("project_inventory").insert(inventory_entries).execute())
                    logger.info("Site Store Registry Established.")
            except Exception as mat_err:
                logger.warning(f"Material Initialization Bypass: {mat_err}")

        api_cache.clear()
        return models.Project(**project_node)
    except Exception as e:
        logger.error(f"Initialization Critical Failure: {str(e)}")
        if "403" in str(e):
            raise HTTPException(status_code=403, detail="Security Rejection: Insufficient operational clearance for registry write.")
        raise HTTPException(status_code=500, detail=f"Database Synchronization Failure: {str(e)}")

# --- Stage/Phase Logic ---

@app.get("/api/v1/projects/{project_id}/stages", response_model=List[models.Stage])
def get_project_stages(project_id: int, user: models.User = Depends(auth.get_current_user)):
    """Fetch all stages/phases for a specific project node."""
    res = with_retry(lambda: supabase.table("stage").select("*").eq("project_id", project_id).order("created_at").execute())
    return [models.Stage(**s) for s in res.data]

@app.post("/api/v1/stages/", response_model=models.Stage)
def create_stage(
    stage: models.Stage,
    user: models.User = Depends(auth.check_role([models.UserRole.admin, models.UserRole.director, models.UserRole.manager]))
):
    """P.M creates a stage and assigns tasks to it."""
    stage_data = serialize_for_supabase(stage.dict(exclude={"id"}))
    res = with_retry(lambda: supabase.table("stage").insert(stage_data).execute())
    if not res.data:
        raise HTTPException(status_code=500, detail="Stage virtualization failed")
    
    api_cache.clear()
    return models.Stage(**res.data[0])

@app.patch("/api/v1/projects/{project_id}", response_model=models.Project)
async def update_project(
    project_id: int,
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    design_id: Optional[int] = Form(None),
    bim_model_url: Optional[str] = Form(None),
    user: models.User = Depends(auth.check_role([models.UserRole.admin, models.UserRole.director]))
):
    """Updates project metadata. Required to attach/detach designs."""
    update_data = {}
    if name is not None: update_data["name"] = name
    if description is not None: update_data["description"] = description
    if design_id is not None: 
        update_data["design_id"] = design_id if design_id > 0 else None
    if bim_model_url is not None: update_data["bim_model_url"] = bim_model_url

    res = with_retry(lambda: supabase.table("project").update(update_data).eq("id", project_id).execute())
    if not res.data:
        raise HTTPException(status_code=404, detail="Project not found")

    api_cache.clear()
    return models.Project(**res.data[0])

@app.post("/api/v1/projects/{project_id}/upload-resource")
async def upload_project_resource(
    project_id: int,
    file: UploadFile = File(...),
    user: models.User = Depends(auth.check_role([models.UserRole.admin, models.UserRole.director]))
):
    """Upload a project resource (PDF/PPT/DOCX) directly to a project."""
    # Validate project exists
    project_res = supabase.table("project").select("*").eq("id", project_id).single().execute()
    if not project_res.data:
        raise HTTPException(status_code=404, detail="Project not found")

    if not file.filename.lower().endswith(('.pdf', '.pptx', '.jpg', '.jpeg', '.png', '.mp4', '.webm', '.ogg')):
        raise HTTPException(status_code=400, detail="Unsupported format")

    try:
        from .services.supabase_client import upload_file
        file_bytes = await file.read()
        model_url = upload_file(file_bytes, file.filename, f"projects/{project_id}/resources")
        
        # Update project record
        supabase.table("project").update({"bim_model_url": model_url}).eq("id", project_id).execute()
        
        api_cache.clear()
        return {"message": "Resource uploaded securely", "url": model_url}
        
    except Exception as e:
        logger.error(f"Resource upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Resource upload failed: {str(e)}")


@app.get("/api/v1/projects/", response_model=list[models.Project])
async def read_projects(
    user: models.User = Depends(auth.get_current_user)
):
    """Return projects filtered by user assignment. Directors/admins see all."""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Directors and admins see all projects
    if user.role in [models.UserRole.director, models.UserRole.admin]:
        result = await async_with_retry(lambda: supabase.table("project").select("*").execute())
        return result.data
    
    # Engineers and managers only see assigned projects
    assignment_res = await async_with_retry(lambda: supabase.table("projectassignment").select("project_id").eq("user_id", user.id).execute())
    project_ids = [a["project_id"] for a in assignment_res.data]
    
    if not project_ids:
        return []
    
    result = await async_with_retry(lambda: supabase.table("project").select("*").in_("id", project_ids).execute())
    return result.data




# --- Project Assignment Endpoints ---

class AssignRequest(BaseModel):
    user_id: str  # UUID
    assigned_role: str = "member"

@app.post("/api/v1/projects/{project_id}/assign")
def assign_user_to_project(
    project_id: int,
    req: AssignRequest,
    user: models.User = Depends(auth.check_role([models.UserRole.admin, models.UserRole.director]))
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
    user: models.User = Depends(auth.check_role([models.UserRole.admin, models.UserRole.director]))
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
    user: models.User = Depends(auth.check_role([models.UserRole.admin, models.UserRole.director]))
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
    user: models.User = Depends(auth.check_role([models.UserRole.admin, models.UserRole.director]))
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
async def get_project_stats(project_id: int, user: models.User = Depends(auth.get_current_user)):
    # 1. Authorization Access Gate
    await check_project_access(user, project_id)
    
    # Fetch project
    project_res = await async_with_retry(lambda: supabase.table("project").select("*").eq("id", project_id).single().execute())
    if not project_res.data:
        raise HTTPException(status_code=404, detail="Project not found")
    project_data = project_res.data
    
    # Fetch work packages
    wp_res = with_retry(lambda: supabase.table("workpackage").select("*").eq("project_id", project_id).execute())
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

@app.get("/api/v1/project-updates/", response_model=List[models.WorkPackage])
async def list_all_project_updates(user: models.User = Depends(auth.get_current_user)):
    """List all work packages/tasks across authorized projects."""
    if user.role in [models.UserRole.admin, models.UserRole.director]:
        result = await async_with_retry(lambda: supabase.table("workpackage").select("*").execute())
        return [models.WorkPackage(**wp) for wp in result.data]
    
    # Isolation: Get assigned pids
    assignment_res = await async_with_retry(lambda: supabase.table("projectassignment").select("project_id").eq("user_id", user.id).execute())
    pids = [a["project_id"] for a in assignment_res.data]
    
    if not pids: return []
    
    result = await async_with_retry(lambda: supabase.table("workpackage").select("*").in_("project_id", pids).execute())
    return [models.WorkPackage(**wp) for wp in result.data]

@app.post("/api/v1/project-updates/")
def create_project_update(
    wp: models.WorkPackage,
    user: models.User = Depends(auth.check_role([models.UserRole.admin, models.UserRole.director, models.UserRole.manager]))
):
    # Defensive: Exclude 'logging_period' as it appears to be missing in the current Supabase schema (PGRST204)
    wp_data = serialize_for_supabase(wp.dict(exclude={"id", "logging_period"}))
    result = with_retry(lambda: supabase.table("workpackage").insert(wp_data).execute())
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to initialize work package")
    
    api_cache.clear()
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
    result = with_retry(lambda: supabase.table("workpackage").select("*").eq("project_id", project_id).execute())
    return result.data

# ============================================================
# STAGE MANAGEMENT ENDPOINTS
# ============================================================

# --- Structural Phase Management (DEPRECATED DUPLICATE REMOVED) ---

@app.patch("/api/v1/stages/{stage_id}", response_model=models.Stage)
def update_stage_status(
    stage_id: int,
    status: models.StatusEnum,
    user: models.User = Depends(auth.check_role([models.UserRole.admin, models.UserRole.director, models.UserRole.manager]))
):
    """Synchronize a structural phase's operational status."""
    result = with_retry(lambda: supabase.table("stage").update({"status": status.value}).eq("id", stage_id).execute())
    if not result.data:
        raise HTTPException(status_code=404, detail="Structural phase not found")
    
    api_cache.clear()
    return models.Stage(**result.data[0])


@app.patch("/api/v1/project-updates/{update_id}", response_model=models.WorkPackage)
def update_project_update(
    update_id: int,
    update_data: WPUpdate,
    user: models.User = Depends(auth.check_role([models.UserRole.admin, models.UserRole.director, models.UserRole.manager, models.UserRole.engineer]))
):
    """Partial update for a project update."""
    data = serialize_for_supabase(update_data.dict(exclude_unset=True))
    result = supabase.table("workpackage").update(data).eq("id", update_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Project update not found")
        
    return models.WorkPackage(**result.data[0])


@app.delete("/api/v1/project-updates/{update_id}")
def delete_project_update(
    update_id: int,
    user: models.User = Depends(auth.check_role([models.UserRole.admin, models.UserRole.director, models.UserRole.manager]))
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
    wps = result.data or []
    
    # Initialize high-visibility kanban structure
    board = {
        "not_started": [],
        "in_progress": [],
        "completed": [],
        "inspected": [],
        "approved": [],
        "blocked": [],
        "critical": []
    }
    
    for wp in wps:
        status = wp.get("status", "not_started")
        if status in board:
            board[status].append(wp)
        else:
            board["not_started"].append(wp)
            
    return board

@app.get("/api/v1/analytics/dashboard")
async def get_dashboard_analytics(
    date: Optional[str] = None,
    user: models.User = Depends(auth.get_current_user)
):
    """
    Centralized High-Fidelity Analytics Aggregator.
    Returns: Projects HUD, Global Site Feed, and Cost Telemetry.
    """
    # 1. Resolve Projects (filtered by user assignment)
    if user.role in [models.UserRole.admin, models.UserRole.director]:
        projects_query = supabase.table("project").select("*, workpackage(*)").order("created_at", desc=True)
        projects_res = await async_with_retry(lambda: projects_query.execute())
        projects = projects_res.data or []
    else:
        # Get assigned project IDs
        assigned_res = await async_with_retry(lambda: supabase.table("projectassignment").select("project_id").eq("user_id", user.id).execute())
        assigned = assigned_res.data or []
        pids = [a["project_id"] for a in assigned]
        if not pids: return {"projects": [], "all_updates": [], "budget_utilization": 0}
        projects_query = supabase.table("project").select("*, workpackage(*)").in_("id", pids).order("created_at", desc=True)
        projects_res = await async_with_retry(lambda: projects_query.execute())
        projects = projects_res.data or []

    # 2. Resolve Site Updates (Feed)
    updates_query = supabase.table("siteupdate").select("*, workpackage!inner(*, project(*))")
    
    if date:
        # Expected format: YYYY-MM-DD
        start_ts = f"{date}T00:00:00Z"
        end_ts = f"{date}T23:59:59Z"
        updates_query = updates_query.gte("timestamp", start_ts).lte("timestamp", end_ts)
        
    # Project Isolation Gate for Feed
    if user.role not in [models.UserRole.admin, models.UserRole.director]:
        updates_query = updates_query.in_("workpackage.project_id", pids)
        
    all_updates_res = await async_with_retry(lambda: updates_query.order("timestamp", desc=True).limit(50).execute())
    all_updates = all_updates_res.data or []

    # 3. Calculate Global Economics and Project Health
    total_budget = total_actual = 0
    now = datetime.now(timezone.utc)
    
    for p in projects:
        # Calculate Economics
        p_wps = p.get("workpackage", [])
        p_total_progress = 0
        for wp in p_wps:
            total_budget += float(wp.get("budget_amount") or 0)
            total_actual += float(wp.get("actual_cost") or 0)
            p_total_progress += int(wp.get("progress_pct") or 0)
        
        # Aggregate stats for the project object
        p["progress_pct"] = p_total_progress / len(p_wps) if p_wps else 0
            
        # Calculate Schedule Status (Daily Target Logic)
        p_status = "on_track"
        overdue_count = 0
        behind_count = 0
        
        if p_wps:
            for wp in p_wps:
                wp_obj = models.WorkPackage(**wp)
                if wp_obj.progress_pct < 100:
                    if wp_obj.due_date and now > wp_obj.due_date:
                        overdue_count += 1
                    elif wp_obj.start_date and wp_obj.due_date:
                        dur = (wp_obj.due_date - wp_obj.start_date).total_seconds()
                        elap = (now - wp_obj.start_date).total_seconds()
                        if dur > 0 and elap > 0:
                            bench = (elap / dur) * 100
                            if wp_obj.progress_pct < bench:
                                behind_count += 1
            
            if overdue_count > 0: p_status = "overdue"
            elif behind_count > 0: p_status = "behind"
        
        p["schedule_status"] = p_status

    # 4. Global Indicators
    global_progress = (sum(p["progress_pct"] for p in projects) / len(projects)) if projects else 0

    return {
        "projects": projects,
        "all_updates": all_updates,
        "budget_utilization": total_actual,
        "global_progress": global_progress
    }


@app.get("/api/v1/projects/{project_id}/performance")
async def get_project_performance(project_id: int):
    """Calculates CPI, SPI, and EAC for a project using CostEngine."""
    try:
        wps_res = with_retry(lambda: supabase.table("workpackage").select("*").eq("project_id", project_id).execute())
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
async def get_gantt_data(project_id: int, user: models.User = Depends(auth.get_current_user)):
    """Returns work packages formatted for Gantt libraries with daily target status."""
    await check_project_access(user, project_id)
    result = await async_with_retry(lambda: supabase.table("workpackage").select("*").eq("project_id", project_id).execute())
    wps = result.data
    
    gantt_tasks = []
    now = datetime.now(timezone.utc)
    
    for wp in wps:
        wp_obj = models.WorkPackage(**wp)
        start = wp_obj.start_date or now
        end = wp_obj.due_date or now
        
        # Calculate Daily Target Status
        status_class = "status-on-track"
        if wp_obj.progress_pct >= 100:
            status_class = "status-completed"
        elif wp_obj.due_date and now > wp_obj.due_date:
            status_class = "status-overdue"
        elif wp_obj.start_date and wp_obj.due_date:
            duration = (wp_obj.due_date - wp_obj.start_date).total_seconds()
            elapsed = (now - wp_obj.start_date).total_seconds()
            if duration > 0 and elapsed > 0:
                benchmark = (elapsed / duration) * 100
                if wp_obj.progress_pct < benchmark:
                    status_class = "status-behind"

        gantt_tasks.append({
            "id": str(wp_obj.id),
            "name": wp_obj.name,
            "start": start.strftime("%Y-%m-%d"),
            "end": end.strftime("%Y-%m-%d"),
            "progress": wp_obj.progress_pct,
            "dependencies": str(wp_obj.parent_id) if wp_obj.parent_id else "",
            "custom_class": status_class,
            "_stage_id": wp_obj.stage_id
        })
    
    return gantt_tasks


# ============================================================
# WORKFLOW & ROLE-BASED ENDPOINTS
# ============================================================

@app.post("/api/v1/project-updates/{update_id}/submit")
@limiter.limit("5/10minutes")
async def submit_phase_update(
    request: Request,
    update_id: int,
    progress: int = Form(...), 
    notes: str = Form(""),
    materials_used: str = Form(""),
    cost_incurred: float = Form(0.0),
    photo: Optional[UploadFile] = File(None),
    user: models.User = Depends(auth.check_role([models.UserRole.admin, models.UserRole.director, models.UserRole.manager, models.UserRole.engineer]))
):
    """Staff submission of work performed with optional photo evidence."""
    status_val = models.StatusEnum.completed if progress >= 100 else models.StatusEnum.in_progress
    
    # 1. Fetch WP for context (project_id)
    wp_current = await async_with_retry(lambda: supabase.table("workpackage").select("project_id, actual_cost").eq("id", update_id).single().execute())
    if not wp_current.data:
        raise HTTPException(status_code=404, detail="Work package not found")
    project_id = wp_current.data["project_id"]
    current_cost = float(wp_current.data.get("actual_cost") or 0)
    new_cost = current_cost + cost_incurred

    photo_url = None
    if photo:
        try:
            from .services.supabase_client import upload_photo
            
            # Sanitize filename for field captures
            clean_filename = re.sub(r'[^a-zA-Z0-9._-]', '_', photo.filename)
            
            file_bytes = await photo.read()
            if len(file_bytes) > MAX_UPLOAD_BYTES:
                raise HTTPException(status_code=413, detail=f"Field capture exceeds operational limit of {MAX_UPLOAD_BYTES/(1024*1024):.0f}MB")
            
            photo_url = upload_photo(file_bytes, clean_filename, project_id, update_id)
        except Exception as e:
            logger.error(f"Submission Photo Upload Failed: {str(e)}")
            # We continue even if photo fails, but ideally we'd log this

    # 3. Update work package
    wp_res = await async_with_retry(lambda: supabase.table("workpackage").update({
        "progress_pct": progress,
        "status": status_val,
        "actual_cost": new_cost
    }).eq("id", update_id).execute())
    
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
    await async_with_retry(lambda: supabase.table("siteupdate").insert(update_data).execute())
    
    api_cache.clear()
    return {"message": "Update submitted successfully", "status": status_val, "photo_url": photo_url}


@app.post("/api/v1/project-updates/{update_id}/verify")
async def verify_phase(update_id: int, user: models.User = Depends(auth.check_role([models.UserRole.admin, models.UserRole.director, models.UserRole.manager]))):
    result = await async_with_retry(lambda: supabase.table("workpackage").update({"status": "inspected", "verified_by_id": user.id}).eq("id", update_id).execute())
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Work package not found")
        
    return {"message": "Work verified by manager", "status": models.StatusEnum.inspected}

@app.post("/api/v1/project-updates/{update_id}/approve")
async def approve_phase(update_id: int, user: models.User = Depends(auth.check_role([models.UserRole.admin, models.UserRole.director]))):
    result = await async_with_retry(lambda: supabase.table("workpackage").update({"status": "approved", "approved_by_id": user.id}).eq("id", update_id).execute())
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Work package not found")
        
    return {"message": "Work approved by director", "status": models.StatusEnum.approved}


# ============================================================
# SITE UPDATES & PHOTO UPLOAD
# ============================================================

@app.get("/api/v1/site-updates/")
async def read_site_updates(
    project_id: Optional[int] = None,
    log_date: Optional[str] = None, # YYYY-MM-DD
    user: models.User = Depends(auth.get_current_user)
):
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
        
    query = supabase.table("siteupdate").select("*, workpackage!inner(*)")
    
    if user.role not in [models.UserRole.admin, models.UserRole.director]:
        # 1. Resolve authorized project context
        assignment_res = await async_with_retry(lambda: supabase.table("projectassignment").select("project_id").eq("user_id", user.id).execute())
        pids = [a["project_id"] for a in (assignment_res.data or [])]
        
        if project_id:
            if project_id not in pids:
                raise HTTPException(status_code=403, detail="Clearance required for this project hub.")
            target_pids = [project_id]
        else:
            if not pids: return []
            target_pids = pids
            
        # 2. Resolve target work packages for these projects
        wp_res = await async_with_retry(lambda: supabase.table("workpackage").select("id").in_("project_id", target_pids).execute())
        wp_ids = [w["id"] for w in (wp_res.data or [])]
        
        if not wp_ids: return []
        query = supabase.table("siteupdate").select("*, workpackage(*)") # Keep workpackage for UI mapping
        query = query.in_("work_package_id", wp_ids)
    else:
        # Admins/Directors handle global or filtered query
        query = supabase.table("siteupdate").select("*, workpackage(*)")
        if project_id:
            # Still need to filter siteupdates by workpackages belonging to the project
            wp_res = await async_with_retry(lambda: supabase.table("workpackage").select("id").eq("project_id", project_id).execute())
            wp_ids = [w["id"] for w in (wp_res.data or [])]
            if not wp_ids: return []
            query = query.in_("work_package_id", wp_ids)
    
    if log_date:
        # Filter for the specific day
        start_ts = f"{log_date}T00:00:00Z"
        end_ts = f"{log_date}T23:59:59Z"
        query = query.gte("timestamp", start_ts).lte("timestamp", end_ts)
        
    result = await async_with_retry(lambda: query.order("timestamp", desc=True).execute())
    return result.data


@app.get("/api/v1/projects/{project_id}/elements")
async def get_project_bim_elements(project_id: int, user: models.User = Depends(auth.get_current_user)):
    """Fetch and parse the linked BIM model for a project to return element metadata."""
    await check_project_access(user, project_id)
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
        logger.error(f"Discovery Error: {str(e)}")
        # If library not yet installed, return empty list for now to prevent UI crash
        return []


@app.post("/api/v1/site-updates/{wp_id}/upload-photo")
@limiter.limit("3/10minutes")
async def upload_site_photo(
    request: Request,
    wp_id: int,
    photos: List[UploadFile] = File(...),
    notes: str = Form(""),
    gps_lat: Optional[float] = Form(None),
    gps_long: Optional[float] = Form(None),
    material_id: Optional[int] = Form(None),
    quantity_used: Optional[float] = Form(None),
    progress: int = Form(50),
    user: models.User = Depends(auth.check_role([
        models.UserRole.engineer, models.UserRole.manager, models.UserRole.director, models.UserRole.admin
    ]))
):
    """Upload site photos and create a site update record."""
    # Validate WP exists and get context
    wp_res = supabase.table("workpackage").select("project_id, actual_cost").eq("id", wp_id).single().execute()
    if not wp_res.data:
        raise HTTPException(status_code=404, detail="Work package not found")
    project_id = wp_res.data["project_id"]
    
    photo_urls = []
    from .services.supabase_client import upload_photo
    import re
    
    for photo in photos:
        try:
            # Mission Critical: Sanitize and Optimize
            clean_filename = re.sub(r'[^a-zA-Z0-9._-]', '_', photo.filename)
            file_bytes = await photo.read()

            # Telemetry Optimization Gate
            if HAS_PILLOW and len(file_bytes) > 1 * 1024 * 1024:
                try:
                    img = Image.open(io.BytesIO(file_bytes))
                    if img.mode != 'RGB': img = img.convert('RGB')
                    img.thumbnail((1920, 1080)) # 1080p Operational Quality
                    out = io.BytesIO()
                    img.save(out, format='JPEG', quality=75, optimize=True)
                    file_bytes = out.getvalue()
                    logger.info(f"Field Telemetry Optimized: {len(file_bytes)/1024:.0f}KB")
                except Exception as comp_err:
                    logger.warning(f"Optimization Bypass for {photo.filename}: {comp_err}")

            url = upload_photo(file_bytes, clean_filename, project_id, wp_id)
            photo_urls.append(url)
        except Exception as e:
            logger.error(f"Multi-file sync failure for {photo.filename}: {e}")
            
    if not photo_urls:
        raise HTTPException(status_code=500, detail="No photos could be synchronized to telemetry junction.")
    
    # Store as comma-separated strictly for this v-tier
    photo_url = ",".join(photo_urls)
    
    # 3. Handle Material Usage and Costing
    mat_summary = ""
    cost_calc = 0.0
    
    if material_id and quantity_used and quantity_used > 0:
        try:
            # Shift: Use Project-Specific Inventory for stock and costing
            inv_res = supabase.table("project_inventory").select("*").eq("project_id", project_id).eq("material_id", material_id).single().execute()
            if inv_res.data:
                inv = inv_res.data
                # Fetch material metadata for Unit/Name
                mat_res = supabase.table("material").select("name, unit").eq("id", material_id).single().execute()
                m_meta = mat_res.data
                
                mat_summary = f"{m_meta['name']}: {quantity_used} {m_meta['unit']}"
                cost_calc = float(inv['unit_cost']) * quantity_used # User Req: Project Manager sets price
                
                # Update Local Project Inventory Stock
                new_project_stock = float(inv['quantity']) - quantity_used
                supabase.table("project_inventory").update({"quantity": new_project_stock}).eq("id", inv['id']).execute()
                
                # Update WP Actual Cost (AC) and Progress locally
                current_ac = float(wp_res.data.get("actual_cost") or 0)
                supabase.table("workpackage").update({
                    "actual_cost": current_ac + cost_calc,
                    "progress_pct": progress
                }).eq("id", wp_id).execute()
        except Exception as e:
            logger.warning(f"Project Material processing warning: {e}")
    else:
        # User Req: Even if no materials used, update the progress from the form
        try:
            supabase.table("workpackage").update({"progress_pct": progress}).eq("id", wp_id).execute()
        except Exception as e:
            logger.warning(f"Standard progress update failure: {e}")

    update_data = {
        "work_package_id": wp_id,
        "submitted_by_id": user.id,
        "notes": notes,
        "photo_url": photo_url,
        "gps_lat": gps_lat,
        "gps_long": gps_long,
        "materials_used": mat_summary,
        "cost_incurred": cost_calc,
        "progress_captured": progress,  # Capture progress snapshot
        "timestamp": datetime.utcnow().isoformat()
    }
    
    result = supabase.table("siteupdate").insert(update_data).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create site update record")
    
    api_cache.clear()
    return {"message": "Photo uploaded successfully", "photo_url": photo_url, "update_id": result.data[0]["id"]}


@app.patch("/api/v1/site-updates/{update_id}")
async def update_site_log(
    update_id: int,
    patch: SiteUpdatePatch,
    user: models.User = Depends(auth.check_role([models.UserRole.admin, models.UserRole.director, models.UserRole.manager]))
):
    """Historical correction of a site log's metrics or notes."""
    data = patch.dict(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="No updates provided")
        
    result = await async_with_retry(lambda: supabase.table("siteupdate").update(data).eq("id", update_id).execute())
    if not result.data:
        raise HTTPException(status_code=404, detail="Log entry not found")
    
    # Global Synchronization: If progress was corrected, propagate to the Work Package
    if "progress_captured" in data:
        updated_log = result.data[0]
        try:
            await async_with_retry(lambda: supabase.table("workpackage")
                .update({"progress_pct": data["progress_captured"]})
                .eq("id", updated_log["work_package_id"])
                .execute())
            logger.info(f"Global progress synced for WP {updated_log['work_package_id']} to {data['progress_captured']}%")
        except Exception as sync_err:
            logger.warning(f"Failed to sync global progress: {sync_err}")
            
    api_cache.clear()
    return {"message": "Site log updated successfully", "data": result.data[0]}


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
async def get_materials(user: models.User = Depends(auth.get_current_user)):
    result = await async_with_retry(lambda: supabase.table("material").select("*").execute())
    return result.data

@app.get("/api/v1/store/projects/{project_id}/inventory", response_model=List[dict])
async def get_project_inventory(project_id: int, user: models.User = Depends(auth.get_current_user)):
    """Fetch localized site store inventory for a specific project."""
    await check_project_access(user, project_id)
    result = await async_with_retry(lambda: supabase.table("project_inventory")
                        .select("*, material:material_id(*)")
                        .eq("project_id", project_id)
                        .execute())
    return result.data

@app.post("/api/v1/store/projects/{project_id}/inventory")
def attach_material_to_project(
    project_id: int, 
    material_data: dict, # {"material_id": int, "unit_cost": float}
    user: models.User = Depends(auth.check_role([models.UserRole.admin, models.UserRole.director, models.UserRole.manager]))
):
    """Attach a new resource capability to a site station."""
    entry = {
        "project_id": project_id,
        "material_id": material_data["material_id"],
        "unit_cost": float(material_data["unit_cost"]),
        "quantity": 0.0,
        "low_stock_threshold": 10.0
    }
    result = with_retry(lambda: supabase.table("project_inventory").insert(entry).execute())
    return result.data[0]

@app.patch("/api/v1/store/projects/{project_id}/inventory/{material_id}")
def reconcile_site_stock(
    project_id: int,
    material_id: int,
    stock_data: dict, # {"quantity": float, "unit_cost": float}
    user: models.User = Depends(auth.check_role([models.UserRole.admin, models.UserRole.director, models.UserRole.manager]))
):
    """Manual reconciliation of physical site stock levels."""
    update_node = {}
    if "quantity" in stock_data: update_node["quantity"] = float(stock_data["quantity"])
    if "unit_cost" in stock_data: update_node["unit_cost"] = float(stock_data["unit_cost"])
    
    result = with_retry(lambda: supabase.table("project_inventory")
                        .update(update_node)
                        .eq("project_id", project_id)
                        .eq("material_id", material_id)
                        .execute())
    return result.data[0]

@app.delete("/api/v1/store/projects/{project_id}/inventory/{material_id}")
def purge_site_material(
    project_id: int,
    material_id: int,
    user: models.User = Depends(auth.check_role([models.UserRole.admin, models.UserRole.director, models.UserRole.manager]))
):
    """Purge a resource Capability from a site station."""
    with_retry(lambda: supabase.table("project_inventory")
                .delete()
                .eq("project_id", project_id)
                .eq("material_id", material_id)
                .execute())
    return {"message": "Resource purged from site registry"}

@app.get("/api/v1/store/requests/{request_id}/print")
def print_requisition(request_id: int, user: models.User = Depends(auth.get_current_user)):
    """Generate and return a formal PDF requisition form."""
    try:
        # Load data for the form
        req_res = supabase.table("material_request").select("*").eq("id", request_id).single().execute()
        if not req_res.data: raise HTTPException(404, "Request not found")
        req = req_res.data
        
        proj_res = supabase.table("project").select("*").eq("id", req["project_id"]).single().execute()
        mat_res = supabase.table("material").select("*").eq("id", req["material_id"]).single().execute()
        user_res = supabase.table("user").select("*").eq("id", req["requester_id"]).single().execute()
        
        from .services.report_generator import ReportGenerator
        gen = ReportGenerator(proj_res.data["name"])
        pdf_url = gen.generate_requisition_pdf(req, proj_res.data, mat_res.data, user_res.data)
        
        return {"pdf_url": pdf_url}
    except Exception as e:
        logger.error(f"PDF Generation Error: {e}")
        raise HTTPException(500, detail="Failed to synthesize formal document")

@app.post("/api/v1/store/materials", response_model=models.Material)
def create_material(
    material: models.Material,
    user: models.User = Depends(auth.check_role([models.UserRole.admin, models.UserRole.director, models.UserRole.manager]))
):
    mat_data = serialize_for_supabase(material.dict(exclude={"id"}))
    result = with_retry(lambda: supabase.table("material").insert(mat_data).execute())
    return models.Material(**result.data[0])


@app.patch("/api/v1/store/materials/{material_id}", response_model=models.Material)
def update_material(
    material_id: int,
    material_data: dict, # Support raw partial JSON
    user: models.User = Depends(auth.check_role([models.UserRole.admin, models.UserRole.director, models.UserRole.manager]))
):
    # Ensure decimals/floats converted if present
    if "unit_cost" in material_data:
        material_data["unit_cost"] = float(material_data["unit_cost"])
    if "current_stock" in material_data:
        material_data["current_stock"] = float(material_data["current_stock"])
    if "low_stock_threshold" in material_data:
        material_data["low_stock_threshold"] = float(material_data["low_stock_threshold"])
        
    # Clean up any id sent in body
    if "id" in material_data: del material_data["id"]

    result = with_retry(lambda: supabase.table("material").update(material_data).eq("id", material_id).execute())
    if not result.data:
        raise HTTPException(status_code=404, detail="Material not found")
            
    return models.Material(**result.data[0])

@app.delete("/api/v1/store/materials/{material_id}")
def delete_material(
    material_id: int,
    user: models.User = Depends(auth.check_role([models.UserRole.admin, models.UserRole.director]))
):
    result = with_retry(lambda: supabase.table("material").delete().eq("id", material_id).execute())
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
    result = with_retry(lambda: query.order("request_date", desc=True).execute())
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
    
    result = with_retry(lambda: supabase.table("material_request").insert(req_data).execute())
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
    req_res = with_retry(lambda: supabase.table("material_request").select("*").eq("id", request_id).single().execute())
    if not req_res.data:
        raise HTTPException(status_code=404, detail="Request not found")
    mat_req = req_res.data
    
    # 2. If issuing, transfer stock from Global to Site Warehouse
    if status == models.MaterialRequestStatus.issued and mat_req["status"] != models.MaterialRequestStatus.issued:
        # Check Global Stock
        mat_res = with_retry(lambda: supabase.table("material").select("*").eq("id", mat_req["material_id"]).single().execute())
        if not mat_res.data or mat_res.data["current_stock"] < mat_req["quantity_requested"]:
            raise HTTPException(status_code=400, detail="Insufficient Global Stock")
            
        # Deduct Global
        new_global_stock = mat_res.data["current_stock"] - mat_req["quantity_requested"]
        with_retry(lambda: supabase.table("material").update({"current_stock": new_global_stock}).eq("id", mat_req["material_id"]).execute())

        # Add to Project-Specific Inventory (Site Warehouse)
        # 1. Check if record exists
        inv_check = supabase.table("project_inventory").select("*").eq("project_id", mat_req["project_id"]).eq("material_id", mat_req["material_id"]).execute()
        
        if inv_check.data:
            new_site_stock = inv_check.data[0]["quantity"] + mat_req["quantity_requested"]
            supabase.table("project_inventory").update({"quantity": new_site_stock}).eq("id", inv_check.data[0]["id"]).execute()
        else:
            # Automatic "Attach" if not already managed? 
            # We stick to the PM attachment rule, but for Issuance we'll auto-initialize if missing to avoid logistics failure
            new_entry = {
                "project_id": mat_req["project_id"],
                "material_id": mat_req["material_id"],
                "quantity": mat_req["quantity_requested"],
                "unit_cost": mat_res.data["unit_cost"], # Default to global if not attached
                "low_stock_threshold": 10.0
            }
            supabase.table("project_inventory").insert(new_entry).execute()
    
    with_retry(lambda: supabase.table("material_request").update({"status": status.value}).eq("id", request_id).execute())
    return {"message": f"Request {status.value} successfully"}


@app.delete("/api/v1/store/request/{request_id}")
def delete_material_request(
    request_id: int,
    user: models.User = Depends(auth.check_role([models.UserRole.admin, models.UserRole.director, models.UserRole.manager]))
):
    result = supabase.table("material_request").delete().eq("id", request_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Request not found")
    return {"message": "Material request deleted successfully"}



