"""Streamlit report controls, separate from report data and serialization helpers."""
import streamlit as st
from .rapor_utils import (
    kayit_birim_fiyati_al,
    para_formatla_tr,
    tablo_html_olustur,
)
from .ui_kartlar import (
    bolum_basligi_goster,
    kpi_satiri_goster,
    sayfa_ust_banner_goster,
)


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
    streamlit_api,
    misafir_modu,
    kullanim_loglari,
    tablo_to_excel_bytes,
    tablo_to_html_pdf_bytes,
    ortak_indirme_alani,
    ozel_html_tablo_goster,
):
    """Render the usage-log archive while leaving access state in the app."""
    st = streamlit_api
    if misafir_modu:
        st.warning("⚠️ Bu sayfaya erişim yetkiniz bulunmamaktadır.")
        return

    loglar = kullanim_loglari or []
    toplam_hareket = len(loglar)
    toplam_tutar = sum(float(l.get("tutar", 0) or 0) for l in loglar)
    farkli_urun = len({str(l.get("urun", "")).strip().upper() for l in loglar if l.get("urun")})
    son_islem_tarihi = str(loglar[-1].get("tarih", "-")) if loglar else "-"

    sayfa_ust_banner_goster(
        st,
        "rapor",
        "Tüm Sistem Kullanım Logları ve Hareket Arşivi",
        "Yemek üretimi, toplu sarfiyat, fire ve iade kaynaklı tüm stok çıkış hareketleri",
        tema="mavi",
    )

    kpi_satiri_goster(
        st,
        [
            ("liste", "Toplam Hareket Kaydı", toplam_hareket, "Sistemdeki tüm kullanım ve çıkış logları", "#38bdf8"),
            ("para", "Toplam Hareket Tutarı", para_formatla_tr(toplam_tutar), "Kayıtlı tüm çıkışların mali toplamı", "#10b981"),
            ("stok", "İşlem Gören Ürün", farkli_urun, "Hareket kaydı bulunan ürün çeşidi", "#f59e0b"),
            ("takvim", "Son Hareket Zamanı", son_islem_tarihi, "En son kaydedilen stok çıkış tarihi", "#a855f7"),
        ],
    )

    col_baslik, col_indir = st.columns([2, 2])
    with col_baslik:
        bolum_basligi_goster(
            st,
            "liste",
            "Hareket Logları ve Rapor İndirme",
            "Kronolojik stok düşüm kayıtlarını inceleyin ve Excel/PDF olarak indirin",
            vurgu_renk="#38bdf8",
        )

    if kullanim_loglari:
        log_tablosu = []
        for log in reversed(kullanim_loglari):
            log_tablosu.append({
                "Tarih / Saat": log.get("tarih", "-"),
                "İşlem Türü / Açıklama": log.get("tur", "-"),
                "Ürün / Malzeme": log.get("urun", "-"),
                "Miktar": f"{log.get('miktar', 0)}",
                "Tutar": para_formatla_tr(log.get("tutar", 0)),
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
                excel_data,
                html_data,
                "sistem_kullanim_loglari_arsivi",
                "kullanim_sayfasi",
            )
        ozel_html_tablo_goster(log_tablosu)
    else:
        st.info("Henüz sistemde kayıtlı kullanım logu bulunmuyor.")


def urun_fiyat_analizi_sayfasi(
    streamlit_api,
    girisler,
    aktif_k_maskeleri,
    benzersiz_urun_adlari,
    urun_fiyat_analizi_olustur,
    tablo_to_excel_bytes,
    tablo_to_html_pdf_bytes,
    ortak_indirme_alani,
    ozel_html_tablo_goster,
):
    """Render the product price-analysis page with injected app dependencies."""
    st = streamlit_api

    sayfa_ust_banner_goster(
        st,
        "para",
        "Ürün Birim Fiyatları ve Ay Bazlı Maliyet Analizi",
        "Seçilen ürünün fatura bazlı birim fiyat değişimlerini ve aylık maliyet ortalamalarını analiz edin",
        tema="amber",
    )

    benzersiz_urunler = benzersiz_urun_adlari(girisler)
    if not benzersiz_urunler:
        st.info("Analiz edilecek ürün kaydı bulunmuyor.")
        return

    secenekler = ["Tüm Ürünler"] + list(benzersiz_urunler)
    secilen_urun = st.selectbox("Analiz Edilecek Ürünü Seçin", secenekler)
    tumu_secili = secilen_urun == "Tüm Ürünler"

    if tumu_secili:
        urun_kayitlari = list(girisler)
    else:
        urun_kayitlari = [
            row for row in girisler
            if row.get("urun", "").strip().upper() == secilen_urun.strip().upper()
        ]

    fiyat_gizli = (
        "2. Sayfa: Ürün Birim Fiyatları - Fiyat Sütunu" in aktif_k_maskeleri
    )

    alim_sayisi = len(urun_kayitlari)
    toplam_alinan_miktar = sum(float(r.get("miktar", 0) or 0) for r in urun_kayitlari)
    kalan_miktar = sum(float(r.get("kalan", 0) or 0) for r in urun_kayitlari)
    birim_etiket = urun_kayitlari[0].get("birim", "Kg") if urun_kayitlari else "Kg"
    fiyatlar = [
        kayit_birim_fiyati_al(r)
        for r in urun_kayitlari
        if kayit_birim_fiyati_al(r) > 0
    ]

    if tumu_secili:
        stok_kpi_deger = f"{len(benzersiz_urunler)} Çeşit"
        stok_kpi_alt = "Tüm ürün kalemleri listeleniyor"
        son_fiyat_deger = "🔒 Gizli" if fiyat_gizli else "Çoklu Ürün"
        ort_fiyat_deger = (
            "🔒 Gizli"
            if fiyat_gizli
            else (para_formatla_tr(sum(fiyatlar) / len(fiyatlar)) if fiyatlar else "0,00 ₺")
        )
        alim_alt_metin = "Tüm ürünler için toplam giriş kaydı"
    else:
        stok_kpi_deger = f"{kalan_miktar:,.2f} {birim_etiket}"
        stok_kpi_alt = f"Toplam alınan: {toplam_alinan_miktar:,.2f} {birim_etiket}"
        son_fiyat_deger = (
            "🔒 Gizli"
            if fiyat_gizli
            else (para_formatla_tr(fiyatlar[-1]) if fiyatlar else "0,00 ₺")
        )
        ort_fiyat_deger = (
            "🔒 Gizli"
            if fiyat_gizli
            else (para_formatla_tr(sum(fiyatlar) / len(fiyatlar)) if fiyatlar else "0,00 ₺")
        )
        alim_alt_metin = f"{secilen_urun} için kayıtlı giriş sayısı"

    kpi_satiri_goster(
        st,
        [
            ("fatura", "Alım / Fatura Sayısı", alim_sayisi, alim_alt_metin, "#f59e0b"),
            ("stok", "Mevcut Kalan Stok", stok_kpi_deger, stok_kpi_alt, "#10b981"),
            ("para", "Son Alım Birim Fiyatı", son_fiyat_deger, "En son faturadaki birim maliyet", "#38bdf8"),
            ("rapor", "Ortalama Birim Fiyat", ort_fiyat_deger, "Tüm alımların aritmetik birim ortalaması", "#a855f7"),
        ],
    )

    col_baslik, col_indir = st.columns([2, 2])
    with col_baslik:
        bolum_basligi_goster(
            st,
            "rapor",
            f"{secilen_urun} - Birim Fiyat ve Ay Bazlı Maliyet Tablosu",
            "Alım tarihleri, tedarikçiler ve birim fiyat karşılaştırması",
            vurgu_renk="#f59e0b",
        )

    gorunum, disari_aktarim = urun_fiyat_analizi_olustur(
        urun_kayitlari,
        fiyat_gizli=fiyat_gizli,
    )

    if tumu_secili and gorunum:
        # "Tüm Ürünler" görünümünde satırların hangi ürüne ait olduğunu göstermek için Ürün Adı sütununu başa ekle
        gorunum = [
            {"Ürün Adı": str(kayit.get("urun", "-")).strip(), **satir}
            for kayit, satir in zip(urun_kayitlari, gorunum)
        ]
        disari_aktarim = [
            {"Ürün Adı": str(kayit.get("urun", "-")).strip(), **satir}
            for kayit, satir in zip(urun_kayitlari, disari_aktarim)
        ]

    dosya_ek = "tum_urunler" if tumu_secili else secilen_urun.lower()
    excel_data = tablo_to_excel_bytes(
        disari_aktarim, f"Aziziye Aşevi - {secilen_urun} Fiyat Analizi"
    )
    html_data = tablo_to_html_pdf_bytes(
        f"Aziziye Aşevi - {secilen_urun} Fiyat Analizi", disari_aktarim
    )
    with col_indir:
        ortak_indirme_alani(
            excel_data,
            html_data,
            f"urun_fiyat_analizi_{dosya_ek}",
            "fiyat_analiz_sayfasi",
        )
    ozel_html_tablo_goster(gorunum)
