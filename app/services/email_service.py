"""
Servicio de Email para envío de correos de recuperación de contraseña.
Usa smtplib con configuración por variables de entorno.

- Clientes: el link usa custom URI scheme (nocturnalbar://reset-password?token=...)
  para abrir directamente la app móvil.
- Empleados: el link apunta a la URL del admin web (FRONTEND_URL/admin/reset-password?token=...).
"""
import os
import base64
import smtplib
import ssl
import time
import logging
from urllib.parse import quote
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from pathlib import Path
from fastapi import HTTPException
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

logger = logging.getLogger("EmailService")

SMTP_HOST     = os.getenv("SMTP_HOST", "")
SMTP_PORT     = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER     = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM     = os.getenv("SMTP_FROM") or SMTP_USER or "noreply@nocturnalbar.com"
FRONTEND_URL  = os.getenv("FRONTEND_URL", "http://localhost:3000")
CORE_PUBLIC_URL = os.getenv("CORE_PUBLIC_URL", FRONTEND_URL)
MOBILE_APP_SCHEME = os.getenv("MOBILE_APP_SCHEME", "nocturnalbar://")

# Path to the bar logo (relative to this file's location, two levels up)
_LOGO_PATH = Path(__file__).parent.parent.parent.parent / "LOGO_NORCTURAL_BAR.png"


def _email_configurado() -> bool:
    return bool(SMTP_HOST and SMTP_USER and SMTP_PASSWORD)


def _load_logo_bytes() -> bytes | None:
    """Try to load the bar logo as bytes. Returns None if unavailable."""
    try:
        if _LOGO_PATH.exists():
            return _LOGO_PATH.read_bytes()
    except Exception as exc:
        logger.warning(f"Could not load logo from {_LOGO_PATH}: {exc}")
    return None


# ─── HTML Templates ──────────────────────────────────────────────────────────

def _build_html_cliente(reset_link: str, has_logo: bool) -> str:
    logo_block = ""
    if has_logo:
        logo_block = """
        <img src="cid:nocturnal_logo" alt="Nocturnal Bar"
             style="max-width:160px; height:auto; display:block; margin:0 auto 24px auto;" />
"""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Reset Your Password — Nocturnal Bar</title>
</head>
<body style="margin:0;padding:0;background-color:#0F131C;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#0F131C;padding:40px 16px;">
    <tr>
      <td align="center">
        <!-- Card -->
        <table width="100%" cellpadding="0" cellspacing="0"
               style="max-width:520px;background-color:#1C1F29;border-radius:24px;
                      border:1px solid #31353F;overflow:hidden;">

          <!-- Header gradient band -->
          <tr>
            <td style="background:linear-gradient(135deg,#FF6B00 0%,#A04100 100%);
                       padding:32px 32px 24px 32px;text-align:center;">
              {logo_block}
              <p style="margin:0;font-size:11px;font-weight:700;letter-spacing:5px;
                         color:rgba(255,255,255,0.6);text-transform:uppercase;">
                NOCTURNAL BAR
              </p>
              <h1 style="margin:8px 0 0 0;font-size:28px;font-weight:900;
                          color:#FFFFFF;letter-spacing:2px;">
                Password Reset
              </h1>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:36px 36px 28px 36px;">
              <p style="margin:0 0 16px 0;font-size:16px;line-height:1.6;color:#DFE2EF;">
                Hey there, Nocturnal guest!
              </p>
              <p style="margin:0 0 24px 0;font-size:15px;line-height:1.7;color:#B0B5C5;">
                Someone (hopefully you 😉) requested a password reset for your
                <strong style="color:#FFB693;">Nocturnal Bar</strong> account.
                Tap the button below — it'll open the app directly so you can
                set your new password right away.
              </p>

              <!-- CTA Button -->
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td align="center" style="padding:8px 0 28px 0;">
                    <a href="{reset_link}"
                       style="display:inline-block;background:linear-gradient(135deg,#FF6B00,#FFB693);
                              color:#350F00;text-decoration:none;font-size:15px;font-weight:800;
                              letter-spacing:1.5px;padding:16px 40px;border-radius:14px;
                              text-transform:uppercase;">
                      RESET MY PASSWORD
                    </a>
                  </td>
                </tr>
              </table>

              <!-- Divider -->
              <hr style="border:none;border-top:1px solid #31353F;margin:0 0 24px 0;" />

              <!-- Expiry notice -->
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td width="36" valign="top" style="padding-top:2px;">
                    <div style="width:32px;height:32px;border-radius:50%;
                                background:rgba(255,107,0,0.12);text-align:center;
                                line-height:32px;font-size:16px;">
                      ⏱
                    </div>
                  </td>
                  <td style="padding-left:12px;">
                    <p style="margin:0;font-size:13px;color:#B0B5C5;line-height:1.6;">
                      This link expires in <strong style="color:#FFB693;">30 minutes</strong>.
                      After that, you'll need to request a new one from the app.
                    </p>
                  </td>
                </tr>
                <tr><td colspan="2" height="16"></td></tr>
                <tr>
                  <td width="36" valign="top" style="padding-top:2px;">
                    <div style="width:32px;height:32px;border-radius:50%;
                                background:rgba(255,107,0,0.12);text-align:center;
                                line-height:32px;font-size:16px;">
                      🔒
                    </div>
                  </td>
                  <td style="padding-left:12px;">
                    <p style="margin:0;font-size:13px;color:#B0B5C5;line-height:1.6;">
                      If you didn't request this, you can safely ignore this email.
                      Your password won't change unless you tap the button above.
                    </p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background-color:#181B25;padding:20px 36px;border-top:1px solid #31353F;">
              <p style="margin:0;font-size:11px;color:#6B7280;text-align:center;line-height:1.6;">
                © Nocturnal Bar &amp; Lounge — All rights reserved.<br />
                This is an automated message. Please do not reply.
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""


