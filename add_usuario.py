import bcrypt
import sqlite3
import secrets
from utils_email import enviar_email

def criar_usuario(nome, email, tipo, regiao, email_remetente, senha_app):
    conn = sqlite3.connect("laudos.db")
    cursor = conn.cursor()

    senha_temp = secrets.token_urlsafe(8)
    senha_hash = bcrypt.hashpw(senha_temp.encode(), bcrypt.gensalt())

    try:
        cursor.execute("""
        INSERT INTO usuarios (nome, email, senha_hash, tipo, regiao, senha_temporaria)
        VALUES (?, ?, ?, ?, ?, 1)
        """, (nome, email, senha_hash.decode(), tipo, regiao))
        conn.commit()

        mensagem = f"""
Olá {nome},

Seu acesso ao sistema de laudos HVI foi criado.

Usuário: {email}
Senha temporária: {senha_temp}

Você deverá alterá-la no primeiro acesso.

Atenciosamente,
Sistema de Laudos
"""
        enviar_email(email, "Acesso ao Sistema de Laudos", mensagem, email_remetente, senha_app)
        print("Usuário criado e e-mail enviado.")
    except Exception as e:
        print("Erro ao criar usuário:", e)
    finally:
        conn.close()

# Exemplo de uso:
# criar_usuario("João", "joao@email.com", "usuario", "MT", "seuemail@gmail.com", "senha_app_aqui")
