# src/supabase_db.py
import base64
import json
import time
import requests
import streamlit as st

# Secret okuma yardımcısı
def _secret_oku(anahtar, varsayilan=""):
    try:
        return st.secrets.get(anahtar, varsayilan)
    except Exception:
        return varsayilan

# Global değişkenler (app_runtime'dan bağımsız çalışması için buraya aldık)
SUPABASE_URL = _secret_oku("SUPABASE_URL", "")
SUPABASE_KEY = _secret_oku("SUPABASE_KEY", "")

def _supa_basliklar(ekstra=None):
    h = {"apikey": SUPABASE_KEY}
    if not str(SUPABASE_KEY).startswith("sb_"):
        h["Authorization"] = f"Bearer {SUPABASE_KEY}"
    if ekstra:
        h.update(ekstra)
    return h

def supabase_anahtar_rolu():
    anahtar = str(SUPABASE_KEY or "")
    if anahtar.startswith("sb_publishable"):
        return "anon"
    if anahtar.startswith("sb_secret"):
        return "service_role"
    try:
        parca = anahtar.split(".")[1]
        parca += "=" * (-len(parca) % 4)
        return str(json.loads(base64.urlsafe_b64decode(parca)).get("role", "bilinmiyor"))
    except Exception:
        return "bilinmiyor"

@st.cache_resource
def get_http_session():
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(pool_connections=10, pool_maxsize=20)
    session.mount("https://", adapter)
    return session

def _supabase_ham_oku(kayit_id):
    try:
        session = get_http_session()
        r = session.get(
            f"{SUPABASE_URL}/rest/v1/asevi_veritabani",
            headers=_supa_basliklar(),
            params={"id": f"eq.{kayit_id}", "select": "veri"},
            timeout=10,
        )
    except Exception as e:
        return "hata", f"Bağlantı hatası: {type(e).__name__}"
    if r.status_code != 200:
        return "hata", f"HTTP {r.status_code}"
    try:
        data = r.json()
    except Exception:
        return "hata", "Geçersiz yanıt"
    if data and data[0].get("veri") is not None:
        return "ok", data[0]["veri"]
    return "yok", None

@st.cache_data(ttl=60, show_spinner=False)
def _supabase_ham_oku_cached(kayit_id):
    return _supabase_ham_oku(kayit_id)

def _supabase_ham_oku_versiyonlu(kayit_id):
    try:
        r = get_http_session().get(
            f"{SUPABASE_URL}/rest/v1/asevi_veritabani",
            headers=_supa_basliklar(),
            params={"id": f"eq.{kayit_id}", "select": "veri,versiyon"},
            timeout=10,
        )
    except Exception as e:
        return "hata", f"Bağlantı hatası: {type(e).__name__}", None
    if r.status_code != 200:
        return "hata", f"HTTP {r.status_code}", None
    try:
        data = r.json()
    except Exception:
        return "hata", "Geçersiz yanıt", None
    if data and data[0].get("veri") is not None:
        return "ok", data[0]["veri"], int(data[0].get("versiyon") or 0)
    return "yok", None, None

def _supabase_cas_yaz(kayit_id, beklenen_versiyon, yeni_veri):
    try:
        if beklenen_versiyon is None:
            r = get_http_session().post(
                f"{SUPABASE_URL}/rest/v1/asevi_veritabani",
                headers=_supa_basliklar({
                    "Content-Type": "application/json",
                    "Prefer": "resolution=ignore-duplicates,return=representation",
                }),
                json={"id": kayit_id, "veri": yeni_veri, "versiyon": 0},
                timeout=10,
            )
            if r.status_code in (200, 201) and r.json():
                return True, 0
            return False, "insert-çakışma"
        yeni_versiyon = beklenen_versiyon + 1
        r = get_http_session().patch(
            f"{SUPABASE_URL}/rest/v1/asevi_veritabani",
            headers=_supa_basliklar({
                "Content-Type": "application/json",
                "Prefer": "return=representation",
            }),
            params={"id": f"eq.{kayit_id}", "versiyon": f"eq.{beklenen_versiyon}"},
            json={"veri": yeni_veri, "versiyon": yeni_versiyon},
            timeout=10,
        )
        if r.status_code == 200:
            guncellenen = r.json()
            if guncellenen:
                return True, yeni_versiyon
            return False, "versiyon-çakışma"
        return False, f"HTTP {r.status_code}"
    except Exception as e:
        return False, f"Bağlantı hatası: {type(e).__name__}"

def _atomik_dict_guncelle(kayit_id, guncelleme_fn, max_retry=8):
    son_hata = ""
    for i in range(max_retry):
        durum, mevcut, versiyon = _supabase_ham_oku_versiyonlu(kayit_id)
        if durum == "hata":
            return "hata", mevcut
        mevcut_dict = dict(mevcut) if isinstance(mevcut, dict) else {}
        yeni = guncelleme_fn(dict(mevcut_dict))
        basarili, sonuc = _supabase_cas_yaz(kayit_id, versiyon, yeni)
        if basarili:
            return "ok", yeni
        son_hata = sonuc
        time.sleep(0.02 * (2 ** min(i, 4)))
    return "hata", f"Çakışma ({max_retry} deneme): {son_hata}"
