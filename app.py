import streamlit as st
from database import oturum_baslat, verileri_yukle

# Sayfa Yapılandırması
st.set_page_config(
    page_title="Aziziye Aşevi Takip Sistemi",
    page_icon="🍲",
    layout="wide"
)

# Oturumu Başlat
oturum_baslat()

# --- YAN MENÜ (SİDEBAR): GİRİŞ VE ROL YÖNETİMİ ---
st.sidebar.title("🍲 Aziziye Aşevi")
st.sidebar.info(f"Mevcut Rol: **{st.session_state.rol.upper()}**")

# Giriş Yapma Alanı (Sidebar içinde)
with st.sidebar.expander("🔐 Personel Girişi"):
    kullanici_adi = st.text_input("Kullanıcı Adı")
    sifre = st.text_input("Şifre", type="password")
    
    if st.button("Giriş Yap"):
        # Örnek Sabit Kontroller (İleride bunları veritabanından alabiliriz)
        if kullanici_adi == "admin" and sifre == "1234":
            st.session_state.kullanici_adi = "Admin"
            st.session_state.rol = "admin"
            st.success("Admin olarak giriş yapıldı!")
            st.rerun()
        elif kullanici_adi == "yonetici" and sifre == "1234":
            st.session_state.kullanici_adi = "Yönetici"
            st.session_state.rol = "yonetici"
            st.success("Yönetici olarak giriş yapıldı!")
            st.rerun()
        elif kullanici_adi == "asci" and sifre == "1234":
            st.session_state.kullanici_adi = "Aşçı"
            st.session_state.rol = "asci"
            st.success("Aşçı olarak giriş yapıldı!")
            st.rerun()
        else:
            st.error("Hatalı kullanıcı adı veya şifre!")

if st.sidebar.button("🚪 Çıkış Yap (Misafir Modu)"):
    st.session_state.kullanici_adi = "Misafir"
    st.session_state.rol = "misafir"
    st.success("Misafir moduna geçildi.")
    st.rerun()

# --- ANA EKRAN (DASHBOARD) ---
st.title("🌟 Aziziye Aşevi Yönetim Paneli")
st.write("Sisteme hoş geldiniz! Sol menüden giriş yapabilir veya yetkiniz dahilindeki sayfalara geçiş yapabilirsiniz.")

# Verileri Yükle
veri = verileri_yukle()

# Özet Metrikler
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(label="Toplam Stok Çeşidi", value=len(veri.get("stok", [])))

with col2:
    # Misafir kontrolü için hassas veri maskeleme mantığı
    if st.session_state.rol == "misafir":
        st.metric(label="Güncel Stok Tutarı", value="🔒 Gizli (***)")
    else:
        st.metric(label="Güncel Stok Tutarı", value="₺ 45.250 (Örnek)")

with col3:
    if st.session_state.rol == "misafir":
        st.metric(label="Toplam Fire Tutarı", value="🔒 Gizli (***)")
    else:
        st.metric(label="Toplam Fire Tutarı", value="₺ 1.120 (Örnek)")

st.divider()
st.info("💡 **Bilgi:** Sol taraftaki menüden (veya sayfalar listesinden) diğer modüllere geçiş yapabilirsiniz.")
