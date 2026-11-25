"""Legacy personnel-leave migration transformations, without Streamlit or I/O."""
import datetime


ESKI_IZIN_TURU_ESLEME = {
    "Yıllık İzin": "Yıllık İzin",
    "Sağlık Raporu": "Hastalık / Rapor",
    "Saatlik İzin": "Mazeret İzni",
}


def eski_izinleri_donustur(personeller, mevcut_izinler, yeni_id_uret, tarih_etiketi_uret):
    """Move legacy embedded leaves into the current list, in place; return whether changed."""
    anahtarlar = {
        (i.get("personel_ad"), i.get("izin_turu"), i.get("baslangic"), i.get("bitis"), i.get("aciklama"))
        for i in mevcut_izinler if i.get("kaynak") == "eski_kayit"
    }
    degisti = False
    for personel in personeller:
        eskiler = personel.get("izinler") or []
        if not eskiler:
            continue
        ad = personel.get("ad_soyad", personel.get("ad", personel.get("isim", "-")))
        for izin in eskiler:
            eski_tur = izin.get("tur", "Yıllık İzin")
            tur = ESKI_IZIN_TURU_ESLEME.get(eski_tur, "Resmi Görev / Diğer")
            bas = str(izin.get("baslangic", ""))
            bit = str(izin.get("bitis", bas))
            try:
                gun = (datetime.date.fromisoformat(bit) - datetime.date.fromisoformat(bas)).days + 1
            except Exception:
                gun = 0
            kayit_saat = None
            if eski_tur == "Saatlik İzin":
                kayit_saat = izin.get("saat", 0)
                gun = 0
                aciklama = f"Saatlik izin: {kayit_saat} saat ({izin.get('detay', '-')})"
            else:
                aciklama = str(izin.get("detay") or "Eski sistemden aktarıldı")
            anahtar = (ad, tur, bas, bit, aciklama)
            if anahtar in anahtarlar:
                continue
            yeni = {
                "id": yeni_id_uret("IZN-", mevcut_izinler),
                "personel_ad": ad,
                "izin_turu": tur,
                "baslangic": bas,
                "bitis": bit,
                "gun_sayisi": max(gun, 0),
                "aciklama": aciklama,
                "ekleme_tarihi": tarih_etiketi_uret(),
                "kaynak": "eski_kayit",
            }
            if kayit_saat is not None:
                yeni["saat"] = kayit_saat
            mevcut_izinler.append(yeni)
            anahtarlar.add(anahtar)
        personel["izinler"] = []
        degisti = True
    return degisti
