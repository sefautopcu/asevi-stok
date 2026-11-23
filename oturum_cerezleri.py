"""Session-cookie operations with Streamlit and browser manager injected."""
import datetime


def cerez_oku(anahtar, streamlit_api, cerez_kontrol):
    try:
        if hasattr(streamlit_api, "context") and hasattr(streamlit_api.context, "cookies"):
            deger = streamlit_api.context.cookies.get(anahtar)
            if deger:
                return str(deger)
    except Exception:
        pass
    if cerez_kontrol is None:
        return ""
    try:
        return str(cerez_kontrol.get(anahtar) or "")
    except Exception:
        return ""


def cerez_yaz(deger, anahtar, max_age, cerez_kontrol, log, simdi_fn=None):
    if cerez_kontrol is None:
        return
    if simdi_fn is None:
        simdi_fn = datetime.datetime.now
    try:
        bitis = simdi_fn() + datetime.timedelta(seconds=max_age)
        cerez_kontrol.set(anahtar, deger, expires_at=bitis, path="/")
    except Exception as exc:
        log.error(f"Çerez yazma hatası: {exc}")


def cerez_sil(anahtar, cerez_kontrol):
    if cerez_kontrol is None:
        return
    try:
        cerez_kontrol.remove(anahtar)
    except Exception:
        try:
            cerez_kontrol.delete(anahtar)
        except Exception:
            pass
