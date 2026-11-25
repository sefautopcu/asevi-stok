"""Pure normalization for persisted user permission records."""


def kullanicilari_normallestir(
    data,
    misafir_yasaklar,
    misafir_maskeler,
    varsayilan_misafir,
    sifre_hashle_yeni,
):
    """Apply legacy permission and password migrations in place, matching app behavior."""
    for kullanici, kayit in data.items():
        if "yasakli_menuler" not in kayit:
            kayit["yasakli_menuler"] = []
        if "maskeli_alanlar" not in kayit:
            kayit["maskeli_alanlar"] = []
        if "salt_okunur" not in kayit:
            kayit["salt_okunur"] = kullanici in ["yonetim", "misafir"]
        elif kullanici in ["yonetim", "misafir"]:
            kayit["salt_okunur"] = True

        if kullanici == "misafir":
            if not kayit["yasakli_menuler"]:
                kayit["yasakli_menuler"] = misafir_yasaklar
            if not kayit["maskeli_alanlar"]:
                kayit["maskeli_alanlar"] = misafir_maskeler

        sifre = kayit.get("sifre", "")
        if (
            sifre
            and kullanici != "misafir"
            and not str(sifre).startswith("s1$")
            and len(str(sifre)) != 64
        ):
            kayit["sifre"] = sifre_hashle_yeni(sifre)

    if "misafir" not in data:
        data["misafir"] = varsayilan_misafir
    else:
        misafir = data["misafir"]
        if "buton_metni" not in misafir:
            misafir["buton_metni"] = "👁️ Misafir Girişi İçin Tıklayın (Gözlemci)"
        if "buton_aktif" not in misafir:
            misafir["buton_aktif"] = True
        if not misafir["yasakli_menuler"]:
            misafir["yasakli_menuler"] = misafir_yasaklar
        if not misafir["maskeli_alanlar"]:
            misafir["maskeli_alanlar"] = misafir_maskeler
    return data
