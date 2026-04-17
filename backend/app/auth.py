from fastapi import Depends, HTTPException, status, Request, Response
from typing import Optional, List
import logging
from .database import supabase, with_retry
from . import models

logger = logging.getLogger("vinicius.auth")

from cachetools import TTLCache
auth_cache = TTLCache(maxsize=500, ttl=300)

async def get_current_user(request: Request, response: Response = None) -> Optional[models.User]:
    """Get the currently authenticated user from Supabase Auth.
    
    Zero-trust: Supabase Auth is the SINGLE source of truth.
    Role and username are read from user_metadata (set during registration).
    The public.user table is optional enrichment, never a gate.
    """
    token = request.cookies.get("access_token")
    refresh = request.cookies.get("refresh_token")
    
    if token and token.startswith("Bearer "):
        token = token[7:]
    
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]

    # Auto-refresh check if token is missing
    if not token and refresh:
        try:
            auth_response = supabase.auth.refresh_session(refresh)
            if auth_response and auth_response.session:
                token = auth_response.session.access_token
                expires_in = getattr(auth_response.session, 'expires_in', 3600)
                if response:
                    response.set_cookie(key="access_token", value=f"Bearer {token}", httponly=True, max_age=expires_in, path="/", samesite="strict", secure=True)
                    response.set_cookie(key="refresh_token", value=auth_response.session.refresh_token, httponly=True, max_age=86400*7, path="/", samesite="strict", secure=True)
        except Exception as e:
            pass

    if not token:
        return None

    if token in auth_cache:
        return auth_cache[token]

    try:
        # Step 1: Validate the token with Supabase Auth (the ONLY trust boundary)
        auth_response = with_retry(lambda: supabase.auth.get_user(token))
        if not auth_response or not auth_response.user:
            return None

        auth_user = auth_response.user
        user_id = auth_user.id
        email = auth_user.email or ""
        
        # Step 2: Extract role and username from user_metadata (primary source)
        meta = auth_user.user_metadata or {}
        username = meta.get("username", email.split("@")[0])
        role = meta.get("role", "engineer")

        # Step 3: Try to enrich from public.user table (optional, non-blocking)
        try:
            result = with_retry(lambda: supabase.table("user").select("*").eq("id", user_id).maybe_single().execute())
            if result and result.data:
                # Public table exists and has data — use it for role/username
                username = result.data.get("username", username)
                role = result.data.get("role", role)
                is_active = result.data.get("is_active", True)
                
                if not is_active:
                    return None  # Account disabled
            else:
                # Public table row missing — auto-sync from auth metadata
                try:
                    supabase.table("user").upsert({
                        "id": user_id,
                        "email": email,
                        "username": username,
                        "role": role,
                        "is_active": True
                    }).execute()
                except Exception:
                    pass  # Non-critical, don't block auth
        except Exception:
            pass  # Public table unavailable — auth still works via metadata

        user = models.User(
            id=user_id,
            username=username,
            email=email,
            role=role,
            is_active=True
        )
        auth_cache[token] = user
        return user
        
    except Exception as e:
        logger.error(f"Auth error: {str(e)}")
        return None


def check_role(roles: list[models.UserRole]):
    async def role_checker(user: models.User = Depends(get_current_user)):
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Not enough permissions")
        return user
    return role_checker
