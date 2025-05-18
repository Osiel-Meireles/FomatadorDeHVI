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

from dotenv import load_dotenv
import os
from streamlit_cookies_manager import EncryptedCookieManager

load_dotenv()
cookies = EncryptedCookieManager(prefix="sifhvi_", password=os.getenv("COOKIE_PASSWORD"))
cookies.load()

# Controle de sessão
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
                    st.success("Login realizado com sucesso!")
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
                    st.rerun()
        return False

    return True

if not login():
    st.stop()

st.sidebar.title("Menu")
st.sidebar.markdown(f"**Usuário:** {st.session_state.usuario_nome}")
if st.sidebar.button("Sair"):
    st.session_state.clear()
    cookies.delete("usuario_id")
    cookies.delete("usuario_nome")
    cookies.delete("usuario_tipo")
    cookies.delete("usuario_regiao")
    cookies.save()
    st.rerun()

opcoes = ["Processar PDF", "Histórico de Formatações"]
if st.session_state.usuario_tipo == "admin":
    opcoes.append("Exportar do Banco")

    opcoes.append("Painel Administrativo")

opcao = st.sidebar.radio("Ir para:", opcoes)

# Aba de Processamento de PDF
if opcao == "Processar PDF":
    st.subheader("📄 Processar Laudos HVI (PDF)")
    uploaded_files = st.file_uploader("Envie um ou mais arquivos PDF de laudos HVI", type=["pdf"], accept_multiple_files=True)

    produtor_input = st.text_input("Nome do produtor")
    corretora_input = st.text_input("Nome da corretora")

    df_consolidado = pd.DataFrame()

    if uploaded_files and produtor_input and corretora_input:
        import pdfplumber

        for uploaded_file in uploaded_files:
            with pdfplumber.open(uploaded_file) as pdf:
                linhas_dados = []
                numero_lote = "Desconhecido"
                safra = "Desconhecida"
                data_hvi = "Desconhecida"

                for page in pdf.pages:
                    texto = page.extract_text()

                    if "Lote:" in texto:
                        for linha in texto.split(""):
                            if "Lote:" in linha:
                                partes = linha.split("Lote:")
                                if len(partes) > 1:
                                    numero_lote = partes[1].strip().split()[0]
                            if "Safra:" in linha:
                                safra = linha.split("Safra:")[1].strip().split()[0]
                            if "Data:" in linha:
                                data_hvi = linha.split("Data:")[1].strip().split()[0]

                    for linha in texto.split(""):
                        if linha.startswith("00.0."):
                            linha_formatada = linha.replace(",", ".")
                            partes = linha_formatada.split()
                            partes.insert(0, numero_lote)
                            linhas_dados.append(partes)

            colunas = [
                "Lote", "FardoID", "UHML_mm", "UHML_pol", "UI", "SFI", "STR", "ELG", "MIC", "Mat",
                "Rd", "+b", "CGrd", "TrCnt", "TrAr", "TrID", "SCI", "CSP"
            ]

            df = pd.DataFrame(linhas_dados, columns=colunas)
            st.success(f"[{uploaded_file.name}] {len(df)} fardos processados com sucesso!")
            st.dataframe(df)

            formatacao_id = inserir_formatacao(numero_lote, data_hvi, safra, produtor_input, st.session_state.usuario_id)
            inserir_fardos(formatacao_id, df)

            df_consolidado = pd.concat([df_consolidado, df], ignore_index=True)

        def mm_para_pol(valor):
            try:
                return round((float(valor) / 1000) * 39.3701, 2)
            except:
                return "-"

        def multiplicar_mat(valor):
            try:
                return int(round(float(valor) * 100))
            except:
                return valor

        df_export = pd.DataFrame()
        df_export["LOTE"] = df_consolidado["Lote"]
        df_export["FARDO"] = df_consolidado["FardoID"]
        df_export["MICRONAIR"] = df_consolidado["MIC"]
        df_export["UHML"] = df_consolidado["UHML_mm"].apply(mm_para_pol)
        df_export["RES"] = df_consolidado["STR"]
        df_export["PESO"] = ""
        df_export["SFI"] = df_consolidado["SFI"]
        df_export["UNF"] = df_consolidado["UI"]
        df_export["CSP"] = df_consolidado["CSP"]
        df_export["ELG"] = df_consolidado["ELG"]
        df_export["RD"] = df_consolidado["Rd"]
        df_export["+B"] = df_consolidado["+b"]
        df_export["LEAF"] = df_consolidado["TrID"]
        df_export["SCI"] = df_consolidado["SCI"]
        df_export["MAT"] = df_consolidado["Mat"].apply(multiplicar_mat)
        df_export["CG"] = df_consolidado["CGrd"].astype(str).str.replace("-", ".", regex=False)
        df_export["Produtor"] = produtor_input
        df_export["Tipo"] = ""

        nome_arquivo = f"Resumo_Oferta_{datetime.now().strftime('%Y-%m-%d')}_{produtor_input}_{corretora_input}.xlsx".replace(" ", "_")
        buffer = BytesIO()
        df_export.to_excel(buffer, index=False, engine='openpyxl')
        buffer.seek(0)

        st.download_button(
            label="📥 Baixar Excel Consolidado",
            data=buffer,
            file_name=nome_arquivo,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )


