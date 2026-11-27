from src.rapor_utils import kayit_birim_fiyati_al, para_formatla_tr
from src.ui_kartlar import (
    bolum_basligi_goster,
    kpi_satiri_goster,
    sayfa_ust_banner_goster,
)


def kapsamli_envanter_rapor_sayfasi(
    st,
    misafir_modu,
    girisler,
    kapsamli_envanter_liste_olustur,
    tablo_to_excel_bytes,
    tablo_to_html_pdf_bytes,
    ortak_indirme_alani,
    ozel_html_tablo_goster,
):
    if misafir_modu:
        st.warning("⚠️ Bu sayfaya erişim yetkiniz bulunmamaktadır.")
    else:
        giris_kayitlari = girisler or []
        toplam_parti = len(giris_kayitlari)
        aktif_parti = sum(1 for g in giris_kayitlari if float(g.get("kalan", 0) or 0) > 0)
        urun_cesidi = len({str(g.get("urun", "")).strip().upper() for g in giris_kayitlari if g.get("urun")})
        kalan_stok_degeri = sum(
            float(g.get("kalan", 0) or 0) * kayit_birim_fiyati_al(g)
            for g in giris_kayitlari
        )
        
        sayfa_ust_banner_goster(
            st,
            "rapor",
            "Kapsamlı Envanter ve Hareket Raporu",
            "Tüm stok giriş partilerinin ilk miktar, harcanan tutar, kalan stok ve maliyet dökümü",
            tema="amber",
        )

        kpi_satiri_goster(
            st,
            [
                ("fatura", "Toplam Stok Partisi", toplam_parti, "Sistemdeki tüm giriş / fatura kalemleri", "#f59e0b"),
                ("stok", "Aktif Stok Partisi", aktif_parti, "Bakiyesi tükenmemiş mevcut partiler", "#10b981"),
                ("mutfak", "Kayıtlı Ürün Çeşidi", urun_cesidi, "Envanterdeki benzersiz malzeme sayısı", "#38bdf8"),
                ("para", "Kalan Envanter Değeri", para_formatla_tr(kalan_stok_degeri), "Mevcut stokların birim fiyat bazlı değeri", "#a855f7"),
            ],
        )

        col_b_env, col_indir_env = st.columns([2, 2])
        with col_b_env:
            bolum_basligi_goster(
                st,
                "liste",
                "Detaylı Envanter Hareket Tablosu",
                "Parti bazlı giriş, sarfiyat, kalan miktar ve mali değer listesi",
                vurgu_renk="#f59e0b",
            )

        kapsamli_liste = kapsamli_envanter_liste_olustur(girisler)

        excel_kapsamli_data = tablo_to_excel_bytes(
            kapsamli_liste, "Aziziye Aşevi - Kapsamlı Envanter ve Hareket Raporu"
        )
        pdf_kapsamli_data = tablo_to_html_pdf_bytes(
            "Aziziye Aşevi - Kapsamlı Envanter ve Hareket Raporu", kapsamli_liste
        )

        with col_indir_env:
            ortak_indirme_alani(
                excel_kapsamli_data,
                pdf_kapsamli_data,
                "kapsamli_envanter_ve_hareket_raporu",
                "kapsamli_envanter_sayfasi",
            )

        if kapsamli_liste:
            ozel_html_tablo_goster(kapsamli_liste)
        else:
            st.info("Kapsamlı rapor için kayıt bulunmuyor.")
