"""Helpers for safely rendering database values in HTML reports."""
from html import escape
import datetime


def tablo_html_olustur(veri_listesi):
    """Render a list of dictionaries as an escaped HTML table."""
    if not veri_listesi:
        return ""

    headers = list(veri_listesi[0].keys())
    html = "<table class='custom-table'><thead><tr>"
    for header in headers:
        html += f"<th>{escape(str(header))}</th>"
    html += "</tr></thead><tbody>"

    for row in veri_listesi:
        html += "<tr>"
        for header in headers:
            html += f"<td>{escape(str(row.get(header, '')))}</td>"
        html += "</tr>"
    return html + "</tbody></table>"


def html_guvenli(value):
    """Convert arbitrary values to escaped HTML text (never markup)."""
    return escape("" if value is None else str(value), quote=True)


def benzersiz_urun_adlari(girisler):
    """Return normalized sorted product names as the price-analysis selector does."""
    return sorted(
        set(
            kayit.get("urun", "").strip().upper()
            for kayit in girisler
            if kayit.get("urun")
        )
    )


def urun_fiyat_analizi_olustur(urun_kayitlari, fiyat_gizli=False):
    """Build display and export rows while keeping their existing shape distinct."""
    gorunum, disari_aktarim = [], []
    for kayit in urun_kayitlari:
        fiyat = kayit.get("fiyat", 0)
        gosterilen_fiyat = "🔒 Gizli" if fiyat_gizli else f"{fiyat:,.2f} ₺"
        gorunum.append({
            "Alım Tarihi": kayit.get("tarih", "-"),
            "Fatura No": kayit.get("fatura_no", "-"),
            "Depo": kayit.get("depo", "-"),
            "Miktar": f"{kayit.get('miktar', 0)} {kayit.get('birim', 'Kg')}",
            "Birim Fiyat": gosterilen_fiyat,
            "İşlemi Yapan": kayit.get("islem_yapan", "admin"),
        })
        disari_aktarim.append({
            "Alım Tarihi": kayit.get("tarih", "-"),
            "Fatura No": kayit.get("fatura_no", "-"),
            "Depo": kayit.get("depo", "-"),
            "Miktar": kayit.get("miktar", 0),
            "Birim Fiyat (TL)": fiyat,
            "İşlemi Yapan": kayit.get("islem_yapan", "admin"),
        })
    return gorunum, disari_aktarim


def kapsamli_envanter_liste_olustur(girisler):
    """Build the display/export rows for the comprehensive inventory report."""
    return [
        {
            "Kayıt ID": kayit.get("id", "-"),
            "Tarih": kayit.get("tarih", "-"),
            "Fatura No": kayit.get("fatura_no", "-"),
            "Ürün Adı": kayit.get("urun", "-"),
            "Kategori": kayit.get("kategori", "-"),
            "Depo": kayit.get("depo", "-"),
            "Alınan Miktar": f"{kayit.get('miktar', 0)} {kayit.get('birim', 'Kg')}",
            "Kalan Miktar": f"{kayit.get('kalan', 0)} {kayit.get('birim', 'Kg')}",
            "Birim Fiyat": f"{kayit.get('fiyat', 0):,.2f} ₺",
            "Toplam Değer": f"{(kayit.get('kalan', 0) * kayit.get('fiyat', 0)):,.2f} ₺",
            "İşlemi Yapan": kayit.get("islem_yapan", "admin"),
        }
        for kayit in girisler
    ]


def rapor_donemini_hesapla(bugun, rapor_tipi, manuel=False):
    """Return a report's date bounds, title, and display date for a given day."""
    if rapor_tipi == "gunluk":
        baslangic = bitis = bugun - datetime.timedelta(days=1)
        ad = "Günlük"
        tarih = baslangic.strftime("%d.%m.%Y")
    elif rapor_tipi == "haftalik":
        baslangic = bugun - datetime.timedelta(days=7)
        bitis = bugun - datetime.timedelta(days=1)
        ad = "Haftalık"
        tarih = f"{baslangic.strftime('%d.%m.%Y')} - {bitis.strftime('%d.%m.%Y')}"
    else:
        ilk_gun = bugun.replace(day=1)
        gecen_ay_son_gun = ilk_gun - datetime.timedelta(days=1)
        baslangic = gecen_ay_son_gun.replace(day=1)
        bitis = gecen_ay_son_gun
        ad = "Aylık"
        tarih = baslangic.strftime("%B %Y")

    baslik = f"{ad} Rapor{' (Manuel)' if manuel else ''}"
    return baslangic, bitis, baslik, tarih


