import datetime
import secrets
import time
import zoneinfo
from html import escape as html_escape

from src.cekirdek import rapor_mail_durumunu_guncelle, rapor_verilerini_oku
from src.rapor_utils import rapor_donemini_hesapla

TR_AYLAR = {
    1: "Ocak",
    2: "Şubat",
    3: "Mart",
    4: "Nisan",
    5: "Mayıs",
    6: "Haziran",
    7: "Temmuz",
    8: "Ağustos",
    9: "Eylül",
    10: "Ekim",
    11: "Kasım",
    12: "Aralık",
}


def _rapor_html_metni(deger, varsayilan="-"):
    """Rapor HTML'inde kullanıcı/veritabanı kaynaklı metni güvenli biçimde gösterir."""
    return html_escape(str(varsayilan if deger is None else deger))


def _rapor_dagitim_kisi_sayisi(kayit):
    """Dağıtım kaydındaki yardım alan ihtiyaç sahibi vatandaş/porsiyon sayısını döndürür."""
    for alan in ("kisi", "kisi_sayisi", "vatandas_sayisi", "porsiyon", "miktar"):
        deger = kayit.get(alan)
        if deger not in (None, ""):
            try:
                sayi = float(deger)
                return int(sayi) if sayi.is_integer() else sayi
            except (TypeError, ValueError):
                continue
    return 0


def _rapor_menu_detay_metni(
    yemek_kaydi, yemek_menu_ogelerini_kayittan_al, yemek_menu_alanlari
):
    """Yemek üretim kaydındaki menü bölümlerini okunabilir metne çevirir."""
    menu_ogeleri = yemek_menu_ogelerini_kayittan_al(yemek_kaydi)
    parcalar = [
        f"{etiket}: {menu_ogeleri[alan]}"
        for alan, etiket in yemek_menu_alanlari()
        if menu_ogeleri.get(alan)
    ]
    if parcalar:
        return " | ".join(parcalar)
    return str(yemek_kaydi.get("yemek_adi") or "-")


