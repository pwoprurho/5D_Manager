from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions
from .config import settings
import httpx
import time
import logging

# ============================================================
# SUPABASE CLIENT — STABILIZED CONFIGURATION
# ============================================================

logger = logging.getLogger("vinicius.db")

_supabase_client: Client | None = None

def get_supabase() -> Client:
    """Return (and lazily create) the Supabase client."""
    global _supabase_client
    if _supabase_client is None:
        url = settings.SUPABASE_URL
        key = settings.SUPABASE_SERVICE_KEY
        
        if not url or not key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        
        # Standard initialization to prevent attribute masking
        _supabase_client = create_client(url, key)
        logger.info(f"Supabase client initialized: {url[:40]}...")
    return _supabase_client


def reset_supabase() -> Client:
    """Force-recreate the Supabase client (clears stale connections)."""
    global _supabase_client
    _supabase_client = None
    return get_supabase()


def with_retry(fn, retries=2, delay=0.5):
    """Execute a Supabase operation with automatic retry on connection drops.
    
    Catches: HTTP/2 disconnects, DNS failures, SSL timeouts.
    Usage: result = with_retry(lambda: supabase.table("x").select("*").execute())
    """
    last_exc = None
    for attempt in range(retries + 1):
        try:
            return fn()
        except Exception as e:
            err_str = str(e).lower()
            # Catch all known transient connection errors
            is_transient = any(phrase in err_str for phrase in [
                "server disconnected",
                "remoteerror",
                "remoteprotocolerror",
                "getaddrinfo failed",
                "handshake operation timed out",
                "_ssl.c",
                "connection reset",
                "connection refused",
                "timed out",
                "temporary failure in name resolution",
            ])
            if is_transient:
                last_exc = e
                logger.warning(f"Connection error (attempt {attempt+1}/{retries+1}): {type(e).__name__}: {e}")
                reset_supabase()
                if attempt < retries:
                    time.sleep(delay * (attempt + 1))  # Progressive backoff
                continue
            raise  # Non-connection error, don't retry
    raise last_exc


class _LazySupabase:
    """Proxy that defers create_client() until first attribute access."""

    def __getattr__(self, name):
        return getattr(get_supabase(), name)


# Module-level reference used everywhere via `from .database import supabase`
supabase: Client = _LazySupabase()  # type: ignore[assignment]
