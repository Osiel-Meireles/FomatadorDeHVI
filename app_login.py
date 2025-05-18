import streamlit as st
import bcrypt
import sqlite3
import pandas as pd
from datetime import datetime
from io import BytesIO
from database import (
    criar_tabelas,
    inserir_formatacao,
    inserir_fardos,
    listar_formatacoes,
    listar_fardos_por_formatacao,
    consultar_registros_completos
)

criar_tabelas()

st.set_page_config(page_title="SIFHVI", layout="wide")

# Função para autenticar usuário
def autenticar_usuario(email, senha):
    conn = sqlite3.connect("laudos.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome, senha_hash, tipo, regiao, senha_temporaria FROM usuarios WHERE email = ?", (email,))
    user = cursor.fetchone()
    conn.close()

    if user and bcrypt.checkpw(senha.encode(), user[2].encode()):
        return {
            "id": user[0],
            "nome": user[1],
            "tipo": user[3],
            "regiao": user[4],
            "senha_temporaria": bool(user[5])
        }
    return None

# Função para atualizar senha definitiva
def atualizar_senha(usuario_id, nova_senha):
    conn = sqlite3.connect("laudos.db")
    cursor = conn.cursor()
    senha_hash = bcrypt.hashpw(nova_senha.encode(), bcrypt.gensalt()).decode()
    cursor.execute("UPDATE usuarios SET senha_hash = ?, senha_temporaria = 0 WHERE id = ?", (senha_hash, usuario_id))
    conn.commit()
    conn.close()

# Controle de sessão
def login():
    if "usuario_autenticado" not in st.session_state:
        st.session_state.usuario_autenticado = False

    if not st.session_state.usuario_autenticado:
        with st.form("login_form"):
            email = st.text_input("Email")
            senha = st.text_input("Senha", type="password")
            submit = st.form_submit_button("Entrar")

            if submit:
                usuario = autenticar_usuario(email, senha)
                if usuario:
                    st.session_state.usuario_autenticado = True
                    st.session_state.usuario_id = usuario["id"]
                    st.session_state.usuario_nome = usuario["nome"]
                    st.session_state.usuario_tipo = usuario["tipo"]
                    st.session_state.usuario_regiao = usuario["regiao"]
                    st.session_state.senha_temporaria = usuario["senha_temporaria"]
                    st.success("Login realizado com sucesso!")
                    st.experimental_rerun()
                else:
                    st.error("Email ou senha incorretos.")
        return False

    elif st.session_state.senha_temporaria:
        st.warning("Você está usando uma senha temporária. Altere-a para continuar.")
        with st.form("trocar_senha_form"):
            nova_senha = st.text_input("Nova senha", type="password")
            confirmar = st.text_input("Confirmar nova senha", type="password")
            trocar = st.form_submit_button("Atualizar senha")

            if trocar:
                if nova_senha != confirmar:
                    st.error("As senhas não coincidem.")
                elif len(nova_senha) < 6:
                    st.error("A nova senha deve ter pelo menos 6 caracteres.")
                else:
                    atualizar_senha(st.session_state.usuario_id, nova_senha)
                    st.session_state.senha_temporaria = False
                    st.success("Senha atualizada com sucesso!")
                    st.experimental_rerun()
        return False

    return True

if not login():
    st.stop()

st.sidebar.title("Menu")
st.sidebar.markdown(f"**Usuário:** {st.session_state.usuario_nome}")
if st.sidebar.button("Sair"):
    st.session_state.clear()
    st.experimental_rerun()

opcoes = ["Processar PDF", "Histórico de Formatações"]
if st.session_state.usuario_tipo == "admin":
    opcoes.append("Exportar do Banco")

opcao = st.sidebar.radio("Ir para:", opcoes)

# Exemplo de controle por região (em cada funcionalidade):
if opcao == "Histórico de Formatações":
    st.write(f"🔎 Mostrando dados da região: **{st.session_state.usuario_regiao}**")
    # Aqui você pode aplicar filtros por região se quiser

if opcao == "Exportar do Banco":
    if st.session_state.usuario_tipo != "admin":
        st.error("Apenas administradores podem acessar esta área.")
        st.stop()
    else:
        st.success("Exportação permitida para administradores.")