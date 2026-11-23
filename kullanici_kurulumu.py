"""Initial account creation with injectable secret and password providers."""
import secrets


def varsayilan_kullanicilari_olustur(
    secret_oku, sifre_hashle_yeni, sifre_politika_hatasi, misafir_kaydi_uret,
    rastgele_sifre_uret=None,
):
    """Return (accounts, generated_plaintext_passwords) for first-run setup."""
    if rastgele_sifre_uret is None:
        rastgele_sifre_uret = lambda: secrets.token_urlsafe(9)

    kayit = {}
    uretilenler = {}
    for ad, tip, salt_okunur, secret_adi in (
        ("admin", "admin", False, "ADMIN_INITIAL_PASSWORD"),
        ("asci", "personel", False, "ASCI_INITIAL_PASSWORD"),
        ("yonetim", "personel", True, "YONETIM_INITIAL_PASSWORD"),
    ):
        try:
            sifre = str(secret_oku(secret_adi) or "")
        except Exception:
            sifre = ""

        rastgele = False
        if not sifre:
            sifre = rastgele_sifre_uret()
            uretilenler[ad] = sifre
            rastgele = True
            uygun = True
        else:
            uygun = not sifre_politika_hatasi(sifre)

        kayit[ad] = {
            "sifre": sifre_hashle_yeni(sifre),
            "tip": tip,
            "yasakli_menuler": [],
            "maskeli_alanlar": [],
            "salt_okunur": salt_okunur,
        }
        if rastgele or not uygun:
            kayit[ad]["sifre_degistirilmeli"] = True

    kayit["misafir"] = misafir_kaydi_uret()
    return kayit, uretilenler
