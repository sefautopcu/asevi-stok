"""Login lockout transitions and callback-driven persistence orchestration."""


def giris_kilit_kalan(kayitlar, anahtar, simdi_fn):
    if not isinstance(kayitlar, dict):
        return 0
    return max(0, int(kayitlar.get(anahtar, {}).get("kilit_bitis", 0) - simdi_fn()))


def hatali_giris_kaydet(anahtar, atomik_dict_guncelle, maks=3, taban_sn=30, simdi_fn=None):
    import time

    if simdi_fn is None:
        simdi_fn = time.time
    simdi = simdi_fn()
    sonuc = {"kalan": maks, "kilit": False}

    def guncelle(kayitlar):
        guncel, kalan, kilit = hatali_giris_durumunu_guncelle(
            kayitlar, anahtar, simdi, maks, taban_sn
        )
        sonuc.update(kalan=kalan, kilit=kilit)
        return guncel

    durum, _ = atomik_dict_guncelle("giris_denemeleri", guncelle)
    if durum != "ok":
        return 0, True
    return sonuc["kalan"], sonuc["kilit"]


def hatali_giris_durumunu_guncelle(kayitlar, anahtar, simdi, maks=3, taban_sn=30):
    """Update a login-attempt map and return (map, remaining_attempts, locked)."""
    kayitlar = {
        k: v for k, v in kayitlar.items()
        if v.get("kilit_bitis", 0) > simdi or simdi - v.get("son", 0) < 3600
    }
    kayit = kayitlar.get(
        anahtar,
        {"sayi": 0, "kilit_sayisi": 0, "kilit_bitis": 0, "son": 0},
    )

    if simdi - kayit.get("son", 0) > 3600:
        kayit["sayi"] = 0
        kayit["kilit_sayisi"] = 0

    kayit["sayi"] = kayit.get("sayi", 0) + 1
    kayit["son"] = simdi
    kilit = False

    if kayit["sayi"] >= maks:
        kayit["kilit_sayisi"] = kayit.get("kilit_sayisi", 0) + 1
        sure = min(taban_sn * (2 ** (kayit["kilit_sayisi"] - 1)), 900)
        kayit["kilit_bitis"] = simdi + sure
        kayit["sayi"] = 0
        kilit = True

    kalan = max(maks - kayit["sayi"], 0)
    kayitlar[anahtar] = kayit
    return kayitlar, kalan, kilit
