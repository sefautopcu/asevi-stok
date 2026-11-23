import time

def kullanici_islemi_geri_al_alani(st, kullanici_db, otomatik_yedek_al, kullanıcıları_kaydet, giris_logla):
    # SON İŞLEMİ GERİ AL (UNDO) MEKANİZMASI
    # ------------------------------------------------------------------
    if st.session_state.get("son_kullanici_islem"):
        son_islem = st.session_state["son_kullanici_islem"]
        islem_turu = son_islem.get("tur")
        k_adi_hedef = son_islem.get("kullanici_adi")

        c_undo1, c_undo2 = st.columns([3, 1])
        with c_undo1:
            if islem_turu == "sil":
                st.info(f"💡 **Son İşlem:** '{k_adi_hedef}' kullanıcısı silindi.")
            elif islem_turu == "ekle":
                st.info(f"💡 **Son İşlem:** '{k_adi_hedef}' kullanıcısı eklendi.")
            elif islem_turu == "guncelle":
                st.info(f"💡 **Son İşlem:** '{k_adi_hedef}' kullanıcısının ayarları/yetkileri değiştirildi.")

        with c_undo2:
            if st.button("↩️ Son İşlemi Geri Al", type="secondary", key="btn_undo_kullanici_islem"):
                otomatik_yedek_al("Kullanıcı işlemi geri alma: " + str(islem_turu))

                if islem_turu == "sil":
                    # Silinen kullanıcıyı ve detaylarını geri yükle
                    eski_obj = son_islem.get("eski_obje")
                    if eski_obj:
                        kullanici_db[k_adi_hedef] = eski_obj
                elif islem_turu == "ekle":
                    # Yeni eklenen kullanıcıyı sil
                    if k_adi_hedef in kullanici_db:
                        del kullanici_db[k_adi_hedef]
                elif islem_turu == "guncelle":
                    # Eski yetki/maske ayarlarına geri dön; ANCAK mevcut şifre korunur
                    # (güncelleme şifre değiştirmişse, geri alma eski/ele geçirilmiş şifreyi geri getirmesin).
                    eski_obj = son_islem.get("eski_obje")
                    if eski_obj:
                        eski_obj = dict(eski_obj)
                        if k_adi_hedef in kullanici_db:
                            eski_obj["sifre"] = kullanici_db[k_adi_hedef].get("sifre", eski_obj.get("sifre", ""))
                            if kullanici_db[k_adi_hedef].get("sifre_degistirilmeli"):
                                eski_obj["sifre_degistirilmeli"] = True
                            else:
                                eski_obj.pop("sifre_degistirilmeli", None)
                        kullanici_db[k_adi_hedef] = eski_obj

                kullanıcıları_kaydet(kullanici_db)
                giris_logla("admin", f"kullanıcı işlemi geri alındı: {islem_turu} ({k_adi_hedef})")
                st.session_state.pop("son_kullanici_islem", None)
                st.toast(f"🎉 '{k_adi_hedef}' üzerindeki son işlem geri alındı!", icon="✅")
                time.sleep(1)
                st.rerun()

    # ------------------------------------------------------------------