def _build_html_empleado(reset_link: str, has_logo: bool) -> str:
    logo_block = ""
    if has_logo:
        logo_block = """
        <img src="cid:nocturnal_logo" alt="Nocturnal Bar"
             style="max-width:140px; height:auto; display:block; margin:0 auto 20px auto;" />
"""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Staff Password Reset — Nocturnal Bar</title>
</head>
<body style="margin:0;padding:0;background-color:#F3F4F6;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#F3F4F6;padding:40px 16px;">
    <tr>
      <td align="center">
        <!-- Card -->
        <table width="100%" cellpadding="0" cellspacing="0"
               style="max-width:540px;background-color:#FFFFFF;border-radius:16px;
                      box-shadow:0 4px 24px rgba(0,0,0,0.10);overflow:hidden;">

          <!-- Header -->
          <tr>
            <td style="background:#0F131C;padding:32px 36px 24px 36px;text-align:center;">
              {logo_block}
              <p style="margin:0;font-size:10px;font-weight:700;letter-spacing:5px;
                         color:rgba(255,182,147,0.7);text-transform:uppercase;">
                NOCTURNAL BAR — STAFF PORTAL
              </p>
              <h1 style="margin:8px 0 0 0;font-size:24px;font-weight:800;
                          color:#FFFFFF;letter-spacing:1px;">
                Password Reset Request
              </h1>
            </td>
          </tr>

          <!-- Orange accent line -->
          <tr>
            <td height="4"
                style="background:linear-gradient(90deg,#FF6B00,#FFB693,#FF6B00);
                       font-size:0;line-height:0;">
              &nbsp;
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:36px 36px 28px 36px;">
              <p style="margin:0 0 16px 0;font-size:16px;font-weight:700;color:#111827;">
                Hello, Nocturnal Staff Member,
              </p>
              <p style="margin:0 0 20px 0;font-size:15px;line-height:1.7;color:#374151;">
                A password reset was requested for your staff account on the
                <strong>Nocturnal Bar Management System</strong>.
                Click the button below to set a new password.
              </p>
              <p style="margin:0 0 28px 0;font-size:14px;line-height:1.7;color:#6B7280;">
                For your security, this link is single-use and will expire in
                <strong style="color:#FF6B00;">30 minutes</strong>.
                If you did not make this request, please contact your
                system administrator immediately.
              </p>

              <!-- CTA Button -->
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td align="center" style="padding:8px 0 32px 0;">
                    <a href="{reset_link}"
                       style="display:inline-block;background:#0F131C;
                              color:#FFB693;text-decoration:none;font-size:14px;
                              font-weight:700;letter-spacing:1.5px;padding:16px 40px;
                              border-radius:10px;text-transform:uppercase;
                              border:2px solid #FF6B00;">
                      RESET STAFF PASSWORD
                    </a>
                  </td>
                </tr>
              </table>

              <!-- Security box -->
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td style="background:#FFF7ED;border-left:4px solid #FF6B00;
                             border-radius:0 8px 8px 0;padding:16px 20px;">
                    <p style="margin:0;font-size:13px;color:#92400E;line-height:1.6;">
                      <strong>Security notice:</strong> Nocturnal Bar will never ask you
                      for your password by email, phone or chat. This email was sent
                      automatically because a reset was requested.
                    </p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background:#F9FAFB;padding:20px 36px;
                       border-top:1px solid #E5E7EB;">
              <p style="margin:0;font-size:11px;color:#9CA3AF;
                         text-align:center;line-height:1.6;">
                © Nocturnal Bar &amp; Lounge — Management System<br />
                This is an automated message. Please do not reply to this email.
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""


