import streamlit as st
from database import verileri_yukle, verileri_kaydet, yetki_kontrol, yazma_yetkisi_var_mi, log_kaydet

# Sayfa Yetki Kontrolü: Misafir bu sayfaya erişemez!
yetki_kontrol(["admin", "yonetici", "asci"])

st.title("👥 İhtiyaç Sahipleri ve Dağıtım Yönetimi")

if not yazma_yetkisi_var_mi():
    st.warning("👀 **Yönetici Modu:** Bu sayfayı yalnızca görüntüleyebilirsiniz.")
else:
    st.info(f"✍️ **{st.session_state.rol.upper()} Modu:** İhtiyaç sahibi kaydı ekleme ve güncelleme yetkisine sahipsiniz.")

veri = verileri_yukle()
ihtiyac_sahipleri = veri.get("ihtiyac_sahipleri", [])

# --- YENİ İHTİYAÇ SAHİBİ EKLE ---
if yazma_yetkisi_var_mi():
    with st.expander("➕ Yeni İhtiyaç Sahibi / Aile Ekle"):
        with st.form("ihtiyac_form"):
            ad_soyad = st.text_input("Ad Soyad")
            tc_tel = st.text_input("T.C. Kimlik / Telefon (Hassas Bilgi)")
            kisi_sayisi = st.number_input("Hane Kişi Sayısı", min_value=1, step=1)
            adres = st.text_area("Adres Bilgisi")
            
            submit = st.form_submit_button("Kaydet")
            if submit:
                if ad_soyad:
                    yeni_kayit = {
                        "ad_soyad": ad_soyad,
                        "tc_tel": tc_tel,
                        "kisi_sayisi": kisi_sayisi,
                        "adres": adres
                    }
                    ihtiyac_sahipleri.append(yeni_kayit)
                    veri["ihtiyac_sahipleri"] = ihtiyac_sahipleri
                    verileri_kaydet(veri)
                    
                    log_kaydet(st.session_state.kullanici_adi, st.session_state.rol, f"Yeni ihtiyaç sahibi eklendi: {ad_soyad}")
                    st.success(f"'{ad_soyad}' başarıyla kaydedildi!")
                    st.rerun()
                else:
                    st.error("Lütfen ad soyad bilgisini giriniz.")

# --- LİSTELEME ---
st.subheader("📋 Kayıtlı İhtiyaç Sahipleri Listesi")
if ihtiyac_sahipleri:
    for idx, item in enumerate(ihtiyac_sahipleri):
        st.write(f"👤 **{item.get('ad_soyad')}** — *Hane Kişi Sayısı: {item.get('kisi_sayisi')}*")
        st.caption(f"Adres: {item.get('adres')}")
        
        if yazma_yetkisi_var_mi():
            if st.button("Kaydı Sil", key=f"ihtiyac_sil_{idx}"):
                ihtiyac_sahipleri.pop(idx)
                veri["ihtiyac_sahipleri"] = ihtiyac_sahipleri
                verileri_kaydet(veri)
                log_kaydet(st.session_state.kullanici_adi, st.session_state.rol, f"İhtiyaç sahibi kaydı silindi.")
                st.rerun()
        st.divider()
else:
    st.info("Henüz kayıtlı ihtiyaç sahibi bulunmuyor.")
