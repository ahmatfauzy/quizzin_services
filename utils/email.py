import resend
from config.settings import settings

resend.api_key = settings.RESEND_API_KEY


def _send_email(to_email: str, subject: str, html_content: str) -> bool:
    if not settings.RESEND_API_KEY:
        print(f"Skipping email. RESEND_API_KEY not set. Subject: {subject}")
        return False

    params = {
        "from": f"{settings.RESEND_SENDER_NAME} <{settings.RESEND_SENDER_EMAIL}>",
        "to": [to_email],
        "subject": subject,
        "html": html_content,
    }
    try:
        resend.Emails.send(params)
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False


def send_verification_email(to_email: str, token: str):
    web_link = f"{settings.URL_BASE}/auth/verify-email?token={token}"
    app_link = f"quizzin://verify-email?token={token}"
    html = f"""
    <h2>Verifikasi Email</h2>
    <p>Halo,</p>
    <p>Terima kasih telah mendaftar di <strong>{settings.RESEND_SENDER_NAME}</strong>.</p>
    <p>Klik tombol di bawah untuk verifikasi alamat email kamu:</p>
    <br>
    <a href="{web_link}" style="display:inline-block;padding:12px 24px;color:white;background-color:#007BFF;text-decoration:none;border-radius:5px;font-weight:bold;">Verifikasi Email</a>
    <br><br>
    <p>Atau buka link berikut di browser:</p>
    <p><a href="{web_link}">{web_link}</a></p>
    <p>Tautan berlaku 24 jam.</p>
    <hr>
    <p style="font-size:12px;color:#888;">Link aplikasi: <a href="{app_link}">{app_link}</a></p>
    """
    return _send_email(to_email, "Verifikasi Email Pendaftaran", html)


def send_password_reset_email(to_email: str, token: str):
    web_link = f"{settings.URL_BASE}/auth/reset-password?token={token}"
    app_link = f"quizzin://reset-password?token={token}"
    html = f"""
    <h2>Reset Password</h2>
    <p>Halo,</p>
    <p>Kami menerima permintaan reset password untuk akunmu di <strong>{settings.RESEND_SENDER_NAME}</strong>.</p>
    <p>Klik tombol di bawah untuk membuat password baru:</p>
    <br>
    <a href="{web_link}" style="display:inline-block;padding:12px 24px;color:white;background-color:#007BFF;text-decoration:none;border-radius:5px;font-weight:bold;">Reset Password</a>
    <br><br>
    <p>Atau buka link berikut di browser:</p>
    <p><a href="{web_link}">{web_link}</a></p>
    <p>Tautan berlaku 24 jam.</p>
    <p>Jika kamu tidak meminta reset, abaikan email ini.</p>
    <hr>
    <p style="font-size:12px;color:#888;">Link aplikasi: <a href="{app_link}">{app_link}</a></p>
    """
    return _send_email(to_email, "Reset Password", html)