# ─── Main send function ───────────────────────────────────────────────────────

def enviar_email_reset_password(email_destino: str, token: str, tipo: str = "empleado"):
    """
    Envía el correo de recuperación de contraseña.
    tipo: 'empleado' | 'cliente'

    Clientes → deep-link a la app móvil (nocturnalbar://reset-password?token=...)
    Empleados → enlace web al panel de administración
    """
    if not _email_configurado():
        logger.warning(
            "SMTP no configurado. Token de reset generado pero no enviado por email. "
            f"Token: {token[:8]}... para {email_destino}"
        )
        # En desarrollo, retorna sin error para poder usar el token por logs
        return

    # ── Build reset link ──────────────────────────────────────────────────────
    if tipo == "cliente":
        # Use an HTTPS bridge page first because many email clients block
        # direct custom-scheme CTA buttons inside HTML emails.
        reset_link = (
            f"{CORE_PUBLIC_URL.rstrip('/')}/api/v1/clientes/auth/open-reset"
            f"?token={quote(token)}"
        )
        subject    = "Reset Your Nocturnal Bar Password 🔐"
    else:
        reset_link = f"{FRONTEND_URL}/admin/reset-password?token={token}"
        subject    = "Staff Password Reset — Nocturnal Bar Management System"

    # ── Load logo ─────────────────────────────────────────────────────────────
    logo_bytes = _load_logo_bytes()
    has_logo   = logo_bytes is not None

    # ── Build message ─────────────────────────────────────────────────────────
    msg = MIMEMultipart("related")
    msg["Subject"] = subject
    msg["From"]    = f"Nocturnal Bar <{SMTP_FROM}>"
    msg["To"]      = email_destino

    # Alternative part (plain + html)
    alternative = MIMEMultipart("alternative")
    msg.attach(alternative)

    # Plain text fallback
    if tipo == "cliente":
        texto_plain = f"""Hello, Nocturnal guest!

Someone requested a password reset for your Nocturnal Bar account.

Tap the link below to open the app and set your new password:
{reset_link}

This link expires in 30 minutes. If you didn't request this, simply ignore this email.

— Nocturnal Bar
"""
    else:
        texto_plain = f"""Hello, Nocturnal Staff Member,

A password reset was requested for your staff account on the Nocturnal Bar Management System.

Click the link below to set your new password:
{reset_link}

This link expires in 30 minutes. If you did not make this request, please contact your system administrator immediately.

— Nocturnal Bar Management System
"""

    html_body = (
        _build_html_cliente(reset_link, has_logo)
        if tipo == "cliente"
        else _build_html_empleado(reset_link, has_logo)
    )

    alternative.attach(MIMEText(texto_plain, "plain", "utf-8"))
    alternative.attach(MIMEText(html_body,   "html",  "utf-8"))

    # Attach logo as inline image with CID
    if has_logo:
        logo_mime = MIMEImage(logo_bytes, _subtype="png")
        logo_mime.add_header("Content-ID", "<nocturnal_logo>")
        logo_mime.add_header("Content-Disposition", "inline", filename="logo.png")
        msg.attach(logo_mime)

    # ── Send ─────────────────────────────────────────────────────────────────
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_FROM, email_destino, msg.as_string())
        logger.info(f"Password reset email ({tipo}) sent successfully to {email_destino}")
    except smtplib.SMTPAuthenticationError:
        logger.error("SMTP authentication error. Check SMTP_USER and SMTP_PASSWORD.")
        raise HTTPException(
            status_code=503,
            detail="Email server configuration error. Contact the administrator."
        )
    except smtplib.SMTPException as e:
        logger.error(f"SMTP error sending email: {e}")
        raise HTTPException(
            status_code=503,
        detail="The recovery email could not be sent. Please try again later."
        )
    except Exception as e:
        logger.error(f"Unexpected error sending email: {e}")
        raise HTTPException(
            status_code=503,
        detail="Internal error sending the email. Please try again later."
        )

