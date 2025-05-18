import sqlite3
import bcrypt
import secrets

def criar_usuario(nome, email, tipo, regiao):
    conn = sqlite3.connect("laudos.db")
    cursor = conn.cursor()

    senha_temp = secrets.token_urlsafe(8)
    senha_hash = bcrypt.hashpw(senha_temp.encode(), bcrypt.gensalt()).decode()

    try:
        cursor.execute("""
            INSERT INTO usuarios (nome, email, senha_hash, tipo, regiao, senha_temporaria)
            VALUES (?, ?, ?, ?, ?, 1)
        """, (nome, email, senha_hash, tipo, regiao))
        conn.commit()
        print(f"✅ Usuário criado com sucesso!")
        print(f"👤 Nome: {nome}")
        print(f"📧 Email: {email}")
        print(f"🔑 Senha temporária: {senha_temp}")
    except sqlite3.IntegrityError:
        print(f"⚠️ Já existe um usuário com o e-mail {email}.")
    finally:
        conn.close()

# Exemplo de uso:
criar_usuario("José Alvarenga", "jose.alvarenga@ldc.com", "administrador", "MT")

