# graph_client.py
# ============================================================
# Microsoft Graph Client (App-Only)
#
# Purpose:
# - Use Entra ID App Registration (client credential flow)
# - Call Microsoft Graph to:
#   - Create user (onboarding)
#   - Check if UPN exists (UPN uniqueness)
#   - Find user by employeeId (offboarding)
#   - Disable user account
#   - Revoke sign-in sessions
#   - Remove user from all groups
#
# Required ENV vars (from .env in the SAME folder as this file):
# - PROV_TENANT_ID
# - PROV_CLIENT_ID
# - PROV_CLIENT_SECRET
#
# Notes:
# - Uses Graph v1.0 endpoint
# - Uses msal acquire_token_for_client with .default scope
# - Has simple request helpers: graph_get / graph_post / graph_patch / graph_delete
# ============================================================

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional

import requests
import msal
from dotenv import load_dotenv

GRAPH = "https://graph.microsoft.com/v1.0"
SCOPE = ["https://graph.microsoft.com/.default"]

# Load .env from the same folder as this file
ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=ENV_PATH, override=True)


# ------------------------------------------------------------
# ENV helpers
# ------------------------------------------------------------
def _must(name: str) -> str:
    """
    Read required env var.
    If missing, raise a clear error that shows where we loaded .env from.
    """
    val = os.getenv(name)
    if not val or not val.strip():
        raise RuntimeError(
            f"Missing env var: {name}. "
            f"Loaded env path: {ENV_PATH}. "
            f"cwd: {os.getcwd()}"
        )
    return val.strip()


# ------------------------------------------------------------
# Token acquisition (client credential flow)
# ------------------------------------------------------------
def get_app_token() -> str:
    """
    Get an app-only access token for Microsoft Graph.
    Uses PROV_* env vars and the '.default' scope.
    """
    tenant_id = _must("PROV_TENANT_ID")
    client_id = _must("PROV_CLIENT_ID")
    client_secret = _must("PROV_CLIENT_SECRET")

    authority = f"https://login.microsoftonline.com/{tenant_id}"

    app = msal.ConfidentialClientApplication(
        client_id=client_id,
        client_credential=client_secret,
        authority=authority,
    )

    result = app.acquire_token_for_client(scopes=SCOPE)
    if "access_token" not in result:
        # This contains useful reason/error_description from MSAL
        raise RuntimeError(f"Provisioning token error: {result}")

    return result["access_token"]


# ------------------------------------------------------------
# HTTP helpers
# ------------------------------------------------------------
def _headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def _raise_graph_error(method: str, url: str, r: requests.Response) -> None:
    """
    Raise a readable error from Graph response.
    Keeps the response text (Graph usually returns JSON with a helpful message).
    """
    try:
        body = r.text
    except Exception:
        body = "<no body>"
    raise RuntimeError(f"Graph {method} failed {r.status_code}: {body}")


def graph_get(path: str) -> Dict[str, Any]:
    """
    GET /v1.0{path}
    Returns parsed JSON.
    """
    token = get_app_token()
    url = f"{GRAPH}{path}"
    r = requests.get(url, headers=_headers(token), timeout=30)
    if r.status_code != 200:
        _raise_graph_error("GET", url, r)
    return r.json()


def graph_post(path: str, body: Dict[str, Any]) -> Dict[str, Any]:
    """
    POST /v1.0{path}
    Returns JSON if present, else {}.
    """
    token = get_app_token()
    url = f"{GRAPH}{path}"
    r = requests.post(url, headers=_headers(token), data=json.dumps(body), timeout=30)
    if r.status_code not in (200, 201, 204):
        _raise_graph_error("POST", url, r)
    return r.json() if r.text else {}


def graph_patch(path: str, body: Dict[str, Any]) -> None:
    """
    PATCH /v1.0{path}
    Graph PATCH often returns 204 No Content on success.
    """
    token = get_app_token()
    url = f"{GRAPH}{path}"
    r = requests.patch(url, headers=_headers(token), data=json.dumps(body), timeout=30)
    if r.status_code != 204:
        _raise_graph_error("PATCH", url, r)


