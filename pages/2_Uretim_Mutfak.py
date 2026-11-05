import streamlit as st
from database import verileri_yukle, verileri_kaydet, yetki_kontrol, yazma_yetkisi_var_mi, log_kaydet

# Sayfa Yetki Kontrolü: Misafir bu sayfaya erişemez!
yetki_kontrol(["admin", "yonetici", "asci"])

st.title("🍳 Üretim ve Mutfak Yönetimi")

# Kullanıcı yetki durumu
if not yazma_yetkisi_var_mi():
    st.warning("👀 **Yönetici Modu:** Bu sayfayı yalnızca görüntüleyebilirsiniz.")
else:
    st.info(f"✍️ **{st.session_state.rol.upper()} Modu:** Yemek üretimi ve reçete ekleme yetkisine sahipsiniz.")

veri = verileri_yukle()
uretim_listesi = veri.get("uretim", [])

# --- YENİ ÜRETİM / YEMEK PLANLA ---
if yazma_yetkisi_var_mi():
    with st.expander("🍲 Günlük Yemek Üretimi Planla"):
        with st.form("uretim_form"):
            yemek_adi = st.text_input("Yemek Adı")
            porsiyon = st.number_input("Planlanan Porsiyon / Kişi Sayısı", min_value=1, step=10)
            aciklama = st.text_area("Kullanılacak Malzemeler ve Notlar")
            
            submit = st.form_submit_button("Üretimi Kaydet")
            if submit:
                if yemek_adi:
                    yeni_kayit = {
                        "yemek_adi": yemek_adi,
                        "porsiyon": porsiyon,
                        "aciklama": aciklama
                    }
                    uretim_listesi.append(yeni_kayit)
                    veri["uretim"] = uretim_listesi
                    verileri_kaydet(veri)
                    
                    log_kaydet(st.session_state.kullanici_adi, st.session_state.rol, f"Yeni üretim planlandı: {yemek_adi} ({porsiyon} porsiyon)")
                    st.success(f"'{yemek_adi}' üretim planına eklendi!")
                    st.rerun()
                else:
                    st.error("Lütfen yemek adını giriniz.")

# --- PLANLANAN ÜRETİMLERİ LİSTELE ---
st.subheader("📋 Planlanan Üretimler")
if uretim_listesi:
    for idx, item in enumerate(uretim_listesi):
        st.write(f"🍲 **{item.get('yemek_adi')}** — *{item.get('porsiyon')} Porsiyon*")
        if item.get('aciklama'):
            st.caption(f"Notlar: {item.get('aciklama')}")
        
        if yazma_yetkisi_var_mi():
            if st.button("Üretimi Kaldır", key=f"uret_sil_{idx}"):
                uretim_listesi.pop(idx)
                veri["uretim"] = uretim_listesi
                verileri_kaydet(veri)
                log_kaydet(st.session_state.kullanici_adi, st.session_state.rol, f"Üretim kaydı silindi.")
                st.rerun()
        st.divider()
else:
    st.info("Henüz planlanmış bir üretim kaydı bulunmuyor.")