def rapor_verilerini_filtrele(
    girisler, kullanim_loglari, silinenler, yemekler, izinler,
    baslangic, bitis,
):
    """Select report rows by date range without depending on Streamlit or I/O."""
    def tarihe_gore(liste, anahtar="tarih"):
        return [oge for oge in liste if baslangic <= str(oge.get(anahtar, ""))[:10] <= bitis]

    secilen_izinler = []
    for izin in izinler:
        izin_baslangic = str(izin.get("baslangic", ""))
        izin_bitis = str(izin.get("bitis", ""))
        if izin_baslangic and izin_bitis and baslangic <= izin_bitis and bitis >= izin_baslangic:
            secilen_izinler.append(izin)

    return {
        "girisler": tarihe_gore(girisler),
        "fireler": [
            oge for oge in tarihe_gore(kullanim_loglari)
            if oge.get("tur") == "Fire/Zayiat"
        ],
        "silinenler": tarihe_gore(silinenler),
        "yemekler": tarihe_gore(yemekler),
        "izinler": secilen_izinler,
    }


def rapor_verilerini_yukle_ve_filtrele(ham_oku, baslangic, bitis):
    """Load and normalize report sources through an injected raw-read callback."""
    anahtarlar = (
        "girisler",
        "kullanim_loglari",
        "silinen_urun_loglari",
        "yemek_uretim_arsivi",
        "personel_izinleri",
    )
    kaynaklar = []
    for anahtar in anahtarlar:
        _, veri = ham_oku(anahtar)
        kaynaklar.append(veri if isinstance(veri, list) else [])
    return rapor_verilerini_filtrele(*kaynaklar, baslangic, bitis)


