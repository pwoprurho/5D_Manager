from supabase import create_client, Client
from .config import settings

# Lazy-initialized Supabase client.
# This avoids a hard crash at import time if Supabase is temporarily
# unreachable (e.g. paused free-tier project, network blip).

_supabase_client: Client | None = None


def get_supabase() -> Client:
    """Return (and lazily create) the Supabase client."""
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_KEY,
        )
    return _supabase_client


class _LazySupabase:
    """Proxy that defers create_client() until first attribute access."""

    def __getattr__(self, name):
        return getattr(get_supabase(), name)


# Module-level reference used everywhere via `from .database import supabase`
supabase: Client = _LazySupabase()  # type: ignore[assignment]
