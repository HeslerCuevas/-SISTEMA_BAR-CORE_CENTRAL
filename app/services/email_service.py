"""
Servicio de Email para envío de correos de recuperación de contraseña.
Usa smtplib con configuración por variables de entorno.
"""
import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fastapi import HTTPException

logger = logging.getLogger("EmailService")

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "noreply@corebarlounge.com")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


def _email_configurado() -> bool:
    return bool(SMTP_HOST and SMTP_USER and SMTP_PASSWORD)


def enviar_email_reset_password(email_destino: str, token: str, tipo: str = "empleado"):
    """
    Envía el correo de recuperación de contraseña.
    tipo: 'empleado' | 'cliente'
    """
    if not _email_configurado():
        logger.warning(
            "SMTP no configurado. Token de reset generado pero no enviado por email. "
            f"Token: {token[:8]}... para {email_destino}"
        )
        # En desarrollo, retorna sin error para poder usar el token por logs
        return

    ruta = "admin/reset-password" if tipo == "empleado" else "cliente/reset-password"
    reset_link = f"{FRONTEND_URL}/{ruta}?token={token}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Recuperación de Contraseña — CORE Bar & Lounge"
    msg["From"] = SMTP_FROM
    msg["To"] = email_destino

    texto_plain = f"""
Hola,

Recibiste este correo porque se solicitó restablecer la contraseña de tu cuenta.

Haz clic en el siguiente enlace para continuar (expira en 30 minutos):
{reset_link}

Si no solicitaste este cambio, ignora este mensaje.

— CORE Bar & Lounge
"""

    texto_html = f"""
<html>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 20px;">
  <h2 style="color: #333;">Recuperación de Contraseña</h2>
  <p>Recibiste este correo porque se solicitó restablecer la contraseña de tu cuenta.</p>
  <p>Haz clic en el siguiente botón para continuar (expira en <strong>30 minutos</strong>):</p>
  <p style="text-align:center; margin: 30px 0;">
    <a href="{reset_link}"
       style="background:#1a1a2e;color:#fff;padding:14px 28px;border-radius:6px;
              text-decoration:none;font-size:16px;">
      Restablecer Contraseña
    </a>
  </p>
  <p style="color:#888;font-size:12px;">
    Si no solicitaste este cambio, ignora este mensaje. El enlace expirará automáticamente.
  </p>
  <hr style="border:none;border-top:1px solid #eee;margin-top:30px;">
  <p style="color:#aaa;font-size:11px;">CORE Bar &amp; Lounge — Sistema de Gestión</p>
</body>
</html>
"""

    msg.attach(MIMEText(texto_plain, "plain"))
    msg.attach(MIMEText(texto_html, "html"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_FROM, email_destino, msg.as_string())
        logger.info(f"Email de reset enviado exitosamente a {email_destino}")
    except smtplib.SMTPAuthenticationError:
        logger.error("Error de autenticación SMTP. Verifica SMTP_USER y SMTP_PASSWORD.")
        raise HTTPException(
            status_code=503,
            detail="Error de configuración del servidor de correo. Contacta al administrador."
        )
    except smtplib.SMTPException as e:
        logger.error(f"Error SMTP al enviar email: {e}")
        raise HTTPException(
            status_code=503,
            detail="No se pudo enviar el correo de recuperación. Intenta más tarde."
        )
    except Exception as e:
        logger.error(f"Error inesperado enviando email: {e}")
        raise HTTPException(
            status_code=503,
            detail="Error interno al enviar el correo. Intenta más tarde."
        )