def graph_delete(path: str) -> None:
    """
    DELETE /v1.0{path}
    Returns 204 No Content on success.
    """
    token = get_app_token()
    url = f"{GRAPH}{path}"
    r = requests.delete(url, headers=_headers(token), timeout=30)
    if r.status_code != 204:
        _raise_graph_error("DELETE", url, r)


# ------------------------------------------------------------
# Onboarding helpers
# ------------------------------------------------------------
def user_exists_by_upn(upn: str) -> bool:
    """
    Check if a user exists by UPN (userPrincipalName).
    Used to generate unique UPN during onboarding.
    """
    safe = (upn or "").replace("'", "''")  # simple escaping for OData filter
    data = graph_get(f"/users?$filter=userPrincipalName eq '{safe}'&$select=id&$top=1")
    return bool(data.get("value"))


def create_user(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a new Entra ID user with Graph POST /users.
    Returns the created user object from Graph (JSON).
    """
    token = get_app_token()
    url = f"{GRAPH}/users"
    r = requests.post(url, headers=_headers(token), data=json.dumps(payload), timeout=30)
    if r.status_code not in (200, 201):
        _raise_graph_error("POST", url, r)
    return r.json()


# ------------------------------------------------------------
# Check Dublicate Username Helper
# ------------------------------------------------------------

def clean_name(s: str) -> str:
    return (s or "").strip()

def short_actor(actor: str) -> str:
    # if it is already a full display name, keep it
    if "@" not in actor and " " in actor:
        return actor
    # if it is a UPN/email, show left part
    return (actor or "").split("@")[0]


# ------------------------------------------------------------
# Offboarding helpers
# ------------------------------------------------------------
def find_user_by_employee_id(employee_number: int) -> Optional[Dict[str, Any]]:
    """
    Find a user by employeeId (we set employeeId = employee_number during onboarding).
    Returns a small user dict or None if not found.
    """
    emp = str(employee_number)
    path = (
        "/users"
        f"?$filter=employeeId eq '{emp}'"
        "&$select=id,userPrincipalName,accountEnabled,employeeId"
        "&$top=1"
    )
    data = graph_get(path)
    items = data.get("value", [])
    return items[0] if items else None


def disable_user(user_id: str) -> None:
    """Disable an account (accountEnabled=False)."""
    graph_patch(f"/users/{user_id}", {"accountEnabled": False})


def revoke_signin_sessions(user_id: str) -> None:
    """
    Revoke sign-in sessions (forces re-auth).
    Graph returns 204 or 200 depending on tenant behavior.
    """
    graph_post(f"/users/{user_id}/revokeSignInSessions", {})


def remove_user_from_all_groups(user_id: str) -> int:
    """
    Remove user from all groups they are member of.
    Returns number of groups removed.

    NOTE:
    - /memberOf can be paged (nextLink). This version handles only first page.
      For large tenants, we should add pagination later.
    """
    token = get_app_token()
    headers = _headers(token)

    # List memberships
    r = requests.get(f"{GRAPH}/users/{user_id}/memberOf", headers=headers, timeout=30)
    if r.status_code != 200:
        _raise_graph_error("GET", f"{GRAPH}/users/{user_id}/memberOf", r)

    items = r.json().get("value", [])
    groups = [g for g in items if g.get("@odata.type") == "#microsoft.graph.group"]

    # Remove from each group
    count = 0
    for g in groups:
        gid = g["id"]
        dr = requests.delete(
            f"{GRAPH}/groups/{gid}/members/{user_id}/$ref",
            headers=headers,
            timeout=30,
        )
        if dr.status_code != 204:
            _raise_graph_error("DELETE", f"{GRAPH}/groups/{gid}/members/{user_id}/$ref", dr)
        count += 1

    return count
