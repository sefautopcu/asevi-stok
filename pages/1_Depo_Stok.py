import streamlit as st
from database import verileri_yukle, verileri_kaydet, yetki_kontrol, yazma_yetkisi_var_mi, log_kaydet

# Sayfa Yetki Kontrolü: Misafir bu sayfaya erişemez!
yetki_kontrol(["admin", "yonetici", "asci"])

st.title("📦 Depo ve Stok Yönetimi")

# Kullanıcı yetki durumuna göre bilgi mesajı
if not yazma_yetkisi_var_mi():
    st.warning("👀 **Yönetici Modu:** Bu sayfayı yalnızca görüntüleyebilirsiniz. Ekleme veya güncelleme yetkiniz bulunmamaktadır.")
else:
    st.info(f"✍️ **{st.session_state.rol.upper()} Modu:** Stok ekleme ve güncelleme yetkisine sahipsiniz.")

# Verileri Yükle
veri = verileri_yukle()
stoklar = veri.get("stok", [])

# --- YENİ ÜRÜN EKLEME ALANI (Sadece Admin ve Aşçı) ---
if yazma_yetkisi_var_mi():
    with st.expander("➕ Yeni Ürün / Malzeme Ekle"):
        with st.form("stok_ekle_form"):
            urun_adi = st.text_input("Ürün Adı")
            kategori = st.selectbox("Kategori", ["Kuru Gıda", "Bakliyat", "Sebze/Meyve", "Temizlik", "Diğer"])
            miktar = st.number_input("Miktar", min_value=0.0, step=1.0)
            birim = st.selectbox("Birim", ["Kg", "Adet", "Litre", "Çuval", "Paket"])
            
            submit = st.form_submit_button("Stoklara Ekle")
            if submit:
                if urun_adi:
                    yeni_urun = {
                        "urun_adi": urun_adi,
                        "kategori": kategori,
                        "miktar": miktar,
                        "birim": birim
                    }
                    stoklar.append(yeni_urun)
                    veri["stok"] = stoklar
                    verileri_kaydet(veri)
                    
                    # İşlemi Logla
                    log_kaydet(st.session_state.kullanici_adi, st.session_state.rol, f"Yeni ürün eklendi: {urun_adi} ({miktar} {birim})")
                    
                    st.success(f"'{urun_adi}' başarıyla depoya eklendi!")
                    st.rerun()
                else:
                    st.error("Lütfen ürün adını boş bırakmayın.")

# --- MEVCUT STOKLARI LİSTELEME ---
st.subheader("📋 Mevcut Stok Listesi")
if stoklar:
    for idx, item in enumerate(stoklar):
        col1, col2, col3 = st.columns([3, 2, 1])
        with col1:
            st.write(f"**{item.get('urun_adi')}** ({item.get('kategori')})")
        with col2:
            st.write(f"Miktar: {item.get('miktar')} {item.get('birim')}")
        with col3:
            # Silme işlemi sadece yazma yetkisi olanlarda aktif
            if yazma_yetkisi_var_mi():
                if st.button("Sil", key=f"sil_{idx}"):
                    silinen = stoklar.pop(idx)
                    veri["stok"] = stoklar
                    verileri_kaydet(veri)
                    log_kaydet(st.session_state.kullanici_adi, st.session_state.rol, f"Ürün silindi: {silinen.get('urun_adi')}")
                    st.warning(f"Ürün silindi.")
                    st.rerun()
        st.divider()
else:
    st.info("Depoda henüz kayıtlı ürün bulunmuyor.")
