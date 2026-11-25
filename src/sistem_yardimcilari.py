# src/sistem_yardimcilari.py
import io
import os
import base64
import datetime
import zoneinfo
import smtplib
import streamlit as st
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from PIL import Image, ImageOps

def secret_deger(anahtar, varsayilan=""):
    """Secrets dosyası yokken veya anahtar tanımlı değilken güvenli varsayılan döndürür."""
    try:
        return st.secrets.get(anahtar, varsayilan)
    except Exception:
        return varsayilan

def simdi_tr_str(format_str="%Y-%m-%d %H:%M"):
    """Gerçek Türkiye saatini (Europe/Istanbul) döndürür."""
    try:
        return datetime.datetime.now(zoneinfo.ZoneInfo("Europe/Istanbul")).strftime(format_str)
    except Exception:
        return datetime.datetime.now().strftime(format_str)

def bugunun_turkce_tarihi():
    try:
        simdi = datetime.datetime.now(zoneinfo.ZoneInfo("Europe/Istanbul")).date()
    except Exception:
        simdi = datetime.date.today()
    aylar = {1: "Ocak", 2: "Şubat", 3: "Mart", 4: "Nisan", 5: "Mayıs", 6: "Haziran", 7: "Temmuz", 8: "Ağustos", 9: "Eylül", 10: "Ekim", 11: "Kasım", 12: "Aralık"}
    gunler = {0: "Pazartesi", 1: "Salı", 2: "Çarşamba", 3: "Perşembe", 4: "Cuma", 5: "Cumartesi", 6: "Pazar"}
    return f"{simdi.day} {aylar.get(simdi.month, '')} {simdi.year}, {gunler.get(simdi.weekday(), '')}"

def bellek_kullanimi_al():
    """Python sürecinin sunucuda kullandığı anlık RAM miktarını (MB) hesaplar."""
    try:
        import psutil
        process = psutil.Process(os.getpid())
        return round(process.memory_info().rss / (1024 * 1024), 1)
    except Exception:
        return 0.0

def _dashboard_arka_plan_data_uri(yuklenen_resim):
    from PIL import Image, ImageOps
    try:
        with Image.open(io.BytesIO(yuklenen_resim.getvalue())) as acilan_resim:
            resim = ImageOps.exif_transpose(acilan_resim)
            resim.thumbnail((1920, 1080), Image.Resampling.LANCZOS)
            if "A" in resim.getbands() or "transparency" in resim.info:
                rgba = resim.convert("RGBA")
                optimize_edilmis = Image.new("RGB", rgba.size, "#08131F")
                optimize_edilmis.paste(rgba, mask=rgba.getchannel("A"))
            else:
                optimize_edilmis = resim.convert("RGB")

            cikti = io.BytesIO()
            optimize_edilmis.save(cikti, format="JPEG", quality=85, optimize=True)
    except (OSError, ValueError, Image.DecompressionBombError) as exc:
        raise ValueError("Görsel okunamadı. Lütfen geçerli bir JPG veya PNG seçin.") from exc

    b64 = base64.b64encode(cikti.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{b64}"

def _dashboard_arka_plan_yukleme_callback():
    yuklenen_resim = st.session_state.get("dashboard_bg_uploader")
    if yuklenen_resim is None:
        return
    try:
        st.session_state.dashboard_arka_plan = _dashboard_arka_plan_data_uri(
            yuklenen_resim
        )
    except ValueError as exc:
        st.session_state["_dashboard_bg_upload_error"] = str(exc)
        return
    st.session_state["_dashboard_bg_upload_success"] = True

def _smtp_gonder_senkron(konu, html_icerik):
    """Sadece SMTP. Streamlit API'sine DOKUNMAZ. (basarili, hata_mesaji)."""
    try:
        sender = secret_deger("MAIL_SENDER", "")
        password = secret_deger("MAIL_PASSWORD", "")
        recipient = secret_deger("MAIL_RECIPIENT", "")
        server_adresi = secret_deger("MAIL_SERVER", "smtp.gmail.com")
        port = int(secret_deger("MAIL_PORT", 587))

        msg = MIMEMultipart()
        msg["From"] = formataddr(("Aziziye Aşevi Otomasyon", sender))
        msg["To"] = recipient
        msg["Subject"] = konu
        msg.attach(MIMEText(html_icerik, "html", "utf-8"))

        with smtplib.SMTP(server_adresi, port, timeout=10) as server:
            server.starttls()
            server.login(sender, password)
            server.send_message(msg)
        return True, ""
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"