def _rapor_icerigi_olustur(
    rapor_baslik,
    rapor_tarih_str,
    baslangic_str,
    bitis_str,
    supabase_ham_oku=None,
    yemek_menu_ogelerini_kayittan_al=None,
    yemek_menu_alanlari=None,
):
    """Otomatik ve manuel e-posta raporları için eksiksiz HTML rapor içeriği üretir."""
    if supabase_ham_oku is None:
        raise ValueError("supabase_ham_oku fonksiyonu sağlanmalıdır.")

    rapor_verileri = rapor_verilerini_oku(supabase_ham_oku)
    tum_girisler = rapor_verileri.get("girisler", [])
    tum_kullanim_loglari = rapor_verileri.get("kullanim_loglari", [])
    tum_silinenler = rapor_verileri.get("silinen_urun_loglari", [])
    tum_yemekler = rapor_verileri.get("yemek_uretim_arsivi", [])
    tum_izinler = rapor_verileri.get("personel_izinleri", [])

    tum_dagitimlar = rapor_verileri.get("dagitim_loglari")
    if tum_dagitimlar is None:
        _d_durum, _d_veri = supabase_ham_oku("dagitim_loglari")
        tum_dagitimlar = (
            _d_veri if (_d_durum == "ok" and isinstance(_d_veri, list)) else []
        )

    def _filtre(liste, anahtar="tarih"):
        return [
            i
            for i in liste
            if baslangic_str <= str(i.get(anahtar, ""))[:10] <= bitis_str
        ]

    secilen_girisler = _filtre(tum_girisler)
    filtreli_loglar = _filtre(tum_kullanim_loglari)
    secilen_fireler = [l for l in filtreli_loglar if l.get("tur") == "Fire/Zayiat"]
    secilen_sarfiyatlar = [
        l for l in filtreli_loglar if l.get("tur") != "Fire/Zayiat"
    ]
    secilen_silinenler = _filtre(tum_silinenler)
    secilen_yemekler = _filtre(tum_yemekler)
    secilen_dagitimlar = _filtre(tum_dagitimlar)
    secilen_izinler = [
        i
        for i in tum_izinler
        if str(i.get("baslangic", ""))
        and str(i.get("bitis", ""))
        and baslangic_str <= str(i.get("bitis", ""))
        and bitis_str >= str(i.get("baslangic", ""))
    ]

    toplam_yardim_alan = sum(
        _rapor_dagitim_kisi_sayisi(d) for d in secilen_dagitimlar
    )

    html = f"""<html><head><style>
      body {{ font-family: Arial, sans-serif; background-color: #f4f7f6; padding: 20px; }}
      .container {{ max-width: 800px; margin: 0 auto; background: #fff; padding: 30px;
                   border-radius: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); }}
      h2 {{ color: #10b981; margin-top: 0; }}
      h3 {{ color: #374151; border-bottom: 2px solid #10b981; padding-bottom: 8px; margin-top: 30px; }}
      table {{ width: 100%; border-collapse: collapse; margin: 10px 0 20px; }}
      th {{ background: #f3f4f6; padding: 12px; text-align: left; border-bottom: 2px solid #e5e7eb;
            color: #4b5563; font-size: 13px; }}
      td {{ padding: 12px; border-bottom: 1px solid #e5e7eb; font-size: 14px; color: #1f2937; }}
      .summary-table {{ width: 100%; border-collapse: separate; border-spacing: 8px 0; margin-bottom: 20px; }}
      .summary-card {{ background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px; text-align: center; }}
      .summary-title {{ font-size: 11px; color: #6b7280; text-transform: uppercase; font-weight: bold; }}
      .summary-value {{ font-size: 22px; font-weight: bold; margin-top: 5px; }}
      .yemek-box {{ background: #f9fafb; border-left: 4px solid #10b981; padding: 15px;
                    margin-bottom: 15px; border-radius: 4px; }}
    </style></head><body><div class="container">
      <h2>🍲 Aziziye Aşevi - {_rapor_html_metni(rapor_baslik)}</h2>
      <p style="color:#6b7280;font-size:15px;"><b>Tarih:</b> {_rapor_html_metni(rapor_tarih_str)}</p>
      <table class="summary-table"><tr>
        <td class="summary-card"><div class="summary-title">Stok Girişi</div><div class="summary-value" style="color:#10b981;">{len(secilen_girisler)}</div></td>
        <td class="summary-card"><div class="summary-title">Stok Sarfiyatı</div><div class="summary-value" style="color:#f59e0b;">{len(secilen_sarfiyatlar)}</div></td>
        <td class="summary-card"><div class="summary-title">Fire / Zayiat</div><div class="summary-value" style="color:#ef4444;">{len(secilen_fireler)}</div></td>
        <td class="summary-card"><div class="summary-title">Üretilen Yemek</div><div class="summary-value" style="color:#3b82f6;">{len(secilen_yemekler)}</div></td>
        <td class="summary-card"><div class="summary-title">Yardım Alan Kişi</div><div class="summary-value" style="color:#8b5cf6;">{toplam_yardim_alan}</div></td>
      </tr></table>"""

    if secilen_girisler:
        html += "<h3>📦 Gelen Stok Girişleri</h3><table><tr><th>Ürün</th><th>Miktar</th><th>Fatura No</th></tr>"
        for g in secilen_girisler:
            html += f"<tr><td>{_rapor_html_metni(g.get('urun'))}</td><td>{_rapor_html_metni(g.get('miktar'))} {_rapor_html_metni(g.get('birim', ''), '')}</td><td>{_rapor_html_metni(g.get('fatura_no'))}</td></tr>"
        html += "</table>"

    if secilen_sarfiyatlar:
        html += "<h3>🔄 Genel Stok Çıkışları / Sarfiyatlar</h3><table><tr><th>Tarih</th><th>İşlem / Açıklama</th><th>Ürün</th><th>Miktar</th><th>Tutar</th></tr>"
        for srf in secilen_sarfiyatlar:
            html += (
                f"<tr><td>{_rapor_html_metni(srf.get('tarih'))}</td>"
                f"<td>{_rapor_html_metni(srf.get('tur'))}</td>"
                f"<td>{_rapor_html_metni(srf.get('urun'))}</td>"
                f"<td>{_rapor_html_metni(srf.get('miktar'))} {_rapor_html_metni(srf.get('birim', ''), '')}</td>"
                f"<td>{float(srf.get('tutar', 0) or 0):,.2f} ₺</td></tr>"
            )
        html += "</table>"

    if secilen_fireler:
        html += "<h3>🗑️ Fire / Zayiat</h3><table><tr><th>Ürün</th><th>Fatura No</th><th>Miktar</th><th>Tutar</th><th>Açıklama</th></tr>"
        for f in secilen_fireler:
            html += f"<tr><td>{_rapor_html_metni(f.get('urun'))}</td><td>{_rapor_html_metni(f.get('fatura_no'))}</td><td>{_rapor_html_metni(f.get('miktar'))}</td><td>{float(f.get('tutar', 0) or 0):,.2f} ₺</td><td>{_rapor_html_metni(f.get('aciklama'))}</td></tr>"
        html += "</table>"

    if secilen_silinenler:
        html += "<h3>❌ Silinen Ürünler</h3><table><tr><th>Ürün</th><th>Kayıt ID</th><th>Neden</th></tr>"
        for s in secilen_silinenler:
            html += f"<tr><td>{_rapor_html_metni(s.get('urun'))}</td><td>{_rapor_html_metni(s.get('kayit_id'))}</td><td>{_rapor_html_metni(s.get('neden'))}</td></tr>"
        html += "</table>"

    if secilen_yemekler:
        html += "<h3>🍲 Üretilen Yemekler ve Menü Detayları</h3>"
        for y in secilen_yemekler:
            toplam = float(y.get("toplam_maliyet", 0) or 0)
            kisi = int(y.get("kisi_sayisi", 1) or 1)
            kisi_basi = toplam / kisi if kisi > 0 else 0
            if yemek_menu_ogelerini_kayittan_al and yemek_menu_alanlari:
                menu_detayi = _rapor_menu_detay_metni(
                    y, yemek_menu_ogelerini_kayittan_al, yemek_menu_alanlari
                )
            else:
                menu_detayi = str(y.get("yemek_adi") or "-")
            html += f"<div class='yemek-box'><h4 style='margin:0 0 8px;'>{_rapor_html_metni(y.get('tarih'))} - {_rapor_html_metni(y.get('yemek_adi'))} ({kisi} Kişilik)</h4>"
            html += f"<p style='margin:0 0 8px;font-size:13px;color:#374151;'><b>Çıkan Menü Detayı:</b> {_rapor_html_metni(menu_detayi)}</p>"
            html += f"<p style='margin:0 0 10px;font-size:14px;'><b>Toplam:</b> {toplam:,.2f} ₺ | <b>Kişi Başı:</b> {kisi_basi:,.2f} ₺</p>"
            if y.get("malzemeler"):
                html += "<table style='margin:0;'><tr><th>Kullanılan Malzeme</th><th>Miktar</th><th>Maliyet</th></tr>"
                for m in y.get("malzemeler", []):
                    html += f"<tr><td>{_rapor_html_metni(m.get('urun'))}</td><td>{_rapor_html_metni(m.get('miktar'))} {_rapor_html_metni(m.get('birim', ''), '')}</td><td>{float(m.get('tutar', 0) or 0):,.2f} ₺</td></tr>"
                html += "</table>"
            html += "</div>"

    if secilen_dagitimlar:
        html += (
            f"<h3>🤝 İhtiyaç Sahibi Yemek Dağıtımları "
            f"(Toplam {toplam_yardim_alan} Kişi / Porsiyon)</h3>"
            "<table><tr><th>Tarih</th><th>İhtiyaç Sahibi / Grup</th><th>Menü</th><th>Kişi / Porsiyon</th></tr>"
        )
        for d in secilen_dagitimlar:
            alici = (
                d.get("ad_soyad")
                or d.get("kisi_adi")
                or d.get("aciklama")
                or d.get("tur")
                or "Toplu Dağıtım"
            )
            kisi_degeri = _rapor_dagitim_kisi_sayisi(d)
            html += (
                f"<tr><td>{_rapor_html_metni(d.get('tarih'))}</td>"
                f"<td>{_rapor_html_metni(alici)}</td>"
                f"<td>{_rapor_html_metni(d.get('menu'))}</td>"
                f"<td>{_rapor_html_metni(kisi_degeri)}</td></tr>"
            )
        html += "</table>"

    if secilen_izinler:
        html += "<h3>👥 Personel İzinleri</h3><table><tr><th>Personel</th><th>Tür</th><th>Başlangıç</th><th>Bitiş</th><th>İzin Nedeni</th></tr>"
        for i in secilen_izinler:
            neden = i.get("aciklama") or i.get("detay") or "-"
            html += (
                f"<tr><td>{_rapor_html_metni(i.get('personel_ad'))}</td>"
                f"<td>{_rapor_html_metni(i.get('izin_turu'))}</td>"
                f"<td>{_rapor_html_metni(i.get('baslangic'))}</td>"
                f"<td>{_rapor_html_metni(i.get('bitis'))}</td>"
                f"<td>{_rapor_html_metni(neden)}</td></tr>"
            )
        html += "</table>"

    if not (
        secilen_girisler
        or secilen_sarfiyatlar
        or secilen_fireler
        or secilen_silinenler
        or secilen_yemekler
        or secilen_dagitimlar
        or secilen_izinler
    ):
        html += "<div style='text-align:center;padding:30px;color:#6b7280;'><b>Bu dönemde veri yok.</b></div>"

    html += "</div></body></html>"
    return html


