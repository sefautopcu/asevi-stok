import html
import re
import time
import pandas as pd
from src.ui_kartlar import (
    bolum_basligi_goster,
    ikon_rozeti_html,
    kpi_satiri_goster,
    kullanici_ayarlari_luks_banner_goster,
)

_MASKE_GRUP_IKONLARI = {
    "Kurumsal Dashboard": ("rapor", "#38bdf8"),
    "Güncel Stok / Fire / Fiyat": ("stok", "#10b981"),
    "Günlük Yemek Üretimi": ("mutfak", "#f59e0b"),
    "Hazır Yemek Reçeteleri": ("mutfak", "#10b981"),
    "İhtiyaç Sahipleri Listesi": ("kullanici", "#a855f7"),
    "Yemek Dağıtımları": ("takvim", "#38bdf8"),
    "Dağıtım Sayaç Raporu": ("liste", "#fbbf24"),
}


def kullanici_yonetim_sekmesini_goster(sekme_k, st, kullanici_db, ESKI_VARSAYILAN_HASHLER, gecerli_menuler, otomatik_yedek_al, kullanici_oturumlarini_kapat, kullanıcıları_kaydet, giris_logla, sifre_hashle_yeni, sifre_politika_hatasi, sifre_degistir):
    with sekme_k:
        toplam_kullanici = len(kullanici_db)
        yetkili_sayisi = sum(
            1
            for k_adi, k_obj in kullanici_db.items()
            if k_adi == "admin" or k_obj.get("rol") == "Yönetim"
        )
        kisitli_hesap_sayisi = sum(
            1
            for k_obj in kullanici_db.values()
            if k_obj.get("maskeli_alanlar") or k_obj.get("yasakli_menuler") or k_obj.get("salt_okunur")
        )
        sifre_bekleyen_sayisi = sum(
            1
            for k_obj in kullanici_db.values()
            if k_obj.get("sifre_degistirilmeli") or k_obj.get("sifre", "") in ESKI_VARSAYILAN_HASHLER
        )

        kullanici_ayarlari_luks_banner_goster(st, toplam_kullanici=toplam_kullanici)

        kpi_satiri_goster(
            st,
            [
                ("kalkan", "Toplam Sistem Kullanıcısı", toplam_kullanici, "Tanımlı aktif kullanıcı hesapları", "#fbbf24"),
                ("tac", "Admin & Yönetim Rolü", yetkili_sayisi, "Üst düzey yönetici ve denetim hesapları", "#10b981"),
                ("maske", "Maskeli / Kısıtlı Hesap", kisitli_hesap_sayisi, "Alan maskesi veya sayfa kısıtı olanlar", "#38bdf8"),
                ("kilit", "Şifre Değişimi Bekleyen", sifre_bekleyen_sayisi, "İlk girişte şifre yenileyecek hesaplar", "#f43f5e"),
            ],
        )

        bolum_basligi_goster(
            st,
            "kalkan",
            "Aktif Kullanıcılar ve Yetki Matrisi",
            "Tüm kullanıcıların rol, salt okunur modu, maskelenen alan sayısı ve şifre durumu özeti",
            vurgu_renk="#fbbf24",
        )
        if len(kullanici_db) > 0:
            tablo_satirlari = []
            for k_adi, k_obj in kullanici_db.items():
                tablo_satirlari.append({
                    "Kullanıcı Adı": k_adi,
                    "Rol": "Admin" if k_adi == "admin" else k_obj.get("rol", "Personel"),
                    "Salt Okunur": "Evet" if k_obj.get("salt_okunur", False) else "Hayır",
                    "Maskelenen Alan Sayısı": len(k_obj.get("maskeli_alanlar", [])),
                    "Yasaklı Menüler": ", ".join(k_obj.get("yasakli_menuler", [])) or "Yok",
                    "Şifre Durumu": "Değişmesi gerekiyor" if (
                        k_obj.get("sifre_degistirilmeli") or k_obj.get("sifre", "") in ESKI_VARSAYILAN_HASHLER
                    ) else "Tamam",
                })
            st.dataframe(pd.DataFrame(tablo_satirlari), use_container_width=True, hide_index=True)

        st.markdown("---")
        bolum_basligi_goster(
            st,
            "yetki",
            "Kullanıcı Düzenle, Yetki Ver ve Alan Maskele",
            "Mevcut kullanıcıların rolünü, şifresini, gizli veri alanlarını ve menü erişimlerini yapılandırın",
            vurgu_renk="#10b981",
        )

        MASKE_SECENEKLERI = {
            "Kurumsal Dashboard": [
                ("Ürün Çeşidi", "1. Sayfa: Ürün Çeşidi"),
                ("Toplam Fire", "1. Sayfa: Toplam Fire"),
                ("Stok Değeri", "1. Sayfa: Stok Değeri"),
                ("Aktif Personel", "1. Sayfa: Aktif Personel"),
                ("Grafik Alanı", "1. Sayfa: Grafik Alanı"),
                ("Kategori Doluluk Tablosu", "1. Sayfa: Kategori Doluluk"),
                ("Depo Doluluk Tablosu", "1. Sayfa: Depo Doluluk"),
                ("Operasyonel Sağlık Tablosu", "1. Sayfa: Operasyonel Sağlık"),
            ],
            "Güncel Stok / Fire / Fiyat": [
                ("Stok - Kalan Miktar", "2. Sayfa: Güncel Stok Durumu - Kalan Miktar"),
                ("Kayıtlı Fire ve Zayiat Listesi", "2. Sayfa: Kayıtlı Fire ve Zayiatlar Listesi"),
                ("Birim Fiyat Sütunu", "2. Sayfa: Ürün Birim Fiyatları - Fiyat Sütunu"),
            ],
            "Günlük Yemek Üretimi": [
                ("Üretim ve Maliyet Arşivi", "3. Sayfa: Yemek Üretim ve Maliyet Arşivi"),
            ],
            "İhtiyaç Sahipleri Listesi": [
                ("T.C./Hane No", "4. Sayfa: İhtiyaç Sahipleri - T.C./Hane No"),
                ("Adı Soyadı", "4. Sayfa: İhtiyaç Sahipleri - Adı Soyadı"),
                ("Telefon", "4. Sayfa: İhtiyaç Sahipleri - Telefon"),
                ("Adres", "4. Sayfa: İhtiyaç Sahipleri - Adres"),
                ("Birey Sayısı", "4. Sayfa: İhtiyaç Sahipleri - Birey Sayısı"),
            ],
            "Yemek Dağıtımları": [
                ("Tarih/Saat", "4. Sayfa: Yemek Dağıtımları - Tarih/Saat"),
                ("Kişi/Hane", "4. Sayfa: Yemek Dağıtımları - Kişi/Hane"),
                ("Menü", "4. Sayfa: Yemek Dağıtımları - Menü"),
                ("Porsiyon", "4. Sayfa: Yemek Dağıtımları - Porsiyon"),
            ],
            "Dağıtım Sayaç Raporu": [
                ("T.C./Hane No", "4. Sayfa: Sayaç Raporu - T.C./Hane No"),
                ("İhtiyaç Sahibi", "4. Sayfa: Sayaç Raporu - İhtiyaç Sahibi"),
                ("Günlük Alım", "4. Sayfa: Sayaç Raporu - Günlük Alım"),
                ("Haftalık Alım", "4. Sayfa: Haftalık Alım"),
                ("Aylık Alım", "4. Sayfa: Sayaç Raporu - Aylık Alım"),
            ],
            "Hazır Yemek Reçeteleri": [
                ("Reçete Maliyet Bilgileri", "3. Sayfa: Hazır Yemek Reçeteleri - Maliyet"),
                ("Reçete Kalori Bilgileri", "3. Sayfa: Hazır Yemek Reçeteleri - Kalori"),
                ("Kayıtlı Reçete Listesi", "3. Sayfa: Hazır Yemek Reçeteleri - Liste"),
            ],
        }
        _bilinen_maskeler = {a for liste in MASKE_SECENEKLERI.values() for _, a in liste}

        yonetilebilir_kullanicilar = [k for k in kullanici_db.keys() if k != "admin"]
        if yonetilebilir_kullanicilar:
            secilen_k_adi = st.selectbox(
                "İşlem Yapılacak Kullanıcıyı Seçin",
                yonetilebilir_kullanicilar,
                index=None,
                placeholder="Kullanıcı Seçiniz...",
                key="secilen_k_ozel_mask",
            )
            if secilen_k_adi:
                k_obj = kullanici_db[secilen_k_adi]

                # Seçili kullanıcı için lüks kimlik ve güvenlik özeti kartı
                secili_rol = html.escape(str(k_obj.get("rol", "Personel")))
                secili_salt = "Salt Okunur" if k_obj.get("salt_okunur", False) else "Tam Yazma Yetkili"
                secili_maske_sayi = len(k_obj.get("maskeli_alanlar", []))
                secili_yasak_sayi = len(k_obj.get("yasakli_menuler", []))
                yetki_rozet = ikon_rozeti_html("yetki", renk="#fbbf24", boyut=40)
                st.markdown(
                    f'<div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px;'
                    f'background:linear-gradient(90deg,rgba(251,191,36,0.12) 0%,rgba(16,185,129,0.08) 100%);'
                    f'border:1px solid rgba(251,191,36,0.34);border-radius:12px;padding:12px 16px;margin:6px 0 14px 0;">'
                    f'<div style="display:flex;align-items:center;gap:12px;">{yetki_rozet}'
                    f'<div><div style="font-size:1.02rem;font-weight:800;color:#f8fafc;">{html.escape(str(secilen_k_adi))}</div>'
                    f'<div style="font-size:0.78rem;color:#94a3b8;">Rol: <strong style="color:#fbbf24;">{secili_rol}</strong> · Mod: <strong style="color:#10b981;">{secili_salt}</strong></div></div></div>'
                    f'<div style="display:flex;gap:8px;flex-wrap:wrap;">'
                    f'<span style="font-size:0.76rem;font-weight:700;color:#38bdf8;background:rgba(56,189,248,0.14);border:1px solid rgba(56,189,248,0.32);padding:4px 10px;border-radius:999px;">Maskeli Alan: {secili_maske_sayi}</span>'
                    f'<span style="font-size:0.76rem;font-weight:700;color:#f43f5e;background:rgba(244,63,94,0.14);border:1px solid rgba(244,63,94,0.32);padding:4px 10px;border-radius:999px;">Yasaklı Menü: {secili_yasak_sayi}</span>'
                    f'</div></div>',
                    unsafe_allow_html=True,
                )

                col_d1, col_d2 = st.columns(2)
                with col_d1:
                    mevcut_rol = k_obj.get("rol", "Personel")
                    rol_secenekleri = ["Personel", "Yönetim", "Misafir"]
                    rol_index = rol_secenekleri.index(mevcut_rol) if mevcut_rol in rol_secenekleri else 0
                    yeni_rol = st.selectbox("Kullanıcı Rolü", rol_secenekleri, index=rol_index, key=f"rol_ozel_{secilen_k_adi}")
                    yeni_salt_okunur = st.checkbox("Salt Okunur (veri değiştiremez)", value=k_obj.get("salt_okunur", False), key=f"ro_ozel_{secilen_k_adi}")
                with col_d2:
                    yeni_sifre_k = st.text_input("Yeni şifre belirle (boş bırakılırsa değişmez)", type="password", key=f"ysifre_{secilen_k_adi}")
                    sifre_zorunlu_k = st.checkbox("Bir sonraki girişte şifre değiştirmek zorunda olsun", value=True, key=f"szor_{secilen_k_adi}")
                kullaniciyi_sil = st.checkbox(
                    "⚠️ Bu kullanıcıyı KALICI olarak sil (işaretlemezseniz silinmez)", value=False, key=f"sil_ozel_{secilen_k_adi}"
                )

                bolum_basligi_goster(
                    st,
                    "maske",
                    "Gizlenecek (Maskelenecek) Alanlar",
                    "Seçilen kullanıcının ekranlarında '🔒 Gizli' olarak maskelenecek hassas veri alanları",
                    vurgu_renk="#38bdf8",
                )
                mevcut_maskeler = k_obj.get("maskeli_alanlar", [])
                secilen_maskeler = []
                for g_idx, (grup_adi, secenekler) in enumerate(MASKE_SECENEKLERI.items()):
                    g_ikon, g_renk = _MASKE_GRUP_IKONLARI.get(grup_adi, ("liste", "#38bdf8"))
                    g_rozet = ikon_rozeti_html(g_ikon, renk=g_renk, boyut=26)
                    st.markdown(
                        f'<div style="display:flex;align-items:center;gap:9px;margin:10px 0 6px 0;padding:5px 10px;'
                        f'background:rgba(15,23,42,0.52);border-left:3px solid {g_renk};border-radius:0 8px 8px 0;">'
                        f'{g_rozet}<span style="font-size:0.92rem;font-weight:700;color:#f8fafc;">{html.escape(grup_adi)}</span></div>',
                        unsafe_allow_html=True,
                    )
                    m_cols = st.columns(3)
                    for o_idx, (etiket, anahtar) in enumerate(secenekler):
                        with m_cols[o_idx % 3]:
                            if st.checkbox(etiket, value=(anahtar in mevcut_maskeler), key=f"mask_{secilen_k_adi}_{g_idx}_{o_idx}"):
                                secilen_maskeler.append(anahtar)
                yeni_maskeler = [m for m in mevcut_maskeler if m not in _bilinen_maskeler] + secilen_maskeler

                bolum_basligi_goster(
                    st,
                    "kilit",
                    "Sayfa / Menü Erişim Kısıtlamaları",
                    "Kullanıcının sol menüde görmesini istemediğiniz modülleri işaretleyin",
                    vurgu_renk="#f43f5e",
                )
                tum_menu_ogeleri = [m for m in gecerli_menuler if m != "Kullanıcı Ayarları"]
                mevcut_yasaklar = k_obj.get("yasakli_menuler", [])
                yeni_yasaklar = [m for m in mevcut_yasaklar if m not in tum_menu_ogeleri]
                y_cols = st.columns(2)
                for idx, m_item in enumerate(tum_menu_ogeleri):
                    with y_cols[idx % 2]:
                        if st.checkbox(m_item, value=(m_item in mevcut_yasaklar), key=f"ozel_yasak_{secilen_k_adi}_{idx}"):
                            yeni_yasaklar.append(m_item)

                if st.button("Değişiklikleri Kaydet / Uygula", type="primary", key=f"btn_ozel_kaydet_{secilen_k_adi}"):
                    if kullaniciyi_sil:
                        otomatik_yedek_al("Kullanıcı silme: " + str(secilen_k_adi))

                        # Geri al butonu için mevcut halini kaydet
                        st.session_state["son_kullanici_islem"] = {
                            "tur": "sil",
                            "kullanici_adi": secilen_k_adi,
                            "eski_obje": dict(kullanici_db[secilen_k_adi]),
                        }

                        del kullanici_db[secilen_k_adi]
                        kullanıcıları_kaydet(kullanici_db)
                        kullanici_oturumlarini_kapat(secilen_k_adi)
                        giris_logla("admin", f"kullanıcı silindi: {secilen_k_adi}")
                        st.toast(f"🗑️ '{secilen_k_adi}' kullanıcısı silindi!", icon="✅")
                        time.sleep(1)
                        st.rerun()
                    else:
                        sifre_hata = sifre_politika_hatasi(yeni_sifre_k) if yeni_sifre_k else None
                        if sifre_hata:
                            st.error(sifre_hata)
                        else:
                            otomatik_yedek_al("Kullanıcı güncelleme: " + str(secilen_k_adi))

                            # Geri al butonu için güncelleme öncesi halini kaydet
                            st.session_state["son_kullanici_islem"] = {
                                "tur": "guncelle",
                                "kullanici_adi": secilen_k_adi,
                                "eski_obje": dict(kullanici_db[secilen_k_adi]),
                            }

                            k_obj["rol"] = yeni_rol
                            k_obj["salt_okunur"] = yeni_salt_okunur
                            k_obj["maskeli_alanlar"] = yeni_maskeler
                            k_obj["yasakli_menuler"] = yeni_yasaklar
                            if yeni_sifre_k:
                                sifre_degistir(secilen_k_adi, yeni_sifre_k, zorunlu=sifre_zorunlu_k)
                            else:
                                kullanıcıları_kaydet(kullanici_db)
                            giris_logla("admin", f"kullanıcı ayarları güncellendi: {secilen_k_adi}")
                            st.toast(f"✅ '{secilen_k_adi}' ayarları kaydedildi!", icon="🎉")
                            time.sleep(1)
                            st.rerun()
        else:
            st.info("Düzenlenebilecek ek kullanıcı bulunmuyor.")

        st.markdown("---")
        bolum_basligi_goster(
            st,
            "kullanici_ekle",
            "Yeni Sistem Kullanıcısı Ekle",
            "Güçlü şifre politikasıyla yeni personel, yönetim veya misafir hesabı oluşturun",
            vurgu_renk="#a855f7",
        )
        yeni_k_adi = st.text_input("Kullanıcı Adı (3-30 karakter: harf, rakam, . _ -)", key="yeni_k_adi_input_ozel").strip().lower()
        yeni_sifre = st.text_input("Şifre (en az 10 karakter, harf ve rakam)", type="password", key="yeni_sifre_input_ozel")
        y_col1, y_col2, y_col3 = st.columns(3)
        with y_col1:
            yeni_k_rol = st.selectbox("Kullanıcı Rolü", ["Personel", "Yönetim", "Misafir"], key="yeni_rol_select_ozel")
        with y_col2:
            yeni_k_salt = st.checkbox("Salt Okunur Kullanıcı", value=False, key="yeni_salt_chk_ozel")
        with y_col3:
            yeni_k_zorunlu = st.checkbox("İlk girişte şifre değiştirsin", value=True, key="yeni_zorunlu_chk_ozel")

        if st.button("Yeni Kullanıcıyı Sisteme Ekle", type="secondary", key="btn_ozel_yeni_ekle"):
            if not re.fullmatch(r"[a-z0-9_.\-]{3,30}", yeni_k_adi or ""):
                st.error("Kullanıcı adı 3-30 karakter olmalı; yalnızca küçük harf, rakam, nokta, alt çizgi ve tire içerebilir.")
            elif yeni_k_adi in kullanici_db:
                st.error("Bu kullanıcı adı zaten sistemde mevcut!")
            elif sifre_politika_hatasi(yeni_sifre):
                st.error(sifre_politika_hatasi(yeni_sifre))
            else:
                yeni_user_data = {
                    "sifre": sifre_hashle_yeni(yeni_sifre),
                    "rol": yeni_k_rol,
                    "salt_okunur": yeni_k_salt,
                    "maskeli_alanlar": [],
                    "yasakli_menuler": [],
                    "sifre_degistirilmeli": yeni_k_zorunlu,
                }
                kullanici_db[yeni_k_adi] = yeni_user_data

                st.session_state["son_kullanici_islem"] = {
                    "tur": "ekle",
                    "kullanici_adi": yeni_k_adi,
                }

                kullanıcıları_kaydet(kullanici_db)
                giris_logla("admin", f"kullanıcı eklendi: {yeni_k_adi}")
                st.toast(f"🎉 Yeni kullanıcı '{yeni_k_adi}' eklendi!", icon="✨")
                time.sleep(1)
                st.rerun()
