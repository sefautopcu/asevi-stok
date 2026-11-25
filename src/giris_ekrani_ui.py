import streamlit as st


def giris_ekrani_goster(
    kimlik_dogrula=None,
    log=None,
    baslik="Aziziye Aşevi Giriş Paneli",
    alt_baslik="Mutfak, stok ve dağıtım operasyonları için oturum açın.",
):
    """Dark temalı giriş ekranı bileşeni."""
    st.markdown(f"## 🔐 {baslik}")
    st.caption(alt_baslik)

    with st.form("aziziyeasevi_giris_formu", clear_on_submit=False):
        kullanici_adi = st.text_input("Kullanıcı Adı veya E-posta", key="giris_kullanici")
        parola = st.text_input("Parola", type="password", key="giris_parola")
        giris_yap = st.form_submit_button("Giriş Yap", type="primary")

    if not giris_yap:
        return False

    if not kullanici_adi.strip() or not parola:
        st.error("Lütfen kullanıcı adı ve parola girin.")
        return False

    if kimlik_dogrula is None:
        aktif = kullanici_adi.strip()
        st.session_state["giris_yapildi"] = True
        st.session_state["oturum_aktif"] = True
        st.session_state["aktif_kullanici"] = aktif
        st.success("Oturum açıldı.")
        st.rerun()
        return True

    ok, kullanici_bilgisi, mesaj = kimlik_dogrula(kullanici_adi.strip(), parola)
    if ok:
        aktif = kullanici_bilgisi or kullanici_adi.strip()
        st.session_state["giris_yapildi"] = True
        st.session_state["oturum_aktif"] = True
        st.session_state["aktif_kullanici"] = aktif
        if log is not None:
            log.info("Başarılı giriş: %s", aktif)
        st.success("Giriş başarılı. Yönlendiriliyor...")
        st.rerun()
        return True

    if log is not None:
        log.warning("Başarısız giriş denemesi: %s", kullanici_adi.strip())
    st.error(mesaj or "Kullanıcı adı veya parola hatalı.")
    return False
