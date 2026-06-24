import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.workers.celery_app import celery_app
from app.core.config import settings


def _send_email(to: str, subject: str, html_body: str):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.EMAIL_FROM
    msg["To"] = to
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.sendmail(settings.EMAIL_FROM, to, msg.as_string())


@celery_app.task(name="email.send_verification", bind=True, max_retries=3)
def send_verification_email(self, to: str, full_name: str, token: str):
    try:
        verify_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"
        html = f"""
        <h2>Welcome to Atlas, {full_name}!</h2>
        <p>Click the link below to verify your email address:</p>
        <a href="{verify_url}">Verify Email</a>
        <p>This link expires in 24 hours.</p>
        """
        _send_email(to, "Verify your Atlas account", html)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=2**self.request.retries)


@celery_app.task(name="email.send_password_reset", bind=True, max_retries=3)
def send_password_reset_email(self, to: str, full_name: str, token: str):
    try:
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
        html = f"""
        <h2>Atlas Password Reset</h2>
        <p>Hi {full_name}, you requested a password reset.</p>
        <a href="{reset_url}">Reset Password</a>
        <p>This link expires in 1 hour. If you didn't request this, ignore this email.</p>
        """
        _send_email(to, "Reset your Atlas password", html)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=2**self.request.retries)
