import secrets
import smtplib
import os
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def gerar_token_reset() -> tuple[str, datetime]:
    """
    Gera um token seguro de 32 bytes (256 bits) e calcula
    o horário de expiração: agora em UTC + 1 hora.
    Retorna os dois valores juntos para salvar no banco.
    """
    token     = secrets.token_urlsafe(32)
    expira_em = datetime.utcnow() + timedelta(hours=1)
    return token, expira_em


def enviar_email_reset(destinatario: str, token: str):
    """
    Monta e envia o e-mail com o link de reset via SMTP.
    Todas as configurações vêm das variáveis de ambiente.
    """
    base_url = os.getenv("APP_BASE_URL", "http://localhost:3000")
    link     = f"{base_url}/reset-password?token={token}"

    msg            = MIMEMultipart("alternative")
    msg["Subject"] = "Redefinição de senha"
    msg["From"]    = os.getenv("EMAIL_FROM")
    msg["To"]      = destinatario

    html = f"""
    <div style="font-family: sans-serif; max-width: 480px; margin: 0 auto;">
      <h2 style="color: #1a1a1a;">Redefinição de senha</h2>
      <p style="color: #444;">Recebemos uma solicitação para redefinir a senha da sua conta.</p>
      <a href="{link}"
         style="display: inline-block; padding: 12px 24px; margin: 16px 0;
                background: #4F46E5; color: #ffffff;
                border-radius: 6px; text-decoration: none; font-weight: 500;">
        Redefinir minha senha
      </a>
      <p style="color: #888; font-size: 13px; margin-top: 24px;">
        Este link expira em <strong>1 hora</strong>.<br>
        Se não foi você quem solicitou, ignore este e-mail — sua senha permanece a mesma.
      </p>
    </div>
    """

    msg.attach(MIMEText(html, "html"))

    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASSWORD")

    with smtplib.SMTP(smtp_host, smtp_port) as servidor:
        servidor.starttls()                        # ativa criptografia TLS
        servidor.login(smtp_user, smtp_pass)       # autentica no servidor de e-mail
        servidor.sendmail(msg["From"], destinatario, msg.as_string())