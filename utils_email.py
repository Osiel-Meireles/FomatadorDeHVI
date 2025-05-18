import smtplib
from email.mime.text import MIMEText

def enviar_email(destinatario, assunto, mensagem, remetente, senha_app):
    msg = MIMEText(mensagem)
    msg["Subject"] = assunto
    msg["From"] = remetente
    msg["To"] = destinatario

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(remetente, senha_app)
        server.send_message(msg)
