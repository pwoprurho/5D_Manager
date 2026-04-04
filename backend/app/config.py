from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./test.db"
    SECRET_KEY: str  # Required — no default, must be set in .env
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Supabase Configuration
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    SUPABASE_SERVICE_KEY: str = ""
    SUPABASE_STORAGE_BUCKET: str = "site-photos"
    GEMINI_API_KEY: Optional[str] = None
    
    @property
    def gemini_api_keys(self) -> list[str]:
        keys = []
        if self.GEMINI_API_KEY and self.GEMINI_API_KEY != "your_key_here":
            keys.extend([k.strip() for k in self.GEMINI_API_KEY.split(",") if k.strip()])
            
        import os
        from dotenv import dotenv_values
        
        # Load directly from .env to bypass Pydantic static typing
        env_vars = dotenv_values(".env")
        for k, v in env_vars.items():
            if (k.startswith("GEMINI_API_KEY_") or k.startswith("GEMINI_KEY_")) and isinstance(v, str) and v and v != "your_key_here":
                keys.append(v)
                
        for k, v in os.environ.items():
            if (k.startswith("GEMINI_API_KEY_") or k.startswith("GEMINI_KEY_")) and isinstance(v, str) and v and v != "your_key_here":
                keys.append(v)
                
        return list(set(keys))

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
