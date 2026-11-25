"""Data transformations for sensitive entity fields; storage stays in the app layer."""


def ihtiyac_sahiplerini_coz(ham_veri, metni_coz):
    cozulmus_liste = []
    for kayit in ham_veri:
        kopya = kayit.copy()
        hane = kayit.get("tc_hane", "")
        telefon = kayit.get("telefon", "")
        adres = kayit.get("adres", "")
        kopya["tc_hane"] = metni_coz(hane) if hane else ""
        kopya["telefon"] = metni_coz(telefon) if telefon else ""
        kopya["adres"] = metni_coz(adres) if adres else ""
        if "aktif" not in kopya:
            kopya["aktif"] = True
        cozulmus_liste.append(kopya)
    return cozulmus_liste


def ihtiyac_sahiplerini_sifrele(veri_listesi, metni_sifrele):
    sifrelenmis_liste = []
    for kayit in veri_listesi:
        kopya = kayit.copy()
        kopya["tc_hane"] = metni_sifrele(kayit.get("tc_hane", ""))
        kopya["telefon"] = metni_sifrele(kayit.get("telefon", ""))
        kopya["adres"] = metni_sifrele(kayit.get("adres", ""))
        sifrelenmis_liste.append(kopya)
    return sifrelenmis_liste


def personelleri_coz(ham_veri, metni_coz):
    cozulmus = []
    for personel in ham_veri:
        kopya = personel.copy()
        tc = personel.get("tc", "")
        kopya["tc"] = metni_coz(tc) if tc else ""
        cozulmus.append(kopya)
    return cozulmus


def personelleri_sifrele(veri_listesi, metni_sifrele):
    sifrelenmis = []
    for personel in veri_listesi:
        kopya = personel.copy()
        kopya["tc"] = metni_sifrele(personel.get("tc", ""))
        sifrelenmis.append(kopya)
    return sifrelenmis
