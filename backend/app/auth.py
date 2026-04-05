from fastapi import Depends, HTTPException, status, Request, Response
from typing import Optional, List
from .database import supabase
from . import models

from cachetools import TTLCache
auth_cache = TTLCache(maxsize=500, ttl=300)

async def get_current_user(request: Request, response: Response = None) -> Optional[models.User]:
    """Get the currently authenticated user from Supabase Auth."""
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
                    response.set_cookie(key="access_token", value=f"Bearer {token}", httponly=True, max_age=expires_in, path="/")
                    response.set_cookie(key="refresh_token", value=auth_response.session.refresh_token, httponly=True, max_age=86400*7, path="/")
        except Exception as e:
            pass

    if not token:
        return None

    if token in auth_cache:
        return auth_cache[token]

    try:
        # Validate the token with Supabase
        auth_response = supabase.auth.get_user(token)
        if not auth_response or not auth_response.user:
            return None
        
        # Fetch role and extra data from our public.user table
        user_id = auth_response.user.id
        result = supabase.table("user").select("*").eq("id", user_id).single().execute()
        
        if not result.data:
            return None
            
        user = models.User(**result.data)
        auth_cache[token] = user
        return user
        
    except Exception as e:
        print(f"Auth error: {str(e)}")
        return None


def check_role(roles: list[models.UserRole]):
    async def role_checker(user: models.User = Depends(get_current_user)):
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Not enough permissions")
        return user
    return role_checker
