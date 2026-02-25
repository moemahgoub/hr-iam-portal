import os

def must_get(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return v

TENANT_ID = must_get("TENANT_ID")
CLIENT_ID = must_get("CLIENT_ID")
CLIENT_SECRET = must_get("CLIENT_SECRET")
TENANT_DOMAIN = must_get("TENANT_DOMAIN")
DATABASE_PATH = os.getenv("DATABASE_PATH", "hr_portal.db")

# Must match your callback route in main.py
REDIRECT_URI = must_get("REDIRECT_URI")

# Strong random string, keep only in env
SESSION_SECRET = must_get("SESSION_SECRET")

# Optional: scopes for Graph / login
GRAPH_SCOPES = os.getenv("GRAPH_SCOPES", "User.Read")