import streamlit as st
st.set_page_config(page_title="SIFHVI", layout="wide")

import pandas as pd
import pdfplumber
import bcrypt
import sqlite3
import secrets
import os
from io import BytesIO
from datetime import datetime
from dotenv import load_dotenv
from streamlit_cookies_manager import EncryptedCookieManager
from utils_email import enviar_email
from database import (
    criar_tabelas,
    inserir_formatacao,
    inserir_fardos,
    listar_formatacoes,
    listar_fardos_por_formatacao,
    consultar_registros_completos
)

load_dotenv()
criar_tabelas()
cookies = EncryptedCookieManager(prefix="sifhvi_", password=os.getenv("COOKIE_PASSWORD"))

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

def atualizar_senha(usuario_id, nova_senha):
    conn = sqlite3.connect("laudos.db")
    cursor = conn.cursor()
    senha_hash = bcrypt.hashpw(nova_senha.encode(), bcrypt.gensalt()).decode()
    cursor.execute("UPDATE usuarios SET senha_hash = ?, senha_temporaria = 0 WHERE id = ?", (senha_hash, usuario_id))
    conn.commit()
    conn.close()

def login():
    if cookies.get("usuario_id") and not st.session_state.get("usuario_autenticado"):
        st.session_state.usuario_autenticado = True
        st.session_state.usuario_id = int(cookies.get("usuario_id"))
        st.session_state.usuario_nome = cookies.get("usuario_nome")
        st.session_state.usuario_tipo = cookies.get("usuario_tipo")
        st.session_state.usuario_regiao = cookies.get("usuario_regiao")
        st.session_state.senha_temporaria = False

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
                    cookies.set("usuario_id", usuario["id"])
                    cookies.set("usuario_nome", usuario["nome"])
                    cookies.set("usuario_tipo", usuario["tipo"])
                    cookies.set("usuario_regiao", usuario["regiao"])
                    cookies.save()
                    st.rerun()
                else:
                    st.error("Email ou senha incorretos.")
        return False

    elif st.session_state.senha_temporaria:
        st.warning("Você está usando uma senha temporária. Altere-a para continuar.")
        with st.form("trocar_senha_form"):
            nova = st.text_input("Nova senha", type="password")
            confirmar = st.text_input("Confirmar nova senha", type="password")
            trocar = st.form_submit_button("Atualizar senha")
            if trocar:
                if nova != confirmar:
                    st.error("As senhas não coincidem.")
                elif len(nova) < 6:
                    st.error("A senha deve ter pelo menos 6 caracteres.")
                else:
                    atualizar_senha(st.session_state.usuario_id, nova)
                    st.session_state.senha_temporaria = False
                    st.success("Senha atualizada com sucesso!")
                    st.rerun()
        return False
    return True

if not login():
    st.stop()

# ----------------- MENU E NAVEGAÇÃO -----------------
st.sidebar.title("Menu")
st.sidebar.markdown(f"**Usuário:** {st.session_state.usuario_nome}")
if st.sidebar.button("Sair"):
    st.session_state.clear()
    for key in ["usuario_id", "usuario_nome", "usuario_tipo", "usuario_regiao"]:
        cookies.delete(key)
    cookies.save()
    st.rerun()

opcoes = ["Processar PDF", "Histórico de Formatações"]
if st.session_state.usuario_tipo == "admin":
    opcoes.append("Painel Administrativo")
    opcoes.append("Exportar do Banco")
opcao = st.sidebar.radio("Ir para:", opcoes)

