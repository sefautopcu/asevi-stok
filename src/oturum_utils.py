"""Session-record operations with storage, clock, and token providers injected."""
import hashlib
import secrets
import time


def bosta_kalma_suresi_sn(deger):
    """Parse configured idle timeout, defaulting to 30 minutes and clamping 5–480."""
    try:
        dakika = int(str(deger))
    except Exception:
        dakika = 30
    return max(5, min(dakika, 480)) * 60


def token_hashle(token):
    return hashlib.sha256(str(token).encode("utf-8")).hexdigest()


def oturum_olustur(
    kullanici_adi, oturum_suresi_sn, atomik_dict_guncelle, veritabani_hatasi_dur,
    simdi_fn=time.time, token_fn=secrets.token_urlsafe,
):
    token = token_fn(32)
    simdi = simdi_fn()
    bitis = simdi + oturum_suresi_sn

    def ekle(oturumlar):
        oturumlar = {
            digest: kayit for digest, kayit in oturumlar.items()
            if kayit.get("bitis", 0) > simdi
        }
        oturumlar[token_hashle(token)] = {"kullanici": kullanici_adi, "bitis": bitis}
        return oturumlar

    durum, sonuc = atomik_dict_guncelle("aktif_oturumlar", ekle)
    if durum != "ok":
        veritabani_hatasi_dur(f"oturum oluşturulamadı ({sonuc})")
    return token, bitis


def oturum_dogrula(token, veri_oku, simdi_fn=time.time):
    if not token:
        return None
    oturumlar = veri_oku("aktif_oturumlar", {}, kritik=False)
    if not isinstance(oturumlar, dict):
        return None
    kayit = oturumlar.get(token_hashle(token))
    if kayit and kayit.get("bitis", 0) > simdi_fn():
        return kayit
    return None


def oturum_sil(token, atomik_dict_guncelle):
    if not token:
        return
    digest = token_hashle(token)

    def sil(oturumlar):
        oturumlar.pop(digest, None)
        return oturumlar

    atomik_dict_guncelle("aktif_oturumlar", sil)


def kullanici_oturumlarini_kapat(kullanici, atomik_dict_guncelle, haric_token=None):
    haric = token_hashle(haric_token) if haric_token else None

    def filtrele(oturumlar):
        return {
            digest: kayit for digest, kayit in oturumlar.items()
            if kayit.get("kullanici") != kullanici or digest == haric
        }

    atomik_dict_guncelle("aktif_oturumlar", filtrele)