def manuel_rapor_maili_gonder(
    rapor_tipi="gunluk",
    st=None,
    log=None,
    supabase_ham_oku=None,
    smtp_gonder=None,
    yemek_menu_ogelerini_kayittan_al=None,
    yemek_menu_alanlari=None,
):
    """Buton ile tetiklendiğinde çalışır, tarih/saat kontrolünü atlar ve veritabanına kayıt atmaz."""
    try:
        simdi = datetime.datetime.now(zoneinfo.ZoneInfo("Europe/Istanbul"))
    except Exception:
        simdi = datetime.datetime.now()
    bugun = simdi.date()

    secili_tip = rapor_tipi if rapor_tipi in ("gunluk", "haftalik", "aylik") else "aylik"
    baslangic_tarih, bitis_tarih, rapor_baslik, rapor_tarih_str = rapor_donemini_hesapla(
        bugun, secili_tip, manuel=True
    )

    baslangic_str = baslangic_tarih.strftime("%Y-%m-%d")
    bitis_str = bitis_tarih.strftime("%Y-%m-%d")

    try:
        html = _rapor_icerigi_olustur(
            rapor_baslik,
            rapor_tarih_str,
            baslangic_str,
            bitis_str,
            supabase_ham_oku=supabase_ham_oku,
            yemek_menu_ogelerini_kayittan_al=yemek_menu_ogelerini_kayittan_al,
            yemek_menu_alanlari=yemek_menu_alanlari,
        )
    except (RuntimeError, ValueError) as e:
        if log is not None:
            log.error("Manuel rapor verileri okunamadı: %s", e)
        if st is not None:
            st.error(
                "Rapor oluşturulamadı; veritabanı verileri alınamadı. Lütfen tekrar deneyin."
            )
        return False

    if smtp_gonder is None:
        return False

    if st is not None:
        with st.spinner("📤 Rapor gönderiliyor..."):
            ok, hata = smtp_gonder(
                f"Aziziye Aşevi {rapor_baslik} - {rapor_tarih_str}", html
            )
    else:
        ok, hata = smtp_gonder(
            f"Aziziye Aşevi {rapor_baslik} - {rapor_tarih_str}", html
        )

    if not ok:
        if log is not None:
            log.error("Manuel rapor hatası: %s", hata)
        return False
    return True

