import datetime
import time
from src.rapor_utils import para_formatla_tr
from src.ui_kartlar import (
    bolum_basligi_goster,
    kpi_satiri_goster,
    sayfa_ust_banner_goster,
)


def guncel_stok_sayfasi(
    st,
    misafir_modu,
    aktif_k_maskeleri,
    stok_excel_liste_olustur,
    tablo_to_excel_bytes,
    tablo_to_html_pdf_bytes,
    ortak_indirme_alani,
    stok_gorunum_listeleri_olustur,
    ozel_html_tablo_goster,
    verileri_kaydet,
    kritik_seviyeleri_kaydet,
    mevcut_urunler_qr_etiket_araci,
):
    if misafir_modu:
        st.warning("⚠️ Bu sayfaya erişim yetkiniz bulunmamaktadır.")
    else:
        sayfa_ust_banner_goster(
            st,
            "stok",
            "Güncel Depo Envanteri ve Kritik Stoklar",
            "Depodaki tüm ürünlerin toplam miktarları, eski partilerden devreden bakiyeleri ve kritik seviye uyarıları",
            tema="yesil",
        )
        bugun = datetime.date.today()

        # Excel ve Raporlama için Hazırlık
        benzersiz_urunler_Excel, excel_liste = stok_excel_liste_olustur(
            st.session_state.girisler, aktif_k_maskeleri
        )

        # Canlı KPI Hesaplamaları
        girisler_liste = st.session_state.get("girisler", []) or []
        toplam_stok_degeri = 0.0
        yaklasan_skt_sayisi = 0
        for _g in girisler_liste:
            try:
                _kalan = float(_g.get("kalan", 0) or 0)
                if _kalan > 0:
                    if _g.get("birim_fiyat") is not None:
                        _bf = float(_g.get("birim_fiyat") or 0)
                    else:
                        _bf = float(_g.get("fiyat") or 0)
                    toplam_stok_degeri += _kalan * _bf

                    if _g.get("skt"):
                        _skt_dt = datetime.datetime.strptime(str(_g.get("skt"))[:10], "%Y-%m-%d").date()
                        if (_skt_dt - bugun).days <= 15:
                            yaklasan_skt_sayisi += 1
            except Exception:
                pass

        depo_sayisi = len(st.session_state.get("depolar", []) or [])
        kpi_satiri_goster(
            st,
            [
                ("stok", "Toplam Ürün Çeşidi", len(benzersiz_urunler_Excel), "Depoda tanımlı farklı ürün kalemi", "#10b981"),
                ("para", "Güncel Stok Değeri", para_formatla_tr(toplam_stok_degeri), "Kalan bakiyelerin toplam maliyeti", "#38bdf8"),
                ("takvim", "SKT Yaklaşan / Geçen", yaklasan_skt_sayisi, "15 gün içinde veya tarihi geçmiş parti", "#f59e0b"),
                ("depo", "Aktif Depo Alanı", depo_sayisi, "Tanımlı depolama noktası", "#a855f7"),
            ],
        )

        excel_data = tablo_to_excel_bytes(excel_liste, "Aziziye Aşevi - Güncel Stok Raporu")
        pdf_data = tablo_to_html_pdf_bytes("Aziziye Aşevi - Güncel Stok Raporu", excel_liste)

        col_baslik, col_indir_alan = st.columns([2, 2])
        with col_baslik:
            depolar = ["Tümü"] + st.session_state.depolar
            secilen_depo = st.selectbox("Depo Konumuna Göre Filtrele", depolar)
        with col_indir_alan:
            ortak_indirme_alani(excel_data, pdf_data, "asevi_guncel_stok_raporu", "stok_sayfasi")

        benzersiz_urunler, stok_tablosu, kritik_urunler_tablosu = (
            stok_gorunum_listeleri_olustur(
                st.session_state.girisler, st.session_state.kritik_seviyeler,
                aktif_k_maskeleri, secilen_depo, bugun,
            )
        )

        bolum_basligi_goster(
            st,
            "stok",
            "Envanter Listesi",
            "Seçili depo konumuna göre güncel ürün miktarları ve devreden parti bakiyeleri",
            vurgu_renk="#10b981",
        )
        ozel_html_tablo_goster(stok_tablosu)

        st.markdown("---")
        bolum_basligi_goster(
            st,
            "uyari",
            "Kritik Seviyenin Altındaki veya Tükenen Ürünler Tablosu",
            "Minimum stok eşiğinin altına düşen veya tükenen acil tedarik kalemleri",
            vurgu_renk="#f43f5e",
        )
        if kritik_urunler_tablosu:
            ozel_html_tablo_goster(kritik_urunler_tablosu)
        else:
            st.success("Tebrikler! Kritik seviyenin altında ürün bulunmuyor.")

        st.markdown("---")

        # --- TOPLU SKT GÜNCELLEME FORMU ---
        bolum_basligi_goster(
            st,
            "takvim",
            "Son Tüketim Tarihi (SKT / STT) Güncelle",
            "Stokta kalan ürün partileri için toplu son tüketim tarihi tanımlama",
            vurgu_renk="#38bdf8",
        )
        st.info(
            "Sisteme daha önceden eklenmiş ve SKT tarihi girilmemiş ürünler için buradan toplu tarih güncellemesi yapabilirsiniz. "
            "Girilen tarih, seçilen ürünün en eski (en son kullanılacak) partisine atanır."
        )

        if not benzersiz_urunler:
            st.info("Sistemde kayıtlı ürün bulunmuyor.")
        else:
            with st.form("skt_guncelle_formu"):
                skt_sec_urun = st.selectbox(
                    "SKT Güncellenecek Ürünü Seçin",
                    benzersiz_urunler,
                    index=None,
                    placeholder="Ürün Seçiniz...",
                    key="skt_upd_urun",
                )
                skt_yeni_tarih = st.date_input("Yeni SKT / STT Tarihi", value=None)
                skt_guncelle_btn = st.form_submit_button("SKT Tarihini Güncelle", type="primary")

                if skt_guncelle_btn:
                    if not skt_sec_urun:
                        st.error("⚠️ Lütfen SKT güncellenecek ürünü seçin!")
                    elif skt_yeni_tarih is None:
                        st.error("⚠️ Lütfen yeni SKT / STT tarihini seçin!")
                    else:
                        guncellendi = False
                        yeni_girisler = []
                        aranan_urun = str(skt_sec_urun).strip().upper()

                        for g in st.session_state.girisler:
                            yeni_g = g.copy()
                            # SADECE STOKTA KALANI > 0 OLANLARI GÜNCELLE
                            if (
                                str(yeni_g.get("urun", "")).strip().upper() == aranan_urun
                                and float(yeni_g.get("kalan", 0) or 0) > 0
                            ):
                                yeni_g["skt"] = str(skt_yeni_tarih)
                                guncellendi = True
                            yeni_girisler.append(yeni_g)

                        if guncellendi:
                            st.session_state.girisler = yeni_girisler
                            verileri_kaydet(st.session_state.girisler)
                            st.cache_data.clear()
                            st.success(f"🎉 Başarılı! {skt_sec_urun} ürününün SKT tarihi {skt_yeni_tarih} olarak güncellendi.")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.warning("⚠️ Seçilen ürünün stokta kalan partisi bulunmuyor, tarih atanamadı.")

        # --- ÜRÜN BAZLI KRİTİK EŞİK SINIRI ---
        with st.expander("⚙️ Ürün Bazlı Kritik Eşik Sınırı Belirle"):
            with st.form("kritik_ayar_form"):
                secilen_k_urun = st.selectbox(
                    "Kritik Eşiği Değiştirilecek Ürün",
                    benzersiz_urunler if benzersiz_urunler else ["Yok"],
                )
                mevcut_esin = st.session_state.kritik_seviyeler.get(secilen_k_urun, 10.0)
                yeni_esin_deger = st.number_input("Kritik Miktar Sınırı", min_value=0.0, value=float(mevcut_esin), step=1.0)
                kritik_kaydet_btn = st.form_submit_button("Kritik Eşiği Güncelle", type="primary")

                if kritik_kaydet_btn and secilen_k_urun != "Yok":
                    st.session_state.kritik_seviyeler[secilen_k_urun] = yeni_esin_deger
                    kritik_seviyeleri_kaydet(st.session_state.kritik_seviyeler)

                    st.cache_data.clear()

                    st.success("🎉 Başarılı! Kritik sınır güncellendi.")
                    st.balloons()
                    st.rerun()

        mevcut_urunler_qr_etiket_araci(
            st, benzersiz_urunler, verileri_kaydet
        )
