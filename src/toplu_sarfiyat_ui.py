import datetime
import time
from src.ui_kartlar import (
    bolum_basligi_goster,
    kpi_satiri_goster,
    sayfa_ust_banner_goster,
)


def toplu_stok_dusumu_sayfasi(
    st,
    misafir_modu,
    salt_okunur_modu,
    otomatik_yedek_al,
    fifo_sarfiyat_dus_detayli,
    verileri_kaydet,
    loglari_kaydet,
    ozel_html_tablo_goster,
):
    if misafir_modu:
        st.warning("⚠️ Bu sayfaya erişim yetkiniz bulunmamaktadır.")
    else:
        sayfa_ust_banner_goster(
            st,
            "stok",
            "Toplu Stok Düşümü ve Kullanılan Ürünler",
            "Reçete seçmeden mutfakta kullanılan malzemeleri FIFO yöntemiyle doğrudan stoktan düşün",
            tema="mavi",
        )

        loglar_liste = st.session_state.get("kullanim_loglari", []) or []
        girisler_liste = st.session_state.get("girisler", []) or []
        sarf_ozet_loglar = [l for l in loglar_liste if "Toplu Sarfiyat" in l.get("tur", "")]
        toplam_sarf_tutar = sum(float(_l.get("tutar", 0) or 0) for _l in sarf_ozet_loglar)
        kullanilan_cesit = len({str(_l.get("urun", "")).strip().upper() for _l in sarf_ozet_loglar if _l.get("urun")})
        aktif_stok_cesit = len({str(_g.get("urun", "")).strip().upper() for _g in girisler_liste if float(_g.get("kalan", 0) or 0) > 0})

        kpi_satiri_goster(
            st,
            [
                ("liste", "Toplu Sarfiyat İşlemi", len(sarf_ozet_loglar), "Doğrudan stoktan düşülen kayıt sayısı", "#38bdf8"),
                ("para", "Toplam Sarfiyat Tutarı", f"{toplam_sarf_tutar:,.2f} ₺", "Kullanılan malzemelerin toplam bedeli", "#10b981"),
                ("mutfak", "Kullanılan Ürün Çeşidi", kullanilan_cesit, "Sarfiyat yapılan farklı kalem sayısı", "#f59e0b"),
                ("stok", "Stokta Mevcut Ürün", aktif_stok_cesit, "Düşüm yapılabilir aktif ürün çeşidi", "#a855f7"),
            ],
        )

        if salt_okunur_modu:
            st.warning("👀 Salt okunur (Yönetim/Misafir) modundasınız. Bu ekranda toplu stok düşümü yapamazsınız.")
        else:
            # Son Sarfiyat İşlemini Geri Al Butonu ve Bildirimi
            if st.session_state.get("son_toplu_sarfiyat_kaydi"):
                son_sarf = st.session_state["son_toplu_sarfiyat_kaydi"]
                c_undo1, c_undo2 = st.columns([3, 1])
                with c_undo1:
                    st.info(
                        f"💡 **Son Sarfiyat Kaydı:** {son_sarf.get('urun')} "
                        f"({son_sarf.get('miktar')} Miktar - Tutar: {son_sarf.get('tutar', 0):,.2f} ₺ - Tarih: {son_sarf.get('tarih')})"
                    )
                with c_undo2:
                    if st.button("↩️ Son Sarfiyat İşlemini Geri Al", type="secondary", key="btn_undo_toplu_sarf_son"):
                        otomatik_yedek_al("Toplu sarfiyat geri alma: " + str(son_sarf.get("urun")))

                        # Düşülen miktarları orijinal stok girişlerine iade et
                        for item in son_sarf.get("dusulen_kayitlar", []):
                            for g in st.session_state.girisler:
                                if g.get("id") == item["id"]:
                                    g["kalan"] = float(g.get("kalan", 0)) + float(item["miktar"])

                        # Kullanım loglarından sil
                        log_target = son_sarf.get("log_objesi")
                        if log_target and log_target in st.session_state.kullanim_loglari:
                            st.session_state.kullanim_loglari.remove(log_target)

                        verileri_kaydet(st.session_state.girisler)
                        loglari_kaydet(st.session_state.kullanim_loglari)

                        st.session_state.pop("son_toplu_sarfiyat_kaydi", None)
                        st.success(f"🎉 {son_sarf.get('urun')} için yapılan stok düşümü geri alındı ve stok iade edildi!")
                        time.sleep(1)
                        st.rerun()

            col_form1, col_form2 = st.columns(2)

            with col_form1:
                bolum_basligi_goster(
                    st,
                    "stok",
                    "Malzeme Çıkış Formu",
                    "Stoktan düşülecek ürün, miktar ve kullanım notunu girin",
                    vurgu_renk="#38bdf8",
                )
                benzersiz_urunler_toplu = sorted(
                    list(set(g.get("urun", "").strip().upper() for g in st.session_state.girisler if g.get("urun")))
                )

                if benzersiz_urunler_toplu:
                    col_t1, col_t2 = st.columns(2)
                    with col_t1:
                        toplu_tarih_secim = st.date_input("📅 Sarfiyat Tarihi", value=datetime.date.today(), key="toplu_tarih_inp")
                    with col_t2:
                        toplu_saat_secim = st.time_input("⏰ Sarfiyat Saati", value=datetime.datetime.now().time(), key="toplu_saat_inp")
                    toplu_tarih_str = f"{toplu_tarih_secim.strftime('%Y-%m-%d')} {toplu_saat_secim.strftime('%H:%M')}"

                    selected_item = st.selectbox(
                        "Malzeme Seçin",
                        benzersiz_urunler_toplu,
                        index=None,
                        placeholder="Malzeme Seçiniz...",
                        key="toplu_malzeme_selectbox",
                    )

                    if selected_item:
                        ilgili_girisler_toplu = [
                            g for g in st.session_state.girisler
                            if g.get("urun", "").strip().upper() == selected_item.strip().upper()
                        ]
                        current_stock = sum(float(g.get("kalan", 0)) for g in ilgili_girisler_toplu)
                        aktif_ilgili_toplu = [g for g in ilgili_girisler_toplu if float(g.get("kalan", 0)) > 0]

                        unit = ilgili_girisler_toplu[0].get("birim", "Kg") if ilgili_girisler_toplu else "Kg"

                        st.info(f"Mevcut Toplam Stok ({selected_item}): {current_stock} {unit}")

                        used_amount = st.number_input(f"Kullanılan Miktar ({unit})", min_value=0.1, value=1.0, step=0.5)
                        description = st.text_input("Açıklama / Not (Örn: Kazan yemeği, günlük dağıtım vb.)", "Günlük Aşevi Üretimi")

                        if st.button("Stoktan Düş ve Kullanılanlara Ekle", type="primary"):
                            if used_amount <= 0:
                                st.error("⚠️ Lütfen 0'dan büyük bir miktar girin!")
                            elif used_amount > current_stock:
                                st.error(f"⚠️ Hata: Kullanılan miktar ({used_amount}), mevcut toplam stoktan ({current_stock}) büyük olamaz!")
                            else:
                                harcanan_tutar, dusulen_kayitlar = (
                                    fifo_sarfiyat_dus_detayli(aktif_ilgili_toplu, used_amount)
                                )

                                yeni_log = {
                                    "tarih": toplu_tarih_str,
                                    "urun": selected_item,
                                    "tur": f"Toplu Sarfiyat ({description})",
                                    "miktar": used_amount,
                                    "tutar": harcanan_tutar,
                                    "islem_yapan": st.session_state.aktif_kullanici,
                                }

                                st.session_state.kullanim_loglari.append(yeni_log)

                                st.session_state["son_toplu_sarfiyat_kaydi"] = {
                                    "urun": selected_item,
                                    "miktar": used_amount,
                                    "tutar": harcanan_tutar,
                                    "tarih": toplu_tarih_str,
                                    "dusulen_kayitlar": dusulen_kayitlar,
                                    "log_objesi": yeni_log,
                                }

                                verileri_kaydet(st.session_state.girisler)
                                loglari_kaydet(st.session_state.kullanim_loglari)

                                st.success(f"🎉 Başarılı! {toplu_tarih_str} tarihli {used_amount} {unit} {selected_item} stoktan düşüldü ve loglara eklendi!")
                                st.balloons()
                                time.sleep(1)
                                st.rerun()
                else:
                    st.info("Depoda kayıtlı ürün bulunmuyor.")

            with col_form2:
                bolum_basligi_goster(
                    st,
                    "liste",
                    "Geçmişte Kullanılan Ürünler (Sarfiyat Logu)",
                    "Doğrudan stoktan düşülen sarfiyat kayıtları",
                    vurgu_renk="#10b981",
                )
                toplu_sarfiyat_loglari = [l for l in st.session_state.kullanim_loglari if "Toplu Sarfiyat" in l.get("tur", "")]
                if toplu_sarfiyat_loglari:
                    tablo_sarf = []
                    for s_log in reversed(toplu_sarfiyat_loglari):
                        tablo_sarf.append({
                            "Tarih / Saat": s_log.get("tarih", "-"),
                            "Malzeme": s_log.get("urun", "-"),
                            "Miktar": f"{s_log.get('miktar', 0)}",
                            "Tutar": f"{s_log.get('tutar', 0):,.2f} ₺",
                            "Açıklama": s_log.get("tur", "-"),
                            "İşlemi Yapan": s_log.get("islem_yapan", "-"),
                        })
                    ozel_html_tablo_goster(tablo_sarf)
                else:
                    st.info("Henüz toplu stok düşümü yapılmadı.")
