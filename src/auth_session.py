# src/auth_session.py
import time
import secrets
import hashlib
import datetime
import json
import streamlit as st
import requests

from src.supabase_db import _atomik_dict_guncelle, _supa_basliklar, SUPABASE_URL
from src.cekirdek import sifre_hashle_yeni

OTURUM_SURESI_SN = 8 * 60 * 60
MAKS_HATALI_GIRIS = 3
KILIT_SURESI_SN = 30
IP_MAKS_HATALI_GIRIS = 3
IP_KILIT_SURESI_SN = 30
COOKIE_ADI = "aziziye_oturum"
OTURUM_DOGRULAMA_ARALIGI_SN = 60

def _secret_oku(anahtar, varsayilan=""):
    try:
        return st.secrets.get(anahtar, varsayilan)
    except Exception:
        return varsayilan

def bosta_kalma_suresi_sn():
    try:
        dk = int(str(_secret_oku("BOSTA_KALMA_DAKIKA", 30)))
    except Exception:
        dk = 30
    return max(5, min(dk, 480)) * 60

try:
    import extra_streamlit_components as stx
    cerez_kontrol = stx.CookieManager(key="aziziye_cerez")
except Exception:
    cerez_kontrol = None

def cerez_oku(anahtar=COOKIE_ADI):
    try:
        if hasattr(st, "context") and hasattr(st.context, "cookies"):
            deger = st.context.cookies.get(anahtar)
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

def cerez_yaz(deger, anahtar=COOKIE_ADI, max_age=OTURUM_SURESI_SN):
    if cerez_kontrol is None:
        return
    try:
        bitis = datetime.datetime.now() + datetime.timedelta(seconds=max_age)
        cerez_kontrol.set(anahtar, deger, expires_at=bitis, path="/")
    except Exception:
        pass

def cerez_sil(anahtar=COOKIE_ADI):
    if cerez_kontrol is None:
        return
    try:
        cerez_kontrol.remove(anahtar)
    except Exception:
        try:
            cerez_kontrol.delete(anahtar)
        except Exception:
            pass

def istemci_ip_bilgisi():
    try:
        basliklar = st.context.headers
        xff = str(basliklar.get("X-Forwarded-For", "") or "")
        if xff:
            ip = xff.split(",")[-1].strip()
        else:
            ip = str(basliklar.get("X-Real-Ip", "") or "").strip()
        return (ip or "bilinmiyor"), xff[:200]
    except Exception:
        return "bilinmiyor", ""

def giris_logla(kullanici, durum):
    if not SUPABASE_URL:
        return
    ip, xff = istemci_ip_bilgisi()
    try:
        requests.post(
            f"{SUPABASE_URL}/rest/v1/giris_kayitlari",
            headers=_supa_basliklar({"Content-Type": "application/json", "Prefer": "return=minimal"}),
            json={
                "kullanici": str(kullanici)[:50],
                "durum": str(durum)[:80],
                "ip": ip,
                "xff": xff
            },
            timeout=5
        )
    except Exception:
        pass

def _token_hashle(token):
    return hashlib.sha256(str(token).encode("utf-8")).hexdigest()

def oturum_olustur(kullanici_adi):
    token = secrets.token_urlsafe(32)
    simdi = time.time()
    bitis = simdi + OTURUM_SURESI_SN

    def _ekle(oturumlar):
        oturumlar = {h: o for h, o in oturumlar.items() if o.get("bitis", 0) > simdi}
        oturumlar[_token_hashle(token)] = {"kullanici": kullanici_adi, "bitis": bitis}
        return oturumlar

    durum, sonuc = _atomik_dict_guncelle("aktif_oturumlar", _ekle)
    if durum != "ok":
        # UI'a bağımlılığı kaldırmak için hata fırlatıyoruz. app_runtime içinde yakalayacağız.
        raise Exception(f"oturum oluşturulamadı ({sonuc})")
    return token, bitis

def oturum_dogrula(token):
    if not token:
        return None
    from src.supabase_db import _supabase_ham_oku
    durum, oturumlar = _supabase_ham_oku("aktif_oturumlar")
    if durum != "ok" or not isinstance(oturumlar, dict):
        return None
    kayit = oturumlar.get(_token_hashle(token))
    if kayit and kayit.get("bitis", 0) > time.time():
        return kayit
    return None

def oturum_sil(token):
    if not token:
        return
    h = _token_hashle(token)
    def _sil(oturumlar):
        oturumlar.pop(h, None)
        return oturumlar
    _atomik_dict_guncelle("aktif_oturumlar", _sil)

def kullanici_oturumlarini_kapat(kullanici, haric_token=None):
    haric = _token_hashle(haric_token) if haric_token else None
    def _filtrele(oturumlar):
        return {h: o for h, o in oturumlar.items() if o.get("kullanici") != kullanici or h == haric}
    _atomik_dict_guncelle("aktif_oturumlar", _filtrele)

def giris_kilit_kalan(anahtar):
    from src.supabase_db import _supabase_ham_oku
    durum, kayitlar = _supabase_ham_oku("giris_denemeleri")
    if durum != "ok" or not isinstance(kayitlar, dict):
        return 0
    return max(0, int(kayitlar.get(anahtar, {}).get("kilit_bitis", 0) - time.time()))

def hatali_giris_kaydet(anahtar, maks=MAKS_HATALI_GIRIS, taban_sn=KILIT_SURESI_SN):
    simdi = time.time()
    sonuc = {"kalan": maks, "kilit": False}
    def _guncelle(kayitlar):
        kayitlar = {k: v for k, v in kayitlar.items() if v.get("kilit_bitis", 0) > simdi or simdi - v.get("son", 0) < 3600}
        kayit = kayitlar.get(anahtar, {"sayi": 0, "kilit_sayisi": 0, "kilit_bitis": 0, "son": 0})
        if simdi - kayit.get("son", 0) > 3600:
            kayit["sayi"] = 0
            kayit["kilit_sayisi"] = 0
        kayit["sayi"] = kayit.get("sayi", 0) + 1
        kayit["son"] = simdi
        if kayit["sayi"] >= maks:
            kayit["kilit_sayisi"] = kayit.get("kilit_sayisi", 0) + 1
            sure = min(taban_sn * (2 ** (kayit["kilit_sayisi"] - 1)), 900)
            kayit["kilit_bitis"] = simdi + sure
            kayit["sayi"] = 0
            sonuc["kilit"] = True
        sonuc["kalan"] = max(maks - kayit["sayi"], 0)
        kayitlar[anahtar] = kayit
        return kayitlar
    durum, _ = _atomik_dict_guncelle("giris_denemeleri", _guncelle)
    if durum != "ok":
        return 0, True
    return sonuc["kalan"], sonuc["kilit"]

def giris_denemesini_sifirla(anahtar=None, *ek_anahtarlar):
    if anahtar is None:
        _atomik_dict_guncelle("giris_denemeleri", lambda _: {})
        return
    anahtarlar = (anahtar,) + ek_anahtarlar
    from src.cekirdek import giris_sayaclarini_sifirla
    _atomik_dict_guncelle("giris_denemeleri", lambda kayitlar: giris_sayaclarini_sifirla(kayitlar, anahtarlar))
