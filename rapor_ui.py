"""Streamlit report controls, separate from report data and serialization helpers."""
import streamlit as st
from rapor_utils import tablo_html_olustur


def ortak_indirme_alani(excel_veri, pdf_veri, dosya_adi_koku, unique_key):
    col_sec, col_btn = st.columns([2, 1])
    with col_sec:
        format_secimi = st.selectbox(
            "İndirilecek Formatı Seçin",
            ["Excel (.xlsx)", "PDF / HTML (.html)"],
            key=f"sel_{unique_key}",
        )
    with col_btn:
        st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
        if "Excel" in format_secimi:
            st.download_button(
                label="📥 Raporu İndir",
                data=excel_veri,
                file_name=f"{dosya_adi_koku}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key=f"btn_{unique_key}",
            )
        else:
            st.download_button(
                label="📥 Raporu İndir",
                data=pdf_veri,
                file_name=f"{dosya_adi_koku}.html",
                mime="text/html",
                key=f"btn_{unique_key}",
            )


def ozel_html_tablo_goster(veri_listesi):
    if not veri_listesi:
        st.info("Gösterilecek veri bulunmuyor.")
        return
    st.markdown(tablo_html_olustur(veri_listesi), unsafe_allow_html=True)


def kullanim_takibi_sayfasi(
    streamlit_api, misafir_modu, kullanim_loglari, tablo_to_excel_bytes,
    tablo_to_html_pdf_bytes, ortak_indirme_alani, ozel_html_tablo_goster,
):
    """Render the usage-log archive while leaving access state in the app."""
    st = streamlit_api
    if misafir_modu:
        st.warning("⚠️ Bu sayfaya erişim yetkiniz bulunmamaktadır.")
        return

    col_baslik, col_indir = st.columns([2, 2])
    with col_baslik:
        st.header("📈 Tüm Sistem Kullanım Logları ve Hareket Arşivi")

    if kullanim_loglari:
        log_tablosu = []
        for log in reversed(kullanim_loglari):
            log_tablosu.append({
                "Tarih / Saat": log.get("tarih", "-"),
                "İşlem Türü / Açıklama": log.get("tur", "-"),
                "Ürün / Malzeme": log.get("urun", "-"),
                "Miktar": f"{log.get('miktar', 0)}",
                "Tutar": f"{log.get('tutar', 0):,.2f} ₺",
                "İşlemi Yapan": log.get("islem_yapan", "admin"),
            })

        excel_data = tablo_to_excel_bytes(
            log_tablosu, "Aziziye Aşevi - Sistem Kullanım Logları"
        )
        html_data = tablo_to_html_pdf_bytes(
            "Aziziye Aşevi - Sistem Kullanım Logları", log_tablosu
        )

        with col_indir:
            ortak_indirme_alani(
                excel_data, html_data, "sistem_kullanim_loglari_arsivi",
                "kullanim_sayfasi",
            )
        ozel_html_tablo_goster(log_tablosu)
    else:
        st.info("Henüz sistemde kayıtlı kullanım logu bulunmuyor.")


def urun_fiyat_analizi_sayfasi(
    streamlit_api, girisler, aktif_k_maskeleri, benzersiz_urun_adlari,
    urun_fiyat_analizi_olustur, tablo_to_excel_bytes, tablo_to_html_pdf_bytes,
    ortak_indirme_alani, ozel_html_tablo_goster,
):
    """Render the product price-analysis page with injected app dependencies."""
    st = streamlit_api
    col_baslik, col_indir = st.columns([2, 2])
    with col_baslik:
        st.header("💰 Ürün Birim Fiyatları ve Ay Bazlı Maliyet Analizi")

    benzersiz_urunler = benzersiz_urun_adlari(girisler)
    if not benzersiz_urunler:
        st.info("Analiz edilecek ürün kaydı bulunmuyor.")
        return

    secilen_urun = st.selectbox("Analiz Edilecek Ürünü Seçin", benzersiz_urunler)
    urun_kayitlari = [
        row for row in girisler
        if row.get("urun", "").strip().upper() == secilen_urun.strip().upper()
    ]
    gorunum, disari_aktarim = urun_fiyat_analizi_olustur(
        urun_kayitlari,
        fiyat_gizli=("2. Sayfa: Ürün Birim Fiyatları - Fiyat Sütunu" in aktif_k_maskeleri),
    )

    excel_data = tablo_to_excel_bytes(
        disari_aktarim, f"Aziziye Aşevi - {secilen_urun} Fiyat Analizi"
    )
    html_data = tablo_to_html_pdf_bytes(
        f"Aziziye Aşevi - {secilen_urun} Fiyat Analizi", disari_aktarim
    )
    with col_indir:
        ortak_indirme_alani(
            excel_data, html_data, f"urun_fiyat_analizi_{secilen_urun.lower()}",
            "fiyat_analiz_sayfasi",
        )
    ozel_html_tablo_goster(gorunum)
