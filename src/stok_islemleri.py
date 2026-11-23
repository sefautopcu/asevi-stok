"""Pure stock movement calculations used by inventory workflows."""


def _fifo_dus(kayitlar, miktar, maliyeti_hesapla):
    kalan_dusulecek = miktar
    harcanan_tutar = 0.0
    dusulen_kayitlar = []
    for kayit in kayitlar:
        if kalan_dusulecek <= 0:
            break
        kayit_kalan = float(kayit["kalan"])
        if kayit_kalan > 0:
            if kayit_kalan >= kalan_dusulecek:
                dusulen = kalan_dusulecek
                kayit["kalan"] = kayit_kalan - kalan_dusulecek
                kalan_dusulecek = 0
            else:
                dusulen = kayit_kalan
                kayit["kalan"] = 0.0
                kalan_dusulecek -= kayit_kalan
            dusulen_kayitlar.append({"id": kayit["id"], "miktar": dusulen})
            if maliyeti_hesapla:
                harcanan_tutar += dusulen * float(kayit["fiyat"])
    return harcanan_tutar, dusulen_kayitlar


def fifo_sarfiyat_dus_detayli(kayitlar, miktar):
    """Consume ordered lots in place and return cost plus per-lot breakdown."""
    return _fifo_dus(kayitlar, miktar, maliyeti_hesapla=True)


def fifo_miktar_dus_detayli(kayitlar, miktar):
    """Consume ordered lots in place and return per-lot breakdown only."""
    _, dusulen = _fifo_dus(kayitlar, miktar, maliyeti_hesapla=False)
    return dusulen


def fifo_sarfiyat_dus(kayitlar, miktar):
    """Consume an amount from ordered lots and return its cost only."""
    harcanan_tutar, _ = fifo_sarfiyat_dus_detayli(kayitlar, miktar)
    return harcanan_tutar
