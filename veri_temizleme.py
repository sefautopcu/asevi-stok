"""Pure helpers for identifying disposable test records."""


def test_kayitlarini_ayikla(kayitlar, alanlar):
    """Return records without the substring 'test' in any configured field."""
    kalanlar = []
    silinen_sayisi = 0
    for kayit in kayitlar:
        if any("test" in str(kayit.get(alan, "")).lower() for alan in alanlar):
            silinen_sayisi += 1
        else:
            kalanlar.append(kayit)
    return kalanlar, silinen_sayisi