if opcao == "Processar PDF":
    st.subheader("📄 Processar Laudos HVI")
    arquivos = st.file_uploader("Envie os PDFs", type=["pdf"], accept_multiple_files=True)
    produtor = st.text_input("Nome do produtor")
    corretora = st.text_input("Nome da corretora")
    df_final = pd.DataFrame()

    if arquivos and produtor and corretora:
        for arq in arquivos:
            with pdfplumber.open(arq) as pdf:
                dados, lote, safra, data_hvi = [], "Desconhecido", "Desconhecida", "Desconhecida"
                for pg in pdf.pages:
                    txt = pg.extract_text()
                    for ln in txt.split("\n"):
                        if "Lote:" in ln: lote = ln.split("Lote:")[1].strip().split()[0]
                        if "Safra:" in ln: safra = ln.split("Safra:")[1].strip().split()[0]
                        if "Data:" in ln: data_hvi = ln.split("Data:")[1].strip().split()[0]
                        if ln.startswith("00.0."):
                            partes = ln.replace(",", ".").split()
                            partes.insert(0, lote)
                            dados.append(partes)

            colunas = ["Lote", "FardoID", "UHML_mm", "UHML_pol", "UI", "SFI", "STR", "ELG", "MIC", "Mat",
                       "Rd", "+b", "CGrd", "TrCnt", "TrAr", "TrID", "SCI", "CSP"]
            df = pd.DataFrame(dados, columns=colunas)
            id_fmt = inserir_formatacao(lote, data_hvi, safra, produtor, st.session_state.usuario_id)
            inserir_fardos(id_fmt, df)
            df_final = pd.concat([df_final, df], ignore_index=True)
            st.success(f"{arq.name}: {len(df)} fardos processados.")

        df_final["UHML"] = df_final["UHML_mm"].apply(lambda v: round((float(v)/1000)*39.3701,2) if v.replace('.','',1).isdigit() else "-")
        df_final["MAT"] = df_final["Mat"].apply(lambda x: int(round(float(x)*100)) if x.replace('.','',1).isdigit() else x)
        df_final["CG"] = df_final["CGrd"].astype(str).str.replace("-", ".")
        df_final["PESO"] = ""
        df_final["Tipo"] = ""
        df_final["Produtor"] = produtor

        export = df_final[["Lote","FardoID","MIC","UHML","STR","PESO","SFI","UI","CSP","ELG","Rd","+b","TrID","SCI","MAT","CG","Produtor","Tipo"]]
        buffer = BytesIO()
        export.to_excel(buffer, index=False, engine="openpyxl")
        buffer.seek(0)
        nome = f"Resumo_Oferta_{datetime.now().strftime('%Y-%m-%d')}_{produtor}_{corretora}.xlsx".replace(" ", "_")
        st.download_button("📥 Baixar Excel Consolidado", data=buffer, file_name=nome)

elif opcao == "Histórico de Formatações":
    st.subheader("📋 Histórico de Formatações")
    dados = listar_formatacoes()
    if st.session_state.usuario_tipo != "admin":
        dados = [d for d in dados if d[6] == st.session_state.usuario_id]
    if not dados:
        st.info("Nenhuma formatação registrada.")
    else:
        df = pd.DataFrame(dados, columns=["ID", "Lote", "Safra", "Produtor", "Data HVI", "Data Format", "UsuarioID", "Qtd Fardos"])
        st.dataframe(df)
        escolha = st.selectbox("Selecione uma formatação:", df["ID"])
        fardos = listar_fardos_por_formatacao(escolha)
        st.dataframe(fardos)

elif opcao == "Exportar do Banco":
    st.subheader("📤 Exportar Dados Salvos")
    df = consultar_registros_completos()
    buffer = BytesIO()
    df.to_excel(buffer, index=False, engine="openpyxl")
    buffer.seek(0)
    st.download_button("📁 Baixar Excel com Registros", data=buffer, file_name="export_banco.xlsx")

elif opcao == "Painel Administrativo":
    st.subheader("👤 Painel de Administração")
    conn = sqlite3.connect("laudos.db")
    cursor = conn.cursor()
    with st.form("novo_user"):
        nome = st.text_input("Nome")
        email = st.text_input("Email")
        tipo = st.selectbox("Tipo", ["admin", "usuario"])
        regiao = st.selectbox("Região", ["MT", "BA"])
        cadastrar = st.form_submit_button("Cadastrar Usuário")
        if cadastrar:
            senha_temp = secrets.token_urlsafe(8)
            senha_hash = bcrypt.hashpw(senha_temp.encode(), bcrypt.gensalt()).decode()
            try:
                cursor.execute("INSERT INTO usuarios (nome, email, senha_hash, tipo, regiao, senha_temporaria) VALUES (?, ?, ?, ?, ?, 1)",
                               (nome, email, senha_hash, tipo, regiao))
                conn.commit()
                st.success(f"Usuário {nome} criado com sucesso! Senha: {senha_temp}")
                try:
                    enviar_email(email, "Acesso ao SIFHVI", f"Usuário: {email}\nSenha temporária: {senha_temp}", os.getenv("EMAIL_REMETENTE"), os.getenv("EMAIL_SENHA_APP"))
                    st.info("E-mail enviado com sucesso.")
                except Exception as e:
                    st.warning(f"Erro ao enviar e-mail: {e}")
            except sqlite3.IntegrityError:
                st.error("Este e-mail já está cadastrado.")
    cursor.execute("SELECT id, nome, email, tipo, regiao FROM usuarios")
    usuarios = cursor.fetchall()
    conn.close()
    st.dataframe(pd.DataFrame(usuarios, columns=["ID", "Nome", "Email", "Tipo", "Região"]))
