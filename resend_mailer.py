import os
import logging
import resend

logger = logging.getLogger(__name__)

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
EMAIL_FROM = os.environ.get("EMAIL_FROM", "CrewLog <noreply@crewlog.app>")


EMAIL_SUBJECTS = {
    "de": "CrewLog Passwort zurücksetzen",
    "en": "Reset your CrewLog password",
}

EMAIL_BODY_HTML = {
    "de": """<!DOCTYPE html>
<html><head><meta charset="utf-8"></head><body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 480px; margin: 0 auto; padding: 24px; color: #1a2f4a;">
<div style="text-align: center; margin-bottom: 24px;">
<h2 style="margin: 0; color: #1a2f4a;">CrewLog</h2>
</div>
<p>Hallo,</p>
<p>wir haben eine Anfrage zum Zurücksetzen deines Passworts erhalten. Klicke auf den folgenden Link, um ein neues Passwort zu setzen:</p>
<p style="text-align: center; margin: 32px 0;">
<a href="{reset_url}" style="background: #1a2f4a; color: #fff; padding: 12px 32px; border-radius: 8px; text-decoration: none; font-weight: 600; display: inline-block;">Passwort zurücksetzen</a>
</p>
<p style="font-size: 13px; color: #6b7280;">Dieser Link ist 60 Minuten gültig. Falls du kein Zurücksetzen angefordert hast, kannst du diese E-Mail ignorieren.</p>
<p style="font-size: 13px; color: #6b7280;">Falls der Button nicht funktioniert, kopiere diesen Link in deinen Browser:</p>
<p style="font-size: 12px; color: #9ca3af; word-break: break-all;">{reset_url}</p>
<hr style="border: none; border-top: 1px solid #e5e7eb; margin: 24px 0;">
<p style="font-size: 12px; color: #9ca3af; text-align: center;">CrewLog — Maritime Logbook &amp; Bordkasse</p>
</body></html>""",
    "en": """<!DOCTYPE html>
<html><head><meta charset="utf-8"></head><body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 480px; margin: 0 auto; padding: 24px; color: #1a2f4a;">
<div style="text-align: center; margin-bottom: 24px;">
<h2 style="margin: 0; color: #1a2f4a;">CrewLog</h2>
</div>
<p>Hello,</p>
<p>We received a request to reset your password. Click the link below to set a new password:</p>
<p style="text-align: center; margin: 32px 0;">
<a href="{reset_url}" style="background: #1a2f4a; color: #fff; padding: 12px 32px; border-radius: 8px; text-decoration: none; font-weight: 600; display: inline-block;">Reset Password</a>
</p>
<p style="font-size: 13px; color: #6b7280;">This link is valid for 60 minutes. If you didn't request a password reset, you can safely ignore this email.</p>
<p style="font-size: 13px; color: #6b7280;">If the button doesn't work, copy this link into your browser:</p>
<p style="font-size: 12px; color: #9ca3af; word-break: break-all;">{reset_url}</p>
<hr style="border: none; border-top: 1px solid #e5e7eb; margin: 24px 0;">
<p style="font-size: 12px; color: #9ca3af; text-align: center;">CrewLog — Maritime Logbook &amp; Bordkasse</p>
</body></html>""",
}

EMAIL_BODY_TEXT = {
    "de": """CrewLog — Passwort zurücksetzen

Hallo,

wir haben eine Anfrage zum Zurücksetzen deines Passworts erhalten.
Öffne den folgenden Link, um ein neues Passwort zu setzen:

{reset_url}

Dieser Link ist 60 Minuten gültig.
Falls du kein Zurücksetzen angefordert hast, kannst du diese E-Mail ignorieren.

CrewLog — Maritime Logbook & Bordkasse""",
    "en": """CrewLog — Password Reset

Hello,

We received a request to reset your password.
Open the following link to set a new password:

{reset_url}

This link is valid for 60 minutes.
If you didn't request a password reset, you can safely ignore this email.

CrewLog — Maritime Logbook & Bordkasse""",
}


def send_password_reset(email: str, reset_url: str, locale: str = "de") -> bool:
    if not RESEND_API_KEY:
        logger.error("RESEND_API_KEY not configured — cannot send password reset email")
        return False

    resend.api_key = RESEND_API_KEY

    subject = EMAIL_SUBJECTS.get(locale, EMAIL_SUBJECTS["de"])
    html = EMAIL_BODY_HTML.get(locale, EMAIL_BODY_HTML["de"]).format(reset_url=reset_url)
    text = EMAIL_BODY_TEXT.get(locale, EMAIL_BODY_TEXT["de"]).format(reset_url=reset_url)

    try:
        resend.Emails.send({
            "from": EMAIL_FROM,
            "to": [email],
            "subject": subject,
            "html": html,
            "text": text,
        })
        logger.info("Password reset email sent to %s", email)
        return True
    except Exception as e:
        logger.error("Failed to send password reset email to %s: %s", email, e)
        return False
