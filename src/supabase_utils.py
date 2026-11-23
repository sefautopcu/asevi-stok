"""Pure helpers for Supabase request headers and API-key role inspection."""
import base64
import json


def supabase_basliklar(anahtar, ekstra=None):
    """Build the headers currently used by the app's Supabase REST calls."""
    headers = {"apikey": anahtar}
    if not str(anahtar).startswith("sb_"):
        headers["Authorization"] = f"Bearer {anahtar}"
    if ekstra:
        headers.update(ekstra)
    return headers


def supabase_anahtar_rolu(anahtar):
    """Return anon/service_role from modern keys or a JWT role claim."""
    key = str(anahtar or "")
    if key.startswith("sb_publishable"):
        return "anon"
    if key.startswith("sb_secret"):
        return "service_role"
    try:
        payload = key.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload))
        return str(claims.get("role", "bilinmiyor"))
    except Exception:
        return "bilinmiyor"
