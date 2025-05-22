import streamlit as st
st.set_page_config(page_title="SIFHVI", layout="wide")

import pandas as pd
import pdfplumber
import sqlite3
import os
from io import BytesIO
from datetime import datetime
from dotenv import load_dotenv
from utils_email import enviar_email
from database import (
    criar_tabelas,
    inserir_formatacao,
    inserir_fardos,
    listar_formatacoes,
    listar_fardos_por_formatacao,
    consultar_registros_completos
)

# Carrega variáveis de ambiente e inicializa o banco
load_dotenv()
criar_tabelas()

# Sidebar Menu
st.sidebar.title("Menu")
opcoes = ["Processar PDF", "Histórico de Formatações"]
user_type = os.getenv("DEFAULT_USER_TYPE", "usuario")
if user_type.lower() == "admin":
    opcoes += ["Painel Administrativo", "Exportar do Banco"]
opcao = st.sidebar.radio("Ir para:", opcoes)

# Função de processamento de PDFs
def processar_pdfs(arquivos, produtor, corretora):
    df_final = pd.DataFrame()
    for arq in arquivos:
        with pdfplumber.open(arq) as pdf:
            dados = []
            lote = safra = data_hvi = "Desconhecido"
            for pg in pdf.pages:
                txt = pg.extract_text() or ""
                for ln in txt.split("\n"):
                    if ln.startswith("Cliente:") and "Lote:" in ln:
                        lote = ln.split("Lote:")[1].strip().split()[0]
                    elif ln.startswith("Safra:"):
                        safra = ln.split("Safra:")[1].strip().split()[0]
                    elif ln.startswith("Fazenda:") and "Data:" in ln:
                        data_hvi = ln.split("Data:")[1].strip().split()[0]
                    elif ln.startswith("00.0."):
                        partes = ln.replace(",", ".").split()
                        partes.insert(0, lote)
                        dados.append(partes)
        colunas = [
            "Lote", "FardoID", "UHML_mm", "UHML_pol", "UI", "SFI",
            "STR", "ELG", "MIC", "Mat", "Rd", "+b", "CGrd",
            "TrCnt", "TrAr", "TrID", "SCI", "CSP"
        ]
        df = pd.DataFrame(dados, columns=colunas)
        plantio = colheita = ""
        if "/" in safra:
            plantio, colheita = safra.split("/")
        df["Data HVI"] = data_hvi
        df["Ano Plantio"] = plantio
        df["Ano Colheita"] = colheita
        id_fmt = inserir_formatacao(lote, data_hvi, safra, produtor, None)
        inserir_fardos(id_fmt, df)
        df_final = pd.concat([df_final, df], ignore_index=True)
    return df_final

# Tela: Processar PDF
if opcao == "Processar PDF":
    st.subheader("📄 Processar Laudos HVI")
    arquivos = st.file_uploader("Envie os PDFs", type=["pdf"], accept_multiple_files=True)
    # auto-extract produtor do primeiro PDF
    produtor_default = ""
    if arquivos:
        try:
            with pdfplumber.open(arquivos[0]) as pdf0:
                txt0 = pdf0.pages[0].extract_text() or ""
                for ln0 in txt0.split("\n"):
                    if ln0.startswith("Produtor:"):
                        produtor_default = ln0.split("Produtor:")[1].strip()
                        break
        except:
            produtor_default = ""
    produtor = st.text_input("Nome do produtor", value=produtor_default)
    corretora = st.text_input("Nome da corretora")

    if arquivos and produtor and corretora:
        with st.spinner("Processando os arquivos..."):
            df_final = processar_pdfs(arquivos, produtor, corretora)
            df_final["UHML"] = df_final["UHML_mm"].apply(
                lambda v: round((float(v)/1000)*39.3701, 2) if v.replace('.', '', 1).isdigit() else "-"
            )
            df_final["MAT"] = df_final["Mat"].apply(
                lambda x: int(round(float(x)*100)) if x.replace('.', '', 1).isdigit() else x
            )
            df_final["CG"] = df_final["CGrd"].astype(str).str.replace("-", ".")
            df_final["FardoID"] = df_final["FardoID"].str.replace('.', '', regex=False)
            df_final["PESO"] = ""
            df_final["Tipo"] = ""
            df_final["Produtor"] = produtor
            export_cols = [
                "Lote", "FardoID", "MIC", "UHML", "STR", "PESO", "SFI", "UI",
                "CSP", "ELG", "Rd", "+b", "TrID", "SCI", "MAT", "CG",
                "Produtor", "Tipo", "Data HVI", "Ano Plantio", "Ano Colheita"
            ]
            export = df_final[export_cols]
            buffer = BytesIO()
            export.to_excel(buffer, index=False, engine="openpyxl")
            buffer.seek(0)
            nome = f"Resumo_Oferta_{datetime.now().strftime('%Y-%m-%d')}_{produtor}_{corretora}.xlsx".replace(" ", "_")
            st.download_button("📥 Baixar Excel Consolidado", data=buffer, file_name=nome)
        st.success("Todos os arquivos foram processados com sucesso!")

# Tela: Histórico de Formatações
elif opcao == "Histórico de Formatações":
    st.subheader("📋 Histórico de Formatações")
    dados = listar_formatacoes()
    df = pd.DataFrame(dados, columns=[
        "ID", "Lote", "Safra", "Produtor", "Data HVI", "Data Format", "UsuarioID", "Qtd Fardos"
    ])
    if df.empty:
        st.info("Nenhuma formatação registrada.")
    else:
        st.dataframe(df)
        escolha = st.selectbox("Selecione uma formatação:", df["ID"])
        fardos = listar_fardos_por_formatacao(escolha)
        st.dataframe(pd.DataFrame(fardos))

elif opcao == "Exportar do Banco":
    st.subheader("📤 Exportar Dados Salvos")
    df = consultar_registros_completos()
    buffer = BytesIO()
    df.to_excel(buffer, index=False, engine="openpyxl")
    buffer.seek(0)
    st.download_button("📁 Baixar Excel com Registros", data=buffer, file_name="export_banco.xlsx")

elif opcao == "Painel Administrativo":
    st.subheader("👤 Painel de Administração")
    with sqlite3.connect("laudos.db") as conn:
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
                    cursor.execute(
                        "INSERT INTO usuarios (nome, email, senha_hash, tipo, regiao, senha_temporaria) VALUES (?, ?, ?, ?, ?, 1)",
                        (nome, email, senha_hash, tipo, regiao)
                    )
                    conn.commit()
                    st.success(f"Usuário {nome} criado com sucesso! Senha: {senha_temp}")
                    try:
                        enviar_email(
                            email,
                            "Acesso ao SIFHVI",
                            f"Usuário: {email}\nSenha temporária: {senha_temp}",
                            os.getenv("EMAIL_REMETENTE"),
                            os.getenv("EMAIL_SENHA_APP")
                        )
                        st.info("E-mail enviado com sucesso.")
                    except Exception as e:
                        st.warning(f"Erro ao enviar e-mail: {e}")
                except sqlite3.IntegrityError:
                    st.error("Este e-mail já está cadastrado.")
        cursor.execute("SELECT id, nome, email, tipo, regiao FROM usuarios")
        usuarios = cursor.fetchall()
        st.dataframe(pd.DataFrame(usuarios, columns=["ID", "Nome", "Email", "Tipo", "Região"]))





