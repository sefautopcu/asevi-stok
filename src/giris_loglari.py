"""Supabase audit-log request orchestration, with app dependencies injected."""


def giris_logu_kaydet(url, api_key, kullanici, durum, istemci_ip, basliklar_fn, post_fn, log):
    """Send a bounded login audit record; never include passwords or tokens."""
    if not url or not api_key:
        return
    ip, xff = istemci_ip()
    try:
        post_fn(
            f"{url}/rest/v1/giris_kayitlari",
            headers=basliklar_fn({"Content-Type": "application/json", "Prefer": "return=minimal"}),
            json={
                "kullanici": str(kullanici)[:50],
                "durum": str(durum)[:80],
                "ip": ip,
                "xff": xff,
            },
            timeout=5,
        )
    except Exception as exc:
        log.error(f"Log kaydı hatası: {exc}")
