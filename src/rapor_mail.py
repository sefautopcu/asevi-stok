"""Scheduled report-email orchestration, independent of Streamlit and I/O."""
from .rapor_utils import rapor_donemini_hesapla


def zamanlanmis_rapor_maili_gonder(
    simdi,
    resmi_tatil,
    rapor_sahiplen,
    rapor_geri_al,
    rapor_icerigi_olustur,
    smtp_gonder,
    log,
):
    """Run the scheduled report flow using existing persistence and SMTP callbacks."""
    bugun = simdi.date()
    bugun_str = str(bugun)

    if bugun.day == 1:
        rapor_tipi, rapor_degeri = "aylik", bugun_str[:7]
    elif bugun.weekday() == 0:
        rapor_tipi, rapor_degeri = "haftalik", bugun_str
    elif not resmi_tatil:
        rapor_tipi, rapor_degeri = "gunluk", bugun_str
    else:
        return False

    if not rapor_sahiplen(rapor_tipi, rapor_degeri):
        return False

    bas, bit, baslik, tarih_str = rapor_donemini_hesapla(bugun, rapor_tipi)

    try:
        html = rapor_icerigi_olustur(
            baslik,
            tarih_str,
            bas.strftime("%Y-%m-%d"),
            bit.strftime("%Y-%m-%d"),
        )
        konu = f"Aziziye Aşevi {baslik} - {tarih_str}"
        ok, hata = smtp_gonder(konu, html)
    except Exception as exc:
        ok, hata = False, f"{type(exc).__name__}: {exc}"

    if not ok:
        rapor_geri_al(rapor_tipi, rapor_degeri)
        log.error("Rapor maili hatası (%s): %s", rapor_tipi, hata)
        return False
    return True
