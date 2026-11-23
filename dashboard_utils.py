"""Pure calculations for dashboard summary metrics and stock composition."""
import datetime


def dashboard_ozet_hesapla(girisler, kullanim_loglari, personeller, depolar):
    urun_cesidi_sayisi = len({
        kayit.get("urun", "").strip().upper()
        for kayit in girisler if kayit.get("urun")
    })
    toplam_stok_degeri = sum(
        float(kayit.get("kalan", 0)) * float(kayit.get("fiyat", 0))
        for kayit in girisler
    )
    fireler = [log for log in kullanim_loglari if log.get("tur") == "Fire/Zayiat"]
    toplam_fire_kg = sum(float(log.get("miktar", 0)) for log in fireler)
    toplam_fire_tl = sum(float(log.get("tutar", 0)) for log in fireler)
    aktif_personel_sayisi = sum(1 for personel in personeller if personel.get("aktif", True))

    gida_toplam = sum(
        float(k.get("kalan", 0)) * float(k.get("fiyat", 0))
        for k in girisler if k.get("kategori") == "KURU GIDA"
    )
    sebze_toplam = sum(
        float(k.get("kalan", 0)) * float(k.get("fiyat", 0))
        for k in girisler if k.get("kategori") == "SEBZE"
    )
    yag_toplam = sum(
        float(k.get("kalan", 0)) * float(k.get("fiyat", 0))
        for k in girisler if k.get("kategori") == "YAĞ"
    )
    genel_toplam = toplam_stok_degeri if toplam_stok_degeri > 0 else 1
    yuzde_gida = int((gida_toplam / genel_toplam) * 100)
    yuzde_sebze = int((sebze_toplam / genel_toplam) * 100)
    yuzde_yag = int((yag_toplam / genel_toplam) * 100)

    depo_doluluk = {}
    for depo in depolar:
        depo_toplam = sum(
            float(k.get("kalan", 0)) * float(k.get("fiyat", 0))
            for k in girisler if k.get("depo") == depo
        )
        depo_doluluk[depo] = int((depo_toplam / genel_toplam) * 100)

    return {
        "urun_cesidi_sayisi": urun_cesidi_sayisi,
        "toplam_stok_degeri": toplam_stok_degeri,
        "toplam_fire_kg": toplam_fire_kg,
        "toplam_fire_tl": toplam_fire_tl,
        "aktif_personel_sayisi": aktif_personel_sayisi,
        "gida_toplam": gida_toplam,
        "sebze_toplam": sebze_toplam,
        "yag_toplam": yag_toplam,
        "genel_toplam": genel_toplam,
        "yuzde_gida": yuzde_gida,
        "yuzde_sebze": yuzde_sebze,
        "yuzde_yag": yuzde_yag,
        "depo_doluluk": depo_doluluk,
        "sirali_depolar": sorted(depo_doluluk.items(), key=lambda item: item[1], reverse=True)[:3],
    }


def dashboard_operasyonel_istatistikleri(
    girisler, kritik_seviyeleri, dagitim_loglari, urun_cesidi_sayisi, bugun_tarih
):
    """Calculate critical-stock, expiry, and recent distribution dashboard indicators."""
    urunler = set(
        kayit.get("urun", "").strip().upper()
        for kayit in girisler if kayit.get("urun")
    )
    kritik_urun_sayisi = 0
    for urun in urunler:
        toplam_kalan = sum(
            float(kayit.get("kalan", 0))
            for kayit in girisler
            if kayit.get("urun", "").strip().upper() == urun
        )
        ozel_sinir = kritik_seviyeleri.get(urun, 10.0)
        if toplam_kalan <= float(ozel_sinir):
            kritik_urun_sayisi += 1

    guvenli_urun_sayisi = (
        urun_cesidi_sayisi - kritik_urun_sayisi
        if urun_cesidi_sayisi > kritik_urun_sayisi else 0
    )
    skt_kirmizi = 0
    skt_turuncu = 0
    for urun in urunler:
        skt_listesi = [
            kayit.get("skt") for kayit in girisler
            if kayit.get("urun", "").strip().upper() == urun and kayit.get("skt")
        ]
        en_yakin_skt = min(skt_listesi) if skt_listesi else None
        if en_yakin_skt:
            try:
                skt_date = datetime.datetime.strptime(en_yakin_skt, "%Y-%m-%d").date()
                kalan_gun = (skt_date - bugun_tarih).days
                if kalan_gun < 0:
                    skt_kirmizi += 1
                elif kalan_gun <= 7:
                    skt_turuncu += 1
            except Exception:
                pass

    yuzde_kritik = (
        int((kritik_urun_sayisi / urun_cesidi_sayisi) * 100)
        if urun_cesidi_sayisi > 0 else 0
    )
    yuzde_guvenli = 100 - yuzde_kritik

    aylik_dagitim = {}
    for kayit in dagitim_loglari:
        if len(kayit.get("tarih", "")) >= 7:
            ay = kayit["tarih"][:7]
            aylik_dagitim[ay] = aylik_dagitim.get(ay, 0) + int(kayit.get("porsiyon", 1))

    son_5_ay = sorted(aylik_dagitim.keys())[-5:]
    while len(son_5_ay) < 5:
        son_5_ay.insert(0, f"2026-{len(son_5_ay)+1:02d}")
    aylar_tr = {
        "01": "Oca", "02": "Şub", "03": "Mar", "04": "Nis", "05": "May",
        "06": "Haz", "07": "Tem", "08": "Ağu", "09": "Eyl", "10": "Eki",
        "11": "Kas", "12": "Ara",
    }
    maks_dag = max([aylik_dagitim.get(ay, 0) for ay in son_5_ay] + [1])
    aylik_barlar_html = ""
    for ay in son_5_ay:
        deger = aylik_dagitim.get(ay, 0)
        yuzde = max(10, int((deger / maks_dag) * 100))
        aylik_barlar_html += f"""
            <div style="flex: 1; display: flex; flex-direction: column; justify-content: flex-end; align-items: center; height: 100%;">
                <div style="font-size: 12px; color: #10b981; font-weight: bold; margin-bottom: 5px;">{deger}</div>
                <div style="width: 80%; background: linear-gradient(180deg, #10b981 0%, #059669 100%); border-radius: 6px 6px 0 0; height: {yuzde}%;"></div>
                <div style="font-size: 11px; color: #94a3b8; margin-top: 8px;">{aylar_tr.get(ay[-2:], ay)}</div>
            </div>
        """
    return {
        "kritik_urun_sayisi": kritik_urun_sayisi,
        "guvenli_urun_sayisi": guvenli_urun_sayisi,
        "skt_kirmizi": skt_kirmizi,
        "skt_turuncu": skt_turuncu,
        "yuzde_kritik": yuzde_kritik,
        "yuzde_guvenli": yuzde_guvenli,
        "aylik_barlar_html": aylik_barlar_html,
    }