def _rapor_sahiplen(rapor_tipi, deger, atomik_dict_guncelle):
    """Aynı dönemin raporunu tekilleştirir ve gönderim için süreli sahiplenme alır."""
    sonuc = {"sahiplendi": False}
    claim_id = secrets.token_urlsafe(16)

    def _mutate(mevcut):
        yeni, sonuc["sahiplendi"] = rapor_mail_durumunu_guncelle(
            mevcut, rapor_tipi, deger, time.time(), "sahiplen", claim_id
        )
        return yeni

    durum, _ = atomik_dict_guncelle("mail_loglari", _mutate)
    return claim_id if durum == "ok" and sonuc["sahiplendi"] else None


def _rapor_geri_al(rapor_tipi, deger, claim_id, atomik_dict_guncelle, log=None):
    """Gönderim başarısızsa sahiplenmeyi bırak → bir sonraki tetikleme yeniden denesin."""
    def _mutate(mevcut):
        yeni, _ = rapor_mail_durumunu_guncelle(
            mevcut, rapor_tipi, deger, time.time(), "basarisiz", claim_id
        )
        return yeni

    durum, sonuc = atomik_dict_guncelle("mail_loglari", _mutate)
    if durum != "ok" and log is not None:
        log.error("Rapor gönderim durumu kaydedilemedi (basarisiz): %s", sonuc)


def _rapor_gonderim_tamamlandi(rapor_tipi, deger, claim_id, atomik_dict_guncelle, log=None):
    def _mutate(mevcut):
        yeni, _ = rapor_mail_durumunu_guncelle(
            mevcut, rapor_tipi, deger, time.time(), "tamamlandi", claim_id
        )
        return yeni

    durum, sonuc = atomik_dict_guncelle("mail_loglari", _mutate)
    if durum != "ok":
        if log is not None:
            log.error("Rapor gönderildi fakat durumu kaydedilemedi: %s", sonuc)
        return False
    return True
