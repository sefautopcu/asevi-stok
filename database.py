import json
import os
import streamlit as st
from datetime import datetime

VERITABANI_DOSYASI = "asevi_stok_veritabani.json"
LOG_DOSYASI = "sistem_loglari.json"

# --- VERİTABANI YÖNETİMİ ---
def verileri_yukle():
    if not os.path.exists(VERITABANI_DOSYASI):
        # Varsayılan başlangıç verisi
        varsayilan_veri = {
            "stok": [],
            "ihtiyac_sahipleri": [],
            "personel": [],
            "uretim": []
        }
        verileri_kaydet(varsayilan_veri)
        return varsayilan_veri
    
    try:
        with open(VERITABANI_DOSYASI, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Veritabanı okuma hatası: {e}")
        return {}

def verileri_kaydet(veri):
    with open(VERITABANI_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=4)

# --- LOGLAMA MEKANİZMASI (Aşçı ve Admin İşlemleri İçin) ---
def log_kaydet(kullanici, rol, islem_detayi):
    loglar = []
    if os.path.exists(LOG_DOSYASI):
        try:
            with open(LOG_DOSYASI, "r", encoding="utf-8") as f:
                loglar = json.load(f)
        except:
            loglar = []
            
    yeni_log = {
        "zaman": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "kullanici": kullanici,
        "rol": rol,
        "detay": islem_detayi
    }
    loglar.append(yeni_log)
    
    with open(LOG_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(loglar, f, ensure_ascii=False, indent=4)

# --- YETKİ VE ROL KONTROLÜ ---
def oturum_baslat():
    if "kullanici_adi" not in st.session_state:
        st.session_state.kullanici_adi = "Misafir"
    if "rol" not in st.session_state:
        st.session_state.rol = "misafir"  # Varsayılan rol misafir

def yetki_kontrol(izin_verilen_roller):
    oturum_baslat()
    if st.session_state.rol not in izin_verilen_roller:
        st.error("🔒 Bu sayfaya erişim yetkiniz bulunmamaktadır.")
        st.stop()

def yazma_yetkisi_var_mi():
    oturum_baslat()
    # Yönetici (yonetici) ve Misafir değişiklik yapamaz, sadece Admin ve Aşçı yapabilir
    if st.session_state.rol in ["yonetici", "misafir"]:
        return False
    return True
