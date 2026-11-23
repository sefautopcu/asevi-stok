"""Pure stock-table shaping for the current inventory report."""
import datetime


def stok_urun_adlari_olustur(girisler):
    return sorted(
        list(set(g.get("urun", "").strip().upper() for g in girisler if g.get("urun")))
    )


def stok_excel_liste_olustur(girisler, aktif_k_maskeleri):
    urunler = stok_urun_adlari_olustur(girisler)
    excel_liste = []
    for urun in urunler:
        ilgili = [g for g in girisler if g.get("urun", "").strip().upper() == urun]
        toplam = sum(float(g.get("kalan", 0)) for g in ilgili)
        sirali = sorted(ilgili, key=lambda x: str(x.get("tarih", "")), reverse=True)
        devreden = toplam - float(sirali[0].get("kalan", 0)) if len(sirali) > 1 else 0.0
        maskele = "2. Sayfa: Güncel Stok Durumu - Kalan Miktar" in aktif_k_maskeleri
        skt_listesi = [g.get("skt") for g in ilgili if g.get("skt")]
        excel_liste.append({
            "Ürün Adı": urun,
            "Kategori": ilgili[0].get("kategori", "GENEL"),
            "Birim": ilgili[0].get("birim", "Kg"),
            "Güncel Stok Miktarı": "🔒 Gizli" if maskele else toplam,
            "Devreden Bakiye": "🔒 Gizli" if maskele else devreden,
            "En Yakın SKT / STT": min(skt_listesi) if skt_listesi else "Belirtilmemiş",
            "Depo Yeri": ilgili[0].get("depo", "Merkez Depo"),
            "Son İşlem Tarihi": ilgili[-1].get("tarih", "-"),
            "Son İşlemi Yapan": ilgili[-1].get("islem_yapan", "admin"),
        })
    return urunler, excel_liste


def stok_gorunum_listeleri_olustur(
    girisler, kritik_seviyeler, aktif_k_maskeleri, secilen_depo, bugun
):
    urunler = stok_urun_adlari_olustur(girisler)
    stok_tablosu = []
    kritik_urunler_tablosu = []
    maskele = "2. Sayfa: Güncel Stok Durumu - Kalan Miktar" in aktif_k_maskeleri

    for urun in urunler:
        ilgili = [g for g in girisler if g.get("urun", "").strip().upper() == urun]
        toplam = sum(float(g.get("kalan", 0)) for g in ilgili)
        sirali = sorted(ilgili, key=lambda x: str(x.get("tarih", "")), reverse=True)
        devreden = toplam - float(sirali[0].get("kalan", 0)) if len(sirali) > 1 else 0.0
        kategori = ilgili[0].get("kategori", "GENEL")
        birim = ilgili[0].get("birim", "Kg")
        depo = ilgili[0].get("depo", "Merkez Depo")
        islem_yapan = ilgili[-1].get("islem_yapan", "admin")
        en_son_tarih = ilgili[-1].get("tarih", "-")
        skt_listesi = [g.get("skt") for g in ilgili if g.get("skt")]
        en_yakin_skt = min(skt_listesi) if skt_listesi else "Belirtilmemiş"
        skt_gosterim = en_yakin_skt
        if en_yakin_skt != "Belirtilmemiş":
            try:
                skt_date = datetime.datetime.strptime(en_yakin_skt, "%Y-%m-%d").date()
                kalan_gun = (skt_date - bugun).days
                if kalan_gun < 0:
                    skt_gosterim = f"🔴 {en_yakin_skt} (Süresi Geçti)"
                elif kalan_gun <= 7:
                    skt_gosterim = f"🟠 {en_yakin_skt} ({kalan_gun} Gün Kaldı)"
                else:
                    skt_gosterim = f"🟢 {en_yakin_skt}"
            except Exception:
                pass

        if secilen_depo == "Tümü" or depo == secilen_depo:
            stok_tablosu.append({
                "Ürün Adı": urun,
                "Kategori": kategori,
                "Birim": birim,
                "Güncel Stok Miktarı": "🔒 Gizli" if maskele else toplam,
                "Devreden Bakiye": "🔒 Gizli" if maskele else devreden,
                "SKT / STT": skt_gosterim,
                "Depo Yeri": depo,
                "Son Giriş Tarihi": en_son_tarih,
                "İşlemi Yapan": islem_yapan,
            })

        kritik_esik = kritik_seviyeler.get(urun, 10.0)
        if toplam <= float(kritik_esik) and not maskele:
            kritik_urunler_tablosu.append({
                "Ürün Adı": urun,
                "Kalan Miktar": f"{toplam} {birim}",
                "Kritik Eşik Sınırı": f"{kritik_esik} {birim}",
                "Depo Yeri": depo,
            })

    return urunler, stok_tablosu, kritik_urunler_tablosu
