import streamlit as st
import os
import json
from database import yetki_kontrol

# Sayfa Yetki Kontrolü: Yalnızca ADMIN erişebilir!
yetki_kontrol(["admin"])

st.title("🛠️ Admin Paneli ve Sistem Logları")
st.info("🔒 Bu sayfa yalnızca 'Admin' yetkisine sahip kullanıcılar tarafından görüntülenebilir.")

LOG_DOSYASI = "sistem_loglari.json"

st.subheader("📋 Aşçı ve Admin İşlem Geçmişi (Loglar)")

if os.path.exists(LOG_DOSYASI):
    try:
        with open(LOG_DOSYASI, "r", encoding="utf-8") as f:
            loglar = json.load(f)
            
        if loglar:
            # En son yapılan işlemler üstte görüksün diye ters çevirelim
            for log in reversed(loglar):
                zaman = log.get("zaman")
                kullanici = log.get("kullanici")
                rol = log.get("rol")
                detay = log.get("detay")
                
                st.write(f"🕒 **{zaman}** — 👤 **{kullanici}** (*{rol.upper()}*)")
                st.caption(f"İşlem: {detay}")
                st.divider()
        else:
            st.info("Henüz kaydedilmiş bir sistem logu bulunmuyor.")
    except Exception as e:
        st.error(f-"Loglar okunurken hata oluştu: {e}")
else:
    st.info("Henüz sistem log dosyası oluşturulmamış.")
