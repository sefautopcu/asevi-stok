"""Synchronous SMTP delivery with injected configuration and transport."""
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr


def smtp_gonder(konu, html_icerik, ayarlar, smtp_factory):
    """Send one HTML message and return (success, error_message)."""
    try:
        sender = ayarlar["MAIL_SENDER"]
        password = ayarlar["MAIL_PASSWORD"]
        recipient = ayarlar["MAIL_RECIPIENT"]
        server_adresi = ayarlar.get("MAIL_SERVER", "smtp.gmail.com")
        port = int(ayarlar.get("MAIL_PORT", 587))

        msg = MIMEMultipart()
        msg["From"] = formataddr(("Aziziye Aşevi Otomasyon", sender))
        msg["To"] = recipient
        msg["Subject"] = konu
        msg.attach(MIMEText(html_icerik, "html", "utf-8"))

        with smtp_factory(server_adresi, port, timeout=10) as server:
            server.starttls()
            server.login(sender, password)
            server.send_message(msg)
        return True, ""
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"
