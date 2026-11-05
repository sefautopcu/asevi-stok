import streamlit as st
from database import verileri_yukle, verileri_kaydet, yetki_kontrol, yazma_yetkisi_var_mi, log_kaydet

# Sayfa Yetki Kontrolü: Aşçı ve Misafir bu sayfaya ERİŞEMEZ!
yetki_kontrol(["admin", "yonetici"])

st.title("👨‍💼 Personel ve Çalışma Süresi Takibi")

if st.session_state.rol == "yonetici":
    st.warning("👀 **Yönetici Modu:** Personel listesini yalnızca görüntüleyebilirsiniz.")
else:
    st.info("✍️ **Admin Modu:** Personel ekleme ve düzenleme yetkisine sahipsiniz.")

veri = verileri_yukle()
personel_listesi = veri.get("personel", [])

# --- YENİ PERSONEL EKLE (Sadece Admin) ---
if st.session_state.rol == "admin":
    with st.expander("➕ Yeni Personel Ekle"):
        with st.form("personel_form"):
            ad_soyad = st.text_input("Personel Ad Soyad")
            gorev = st.text_input("Görevi / Pozisyonu")
            ise_baslama = st.date_input("İşe Başlama Tarihi")
            
            submit = st.form_submit_button("Personeli Kaydet")
            if submit:
                if ad_soyad:
                    yeni_personel = {
                        "ad_soyad": ad_soyad,
                        "gorev": gorev,
                        "ise_baslama": str(ise_baslama)
                    }
                    personel_listesi.append(yeni_personel)
                    veri["personel"] = personel_listesi
                    verileri_kaydet(veri)
                    
                    log_kaydet(st.session_state.kullanici_adi, st.session_state.rol, f"Yeni personel eklendi: {ad_soyad}")
                    st.success(f"'{ad_soyad}' başarıyla eklendi!")
                    st.rerun()
                else:
                    st.error("Lütfen personel ad soyad bilgisini giriniz.")

# --- LİSTELEME ---
st.subheader("📋 Personel Listesi")
if personel_listesi:
    for idx, item in enumerate(personel_listesi):
        st.write(f"👨‍🔧 **{item.get('ad_soyad')}** — *{item.get('gorev')}* (Başlangıç: {item.get('ise_baslama')})")
        
        if st.session_state.rol == "admin":
            if st.button("Personeli Sil", key=f"personel_sil_{idx}"):
                personel_listesi.pop(idx)
                veri["personel"] = personel_listesi
                verileri_kaydet(veri)
                log_kaydet(st.session_state.kullanici_adi, st.session_state.rol, f"Personel kaydı silindi.")
                st.rerun()
        st.divider()
else:
    st.info("Henüz kayıtlı personel bulunmuyor.")