# ─── Missing Templates Restored ───────────────────────────────────────────────

def _build_html_generic(title: str, text1: str, text2: str, btn_text: str = None, btn_link: str = None, has_logo: bool = True) -> str:
    logo_block = """<img src="cid:nocturnal_logo" alt="Nocturnal Bar" style="max-width:160px; height:auto; display:block; margin:0 auto 24px auto;" />""" if has_logo else ""
    
    btn_html = ""
    if btn_text and btn_link:
        btn_html = f"""
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td align="center" style="padding:8px 0 28px 0;">
                    <a href="{btn_link}"
                       style="display:inline-block;background:linear-gradient(135deg,#FF6B00,#FFB693);
                              color:#350F00;text-decoration:none;font-size:15px;font-weight:800;
                              letter-spacing:1.5px;padding:16px 40px;border-radius:14px;
                              text-transform:uppercase;">
                      {btn_text}
                    </a>
                  </td>
                </tr>
              </table>
              <hr style="border:none;border-top:1px solid #31353F;margin:0 0 24px 0;" />
        """

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8" /><meta name="viewport" content="width=device-width, initial-scale=1.0" /></head>
<body style="margin:0;padding:0;background-color:#0F131C;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#0F131C;padding:40px 16px;">
    <tr>
      <td align="center">
        <table width="100%" cellpadding="0" cellspacing="0" style="max-width:520px;background-color:#1C1F29;border-radius:24px;border:1px solid #31353F;overflow:hidden;">
          <tr>
            <td style="background:linear-gradient(135deg,#FF6B00 0%,#A04100 100%);padding:32px;text-align:center;">
              {logo_block}
              <h1 style="margin:8px 0 0 0;font-size:26px;font-weight:900;color:#FFFFFF;letter-spacing:2px;">{title}</h1>
            </td>
          </tr>
          <tr>
            <td style="padding:36px;">
              <p style="margin:0 0 16px 0;font-size:16px;line-height:1.6;color:#DFE2EF;">{text1}</p>
              <p style="margin:0 0 24px 0;font-size:15px;line-height:1.7;color:#B0B5C5;">{text2}</p>
              {btn_html}
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""


def _build_html_code_email(
    title: str,
    intro: str,
    detail: str,
    code: str,
    has_logo: bool = True,
) -> str:
    logo_block = """<img src="cid:nocturnal_logo" alt="Nocturnal Bar" style="max-width:160px; height:auto; display:block; margin:0 auto 24px auto;" />""" if has_logo else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8" /><meta name="viewport" content="width=device-width, initial-scale=1.0" /></head>
