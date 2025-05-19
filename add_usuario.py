import sqlite3
import bcrypt
import secrets
from contextlib import closing

def criar_usuario(nome, email, tipo, regiao, db_path="laudos.db"):
    senha_temp = secrets.token_urlsafe(8)
    senha_hash = bcrypt.hashpw(senha_temp.encode(), bcrypt.gensalt()).decode()

    with closing(sqlite3.connect(db_path)) as conn, closing(conn.cursor()) as cursor:
        try:
            cursor.execute(
                """
                INSERT INTO usuarios (nome, email, senha_hash, tipo, regiao, senha_temporaria)
                VALUES (?, ?, ?, ?, ?, 1)
                """,
                (nome, email, senha_hash, tipo, regiao)
            )
            conn.commit()
            print(f"✅ Usuário criado com sucesso!")
            print(f"👤 Nome: {nome}")
            print(f"📧 Email: {email}")
            print(f"🔑 Senha temporária: {senha_temp}")
        except sqlite3.IntegrityError:
            print(f"⚠️ Já existe um usuário com o e-mail {email}.")

if __name__ == "__main__":
    # Exemplo de uso:
    criar_usuario("Adm", "adm@ldc.com", "admin", "BA")