def rapor_html_olustur(
    rapor_baslik, rapor_tarih_str, secilen_girisler, secilen_fireler,
    secilen_silinenler, secilen_yemekler, secilen_izinler,
):
    """Render report HTML from selected records without I/O or Streamlit."""
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
      .summary-table {{ width: 100%; border-collapse: separate; border-spacing: 10px 0; margin-bottom: 20px; }}
      .summary-card {{ background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 15px; text-align: center; }}
      .summary-title {{ font-size: 12px; color: #6b7280; text-transform: uppercase; font-weight: bold; }}
      .summary-value {{ font-size: 24px; font-weight: bold; margin-top: 5px; }}
      .yemek-box {{ background: #f9fafb; border-left: 4px solid #10b981; padding: 15px;
                    margin-bottom: 15px; border-radius: 4px; }}
    </style></head><body><div class="container">
      <h2>🍲 Aziziye Aşevi - {html_guvenli(rapor_baslik)}</h2>
      <p style="color:#6b7280;font-size:15px;"><b>Tarih:</b> {html_guvenli(rapor_tarih_str)}</p>
      <table class="summary-table"><tr>
        <td class="summary-card"><div class="summary-title">Yeni Stok Girişi</div><div class="summary-value" style="color:#10b981;">{len(secilen_girisler)}</div></td>
        <td class="summary-card"><div class="summary-title">Fire / Zayiat</div><div class="summary-value" style="color:#ef4444;">{len(secilen_fireler)}</div></td>
        <td class="summary-card"><div class="summary-title">Üretilen Yemek</div><div class="summary-value" style="color:#3b82f6;">{len(secilen_yemekler)}</div></td>
      </tr></table>"""

    if secilen_girisler:
        html += "<h3>📦 Gelen Stok Girişleri</h3><table><tr><th>Ürün</th><th>Miktar</th><th>Fatura No</th></tr>"
        for row in secilen_girisler:
            html += f"<tr><td>{html_guvenli(row.get('urun'))}</td><td>{html_guvenli(row.get('miktar'))} {html_guvenli(row.get('birim', ''))}</td><td>{html_guvenli(row.get('fatura_no'))}</td></tr>"
        html += "</table>"

    if secilen_fireler:
        html += "<h3>🗑️ Fire / Zayiat</h3><table><tr><th>Ürün</th><th>Miktar</th><th>Tutar</th><th>Açıklama</th></tr>"
        for row in secilen_fireler:
            html += f"<tr><td>{html_guvenli(row.get('urun'))}</td><td>{html_guvenli(row.get('miktar'))}</td><td>{row.get('tutar', 0):,.2f} ₺</td><td>{html_guvenli(row.get('aciklama', '-'))}</td></tr>"
        html += "</table>"

    if secilen_silinenler:
        html += "<h3>❌ Silinen Ürünler</h3><table><tr><th>Ürün</th><th>Kayıt ID</th><th>Neden</th></tr>"
        for row in secilen_silinenler:
            html += f"<tr><td>{html_guvenli(row.get('urun'))}</td><td>{html_guvenli(row.get('kayit_id'))}</td><td>{html_guvenli(row.get('neden'))}</td></tr>"
        html += "</table>"

    if secilen_yemekler:
        html += "<h3>🍲 Üretilen Yemekler</h3>"
        for row in secilen_yemekler:
            toplam = float(row.get("toplam_maliyet", 0))
            kisi = int(row.get("kisi_sayisi", 1) or 1)
            kisi_basi = toplam / kisi if kisi > 0 else 0
            html += f"<div class='yemek-box'><h4 style='margin:0 0 10px;'>{html_guvenli(row.get('tarih'))} - {html_guvenli(row.get('yemek_adi'))} ({kisi} Kişilik)</h4>"
            html += f"<p style='margin:0 0 10px;font-size:14px;'><b>Toplam:</b> {toplam:,.2f} ₺ | <b>Kişi Başı:</b> {kisi_basi:,.2f} ₺</p>"
            if row.get("malzemeler"):
                html += "<table style='margin:0;'><tr><th>Malzeme</th><th>Miktar</th><th>Maliyet</th></tr>"
                for ingredient in row.get("malzemeler", []):
                    html += f"<tr><td>{html_guvenli(ingredient.get('urun'))}</td><td>{html_guvenli(ingredient.get('miktar'))} {html_guvenli(ingredient.get('birim', ''))}</td><td>{ingredient.get('tutar', 0):,.2f} ₺</td></tr>"
                html += "</table>"
            html += "</div>"

    if secilen_izinler:
        html += "<h3>👥 Personel İzinleri</h3><table><tr><th>Personel</th><th>Tür</th><th>Başlangıç</th><th>Bitiş</th></tr>"
        for row in secilen_izinler:
            html += f"<tr><td>{html_guvenli(row.get('personel_ad'))}</td><td>{html_guvenli(row.get('izin_turu'))}</td><td>{html_guvenli(row.get('baslangic'))}</td><td>{html_guvenli(row.get('bitis'))}</td></tr>"
        html += "</table>"

    if not (secilen_girisler or secilen_fireler or secilen_silinenler or secilen_yemekler or secilen_izinler):
        html += "<div style='text-align:center;padding:30px;color:#6b7280;'><b>Bu dönemde veri yok.</b></div>"

    return html + "</div></body></html>"


def manuel_rapor_html_olustur(
    rapor_baslik, rapor_tarih_str, secilen_girisler, secilen_fireler,
    secilen_silinenler, secilen_yemekler, secilen_izinler,
):
    """Render the manual-mail template without Streamlit or I/O."""
    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; background-color: #f4f7f6; padding: 20px; }}
            .container {{ max-width: 800px; margin: 0 auto; background-color: #ffffff; padding: 30px; border-radius: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); }}
            h2 {{ color: #10b981; margin-top: 0; }}
            h3 {{ color: #374151; border-bottom: 2px solid #10b981; padding-bottom: 8px; margin-top: 30px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 10px; margin-bottom: 20px; }}
            th {{ background-color: #f3f4f6; padding: 12px; text-align: left; border-bottom: 2px solid #e5e7eb; color: #4b5563; font-size: 13px; }}
            td {{ padding: 12px; border-bottom: 1px solid #e5e7eb; font-size: 14px; color: #1f2937; }}
            .summary-table {{ width: 100%; border-collapse: separate; border-spacing: 10px 0; margin-bottom: 20px; }}
            .summary-card {{ background: #ffffff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 15px; text-align: center; width: 33%; }}
            .summary-title {{ font-size: 12px; color: #6b7280; text-transform: uppercase; font-weight: bold; }}
            .summary-value {{ font-size: 24px; font-weight: bold; margin-top: 5px; }}
            .yemek-box {{ background: #f9fafb; border-left: 4px solid #10b981; padding: 15px; margin-bottom: 15px; border-radius: 4px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h2>🍲 Aziziye Aşevi - {html_guvenli(rapor_baslik)}</h2>
            <p style="color: #6b7280; font-size: 15px;"><b>Tarih:</b> {html_guvenli(rapor_tarih_str)}</p>
            <table class="summary-table"><tr>
                <td class="summary-card"><div class="summary-title">Yeni Stok Girişi</div><div class="summary-value" style="color: #10b981;">{len(secilen_girisler)}</div></td>
                <td class="summary-card"><div class="summary-title">Fire / Zayiat</div><div class="summary-value" style="color: #ef4444;">{len(secilen_fireler)}</div></td>
                <td class="summary-card"><div class="summary-title">Üretilen Yemek</div><div class="summary-value" style="color: #3b82f6;">{len(secilen_yemekler)}</div></td>
            </tr></table>
    """
    if secilen_girisler:
        html += "<h3>📦 Gelen Stok Girişleri</h3><table><tr><th>Ürün</th><th>Miktar</th><th>Fatura No</th></tr>"
        for row in secilen_girisler:
            html += f"<tr><td>{html_guvenli(row.get('urun'))}</td><td>{html_guvenli(row.get('miktar'))} {html_guvenli(row.get('birim', ''))}</td><td>{html_guvenli(row.get('fatura_no'))}</td></tr>"
        html += "</table>"
    if secilen_fireler:
        html += "<h3>🗑️ Fire / Zayiat Girişleri</h3><table><tr><th>Ürün</th><th>Miktar</th><th>Tutar</th><th>Açıklama</th></tr>"
        for row in secilen_fireler:
            html += f"<tr><td>{html_guvenli(row.get('urun'))}</td><td>{html_guvenli(row.get('miktar'))}</td><td>{row.get('tutar', 0):,.2f} ₺</td><td>{html_guvenli(row.get('aciklama', '-'))}</td></tr>"
        html += "</table>"
    if secilen_yemekler:
        html += "<h3>🍲 Üretilen Yemekler</h3>"
        for row in secilen_yemekler:
            toplam_maliyet = float(row.get('toplam_maliyet', 0))
            kisi = int(row.get('kisi_sayisi', 1) or 1)
            kisi_basi = toplam_maliyet / kisi if kisi > 0 else 0
            html += f"<div class='yemek-box'><h4 style='margin: 0 0 10px 0; color: #111827;'>{html_guvenli(row.get('tarih'))} - {html_guvenli(row.get('yemek_adi'))} ({kisi} Kişilik)</h4>"
            html += f"<p style='margin: 0 0 10px 0; font-size: 14px; color: #4b5563;'><b>Toplam Maliyet:</b> {toplam_maliyet:,.2f} ₺ | <b>Kişi Başı:</b> {kisi_basi:,.2f} ₺</p></div>"
    if secilen_izinler:
        html += "<h3>👥 Personel İzinleri</h3><table><tr><th>Personel</th><th>İzin Türü</th><th>Başlangıç</th><th>Bitiş</th></tr>"
        for row in secilen_izinler:
            html += f"<tr><td>{html_guvenli(row.get('personel_ad'))}</td><td>{html_guvenli(row.get('izin_turu'))}</td><td>{html_guvenli(row.get('baslangic'))}</td><td>{html_guvenli(row.get('bitis'))}</td></tr>"
        html += "</table>"
    if not (secilen_girisler or secilen_fireler or secilen_silinenler or secilen_yemekler or secilen_izinler):
        html += "<div style='text-align: center; padding: 30px; color: #6b7280;'><b>Bu dönemde sisteme girilmiş herhangi bir veri bulunmamaktadır.</b></div>"
    return html + "</div></body></html>"
