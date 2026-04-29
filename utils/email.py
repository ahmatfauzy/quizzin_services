import resend
from config.settings import settings

resend.api_key = settings.RESEND_API_KEY

def send_verification_email(to_email: str, token: str):
    if not settings.RESEND_API_KEY:
        print(f"Skipping email send. RESEND_API_KEY not set. Token: {token}")
        return False
        
    verification_link = f"{settings.URL_BASE}/auth/verify-email?token={token}"
    
    html_content = f"""
    <h2>Verifikasi Email Kamu</h2>
    <p>Halo,</p>
    <p>Terima kasih telah mendaftar di <strong>{settings.RESEND_SENDER_NAME}</strong>. Silakan klik tombol di bawah ini untuk memverifikasi alamat email kamu:</p>
    <br>
    <a href="{verification_link}" style="display:inline-block;padding:12px 24px;color:white;background-color:#007BFF;text-decoration:none;border-radius:5px;font-weight:bold;">Verifikasi Email</a>
    <br><br>
    <p>Atau kamu bisa copy-paste tautan berikut ke browsermu:</p>
    <p><a href="{verification_link}">{verification_link}</a></p>
    <p>Tautan ini akan kedaluwarsa dalam 24 jam.</p>
    <p>Jika kamu tidak merasa mendaftar, silakan abaikan email ini.</p>
    """
    
    params = {
        "from": f"{settings.RESEND_SENDER_NAME} <{settings.RESEND_SENDER_EMAIL}>",
        "to": [to_email],
        "subject": "Verifikasi Email Pendaftaran",
        "html": html_content,
    }
    
    try:
        email = resend.Emails.send(params)
        print("Email sent successfully!")
        return True
    except Exception as e:
        print("Failed to send email:", e)
        return False