<body style="margin:0;padding:0;background-color:#0F131C;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#0F131C;padding:40px 16px;">
    <tr>
      <td align="center">
        <table width="100%" cellpadding="0" cellspacing="0" style="max-width:520px;background-color:#1C1F29;border-radius:24px;border:1px solid #31353F;overflow:hidden;">
          <tr>
            <td style="background:linear-gradient(135deg,#FF6B00 0%,#A04100 100%);padding:32px;text-align:center;">
              {logo_block}
              <p style="margin:0;font-size:11px;font-weight:700;letter-spacing:5px;color:rgba(255,255,255,0.65);text-transform:uppercase;">NOCTURNAL BAR</p>
              <h1 style="margin:10px 0 0 0;font-size:26px;font-weight:900;color:#FFFFFF;letter-spacing:1px;">{title}</h1>
            </td>
          </tr>
          <tr>
            <td style="padding:36px;">
              <p style="margin:0 0 14px 0;font-size:16px;line-height:1.6;color:#DFE2EF;">{intro}</p>
              <p style="margin:0 0 24px 0;font-size:15px;line-height:1.7;color:#B0B5C5;">{detail}</p>
              <div style="margin:0 auto 24px auto;max-width:260px;background:#141822;border:1px solid #3A3F4A;border-radius:18px;padding:20px 18px;text-align:center;">
                <p style="margin:0 0 10px 0;font-size:11px;font-weight:800;letter-spacing:3px;color:#FFB693;text-transform:uppercase;">Your Code</p>
                <div style="font-size:34px;font-weight:900;letter-spacing:10px;color:#FFFFFF;font-family:'Courier New',monospace;">{code}</div>
                <p style="margin:12px 0 0 0;font-size:12px;line-height:1.5;color:#9CA3AF;">Tap and hold to copy, then paste it into the app.</p>
              </div>
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td style="background:#181B25;border:1px solid #31353F;border-radius:14px;padding:14px 16px;">
                    <p style="margin:0;font-size:13px;line-height:1.6;color:#B0B5C5;">
                      This code expires in <strong style="color:#FFB693;">30 minutes</strong>.
                      If you did not request this, you can safely ignore this email.
                    </p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
          <tr>
            <td style="background-color:#181B25;padding:20px 36px;border-top:1px solid #31353F;">
              <p style="margin:0;font-size:11px;color:#6B7280;text-align:center;line-height:1.6;">
                © Nocturnal Bar &amp; Lounge<br />
                This is an automated message. Please do not reply.
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""

def enviar_email_cambio_password_notificacion(email_destino: str, recovery_plano: str) -> None:
    html = _build_html_generic(
        "Security Alert", 
        "Your password was recently changed.", 
        f"If you made this change, you can safely ignore this email. Otherwise, contact support immediately.",
        has_logo=True
    )
    _enviar_email(email_destino, "Security Alert: Password Changed", "Your password was changed.", html, "SECURITY")

def enviar_email_confirmacion_cambio_email_viejo(email_destino: str, nuevo_email: str, token: str) -> None:
    link = f"nocturnalbar://confirm-email-change?token={token}"
    html = _build_html_generic(
        "Email Change Request", 
        f"We received a request to change your email to {nuevo_email}.", 
        "Tap the button to authorize this change.",
        "AUTHORIZE CHANGE", link, True
    )
    _enviar_email(email_destino, "Authorize Email Change", "Authorize email change.", html, "EMAIL_CHANGE_OLD")

def enviar_email_verificacion_nuevo_email(nuevo_email: str, token: str) -> None:
    link = f"nocturnalbar://verify-new-email?token={token}"
    html = _build_html_generic(
        "Verify New Email", 
        "You requested to use this email for your Nocturnal Bar account.", 
        "Tap the button to verify this email address.",
        "VERIFY EMAIL", link, True
    )
    _enviar_email(nuevo_email, "Verify New Email", "Verify new email.", html, "EMAIL_CHANGE_NEW")

def enviar_email_solicitud_eliminacion(email_destino: str, token: str) -> None:
    link = f"nocturnalbar://confirm-delete?token={token}"
    html = _build_html_generic(
        "Account Deletion", 
        "We received a request to delete your account.", 
        "Tap the button below to confirm. This action cannot be undone.",
        "CONFIRM DELETION", link, True
    )
    _enviar_email(email_destino, "Confirm Account Deletion", "Confirm deletion.", html, "ACCOUNT_DELETE")

def enviar_email_reactivacion(email_destino: str, token: str) -> None:
    link = f"nocturnalbar://reactivate?token={token}"
    html = _build_html_generic(
        "Welcome Back", 
        "You requested to reactivate your account.", 
        "Tap the button to regain full access to your account.",
        "REACTIVATE ACCOUNT", link, True
    )
    _enviar_email(email_destino, "Reactivate Your Account", "Reactivate account.", html, "ACCOUNT_REACTIVATE")


def enviar_email_codigo_verificacion(email_destino: str, codigo: str) -> None:
    html = _build_html_code_email(
        "Verify Your Email",
        "Your Nocturnal account is almost ready.",
        "Enter this 6-digit code in the app to verify your email and unlock full account protection.",
        codigo,
        True,
    )
    _enviar_email(
        email_destino,
        "Verify your Nocturnal email",
        f"Your verification code is: {codigo}",
        html,
        "EMAIL_VERIFY_OTP",
    )