# Painel Administrativo
if opcao == "Painel Administrativo":
    st.subheader("👤 Painel de Administração de Usuários")

    conn = sqlite3.connect("laudos.db")
    cursor = conn.cursor()

    st.markdown("### ➕ Adicionar Novo Usuário")
    with st.form("add_user_form"):
        novo_nome = st.text_input("Nome completo")
        novo_email = st.text_input("Email")
        novo_tipo = st.selectbox("Tipo de acesso", ["admin", "usuario"])
        nova_regiao = st.selectbox("Região", ["BA", "MT"])
        cadastrar = st.form_submit_button("Cadastrar")

        if cadastrar and novo_nome and novo_email:
            import secrets
            senha_temp = secrets.token_urlsafe(8)
            senha_hash = bcrypt.hashpw(senha_temp.encode(), bcrypt.gensalt()).decode()

            try:
                cursor.execute("""
                    INSERT INTO usuarios (nome, email, senha_hash, tipo, regiao, senha_temporaria)
                    VALUES (?, ?, ?, ?, ?, 1)
                """, (novo_nome, novo_email, senha_hash, novo_tipo, nova_regiao))
                conn.commit()
                st.success(f"Usuário {novo_nome} criado com sucesso! Senha temporária: {senha_temp}")
            except sqlite3.IntegrityError:
                st.error("Já existe um usuário com esse e-mail.")

    st.markdown("### 📋 Lista de Usuários Cadastrados")
    cursor.execute("SELECT id, nome, email, tipo, regiao FROM usuarios")
    usuarios = cursor.fetchall()
    df_usuarios = pd.DataFrame(usuarios, columns=["ID", "Nome", "Email", "Tipo", "Região"])
    st.dataframe(df_usuarios)

    st.markdown("### ✏️ Editar ou Excluir Usuário")
    usuario_ids = df_usuarios["ID"].tolist()
    usuario_selecionado = st.selectbox("Selecione o ID do usuário", usuario_ids)

    usuario_atual = df_usuarios[df_usuarios["ID"] == usuario_selecionado].iloc[0]
    novo_nome = st.text_input("Nome", value=usuario_atual["Nome"])
    novo_tipo = st.selectbox("Tipo", ["admin", "usuario"], index=["admin", "usuario"].index(usuario_atual["Tipo"]))
    nova_regiao = st.selectbox("Região", ["BA", "MT"], index=["BA", "MT"].index(usuario_atual["Região"]))

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Salvar Alterações"):
            cursor.execute("""
                UPDATE usuarios SET nome = ?, tipo = ?, regiao = ? WHERE id = ?
            """, (novo_nome, novo_tipo, nova_regiao, usuario_selecionado))
            conn.commit()
            st.success("Usuário atualizado com sucesso!")
            st.rerun()

    with col2:
        if st.button("Excluir Usuário"):
            cursor.execute("DELETE FROM usuarios WHERE id = ?", (usuario_selecionado,))
            conn.commit()
            st.warning("Usuário excluído com sucesso!")
            st.rerun()

    conn.close()

# Exemplo de controle por região (em cada funcionalidade):
if opcao == "Histórico de Formatações":
    st.write(f"🔎 Mostrando dados da região: **{st.session_state.usuario_regiao}**")
    # Aplica filtro por região
    dados = listar_formatacoes()
    if st.session_state.usuario_tipo != "admin":
        dados = [d for d in dados if d[2] == st.session_state.usuario_regiao]  # Safra está na posição 2

    if not dados:
        st.info("Nenhuma formatação registrada ainda para sua região.")
    else:
        df_historico = pd.DataFrame(dados, columns=[
            "ID", "Lote", "Safra", "Produtor", "Data do HVI", "Data da Formatação", "UsuárioID", "Total de Fardos"
        ])
        st.dataframe(df_historico)

        formatacao_selecionada = st.selectbox(
            "Selecione uma formatação para ver os fardos:",
            options=df_historico["ID"]
        )

        df_fardos = listar_fardos_por_formatacao(formatacao_selecionada)
        st.write(f"🔍 Mostrando {len(df_fardos)} fardos do lote selecionado:")
        st.dataframe(df_fardos)

if opcao == "Exportar do Banco":
    if st.session_state.usuario_tipo != "admin":
        st.error("Apenas administradores podem acessar esta área.")
        st.stop()

    st.write(f"📊 Exportando dados da região: **{st.session_state.usuario_regiao}**")
    df_banco = consultar_registros_completos()

    if st.session_state.usuario_tipo != "admin":
        df_banco = df_banco[df_banco["Safra"] == st.session_state.usuario_regiao]

    st.dataframe(df_banco)

    buffer = BytesIO()
    df_banco.to_excel(buffer, index=False, engine="openpyxl")
    buffer.seek(0)

    st.download_button(
        label="📥 Baixar Excel da Região",
        data=buffer,
        file_name=f"SIFHVI_Exportacao_{datetime.now().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.success("Exportação permitida para administradores.")