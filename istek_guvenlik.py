"""Pure request-header parsing for login rate-limit identity."""


def istemci_ip_ayikla(basliklar):
    """Return (rate-limit IP, truncated full X-Forwarded-For) as app behavior does."""
    xff = str(basliklar.get("X-Forwarded-For", "") or "")
    if xff:
        ip = xff.split(",")[-1].strip()
    else:
        ip = str(basliklar.get("X-Real-Ip", "") or "").strip()
    return (ip or "bilinmiyor"), xff[:200]