def enviar_email_codigo_reset(email_destino: str, codigo: str) -> None:
    html = _build_html_code_email(
        "Reset Your Password",
        "We received a password reset request for your Nocturnal account.",
        "Enter this 6-digit code in the app to choose a new password.",
        codigo,
        True,
    )
    _enviar_email(
        email_destino,
        "Your Nocturnal password reset code",
        f"Your password reset code is: {codigo}",
        html,
        "PASSWORD_RESET_OTP",
    )


def enviar_email_codigo_cambio_email_actual(email_destino: str, nuevo_email: str, codigo: str) -> None:
    html = _build_html_code_email(
        "Authorize Email Change",
        f"We received a request to change your Nocturnal email to {nuevo_email}.",
        "Enter this 6-digit code from your current email in the app to approve the change.",
        codigo,
        True,
    )
    _enviar_email(
        email_destino,
        "Authorize your Nocturnal email change",
        f"Your authorization code is: {codigo}",
        html,
        "EMAIL_CHANGE_OLD_OTP",
    )


def enviar_email_codigo_cambio_email_nuevo(email_destino: str, codigo: str) -> None:
    html = _build_html_code_email(
        "Verify New Email",
        "This email address was entered for a Nocturnal account change.",
        "Enter this 6-digit code in the app to confirm you can access this new email.",
        codigo,
        True,
    )
    _enviar_email(
        email_destino,
        "Verify your new Nocturnal email",
        f"Your verification code is: {codigo}",
        html,
        "EMAIL_CHANGE_NEW_OTP",
    )

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def _enviar_email(email_destino: str, subject: str, texto_plain: str, html_body: str, log_tag: str) -> None:
    if not _email_configurado():
        logger.warning(f"[{log_tag}] SMTP is not configured - email not sent to {email_destino}. Configure SMTP_HOST / SMTP_USER / SMTP_PASSWORD in .env to enable sending.")
        raise HTTPException(status_code=503, detail="The email service is not configured. Contact the administrator.")

    logo_bytes = _load_logo_bytes()
    has_logo = logo_bytes is not None

    msg = MIMEMultipart("related")
    msg["Subject"] = subject
    msg["From"]    = f"Nocturnal Bar <{SMTP_FROM}>"
    msg["To"]      = email_destino

    alternative = MIMEMultipart("alternative")
    msg.attach(alternative)
    alternative.attach(MIMEText(texto_plain, "plain", "utf-8"))
    alternative.attach(MIMEText(html_body, "html", "utf-8"))

    if has_logo:
        from email.mime.image import MIMEImage
        img = MIMEImage(logo_bytes)
        img.add_header("Content-ID", "<nocturnal_logo>")
        msg.attach(img)

    last_error: Exception | None = None
    for attempt in range(2):
        message_sent = False
        try:
            if SMTP_PORT == 465:
                server = smtplib.SMTP_SSL(
                    SMTP_HOST,
                    SMTP_PORT,
                    timeout=15,
                    context=ssl.create_default_context(),
                )
            else:
                server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15)

            with server:
                server.ehlo()
                if SMTP_PORT != 465:
                    server.starttls(context=ssl.create_default_context())
                    server.ehlo()
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.sendmail(SMTP_FROM, [email_destino], msg.as_string())
                message_sent = True
            logger.info(f"[{log_tag}] Email enviado a {email_destino}")
            return
        except smtplib.SMTPAuthenticationError:
            raise HTTPException(
                status_code=503,
                detail="The email service could not authenticate. Please contact support.",
            )
        except (smtplib.SMTPException, OSError) as error:
            if message_sent:
                # The SMTP server may close immediately after accepting DATA;
                # do not resend and risk a duplicate OTP in that case.
                logger.info(f"[{log_tag}] Email accepted by SMTP server")
                return
            last_error = error
            if attempt == 0:
                time.sleep(0.5)

    logger.error(f"[{log_tag}] Error sending email after retry: {last_error}")
    raise HTTPException(
        status_code=503,
        detail="The email service is temporarily unavailable. Please try again shortly.",
    )
    if False:
        raise HTTPException(status_code=503, detail="Internal error sending the email. Please try again later.")
