import streamlit as st
import pandas as pd
import pdfplumber
from io import BytesIO
from datetime import datetime
from database import (
    criar_tabelas,
    inserir_formatacao,
    inserir_fardos,
    listar_formatacoes,
    listar_fardos_por_formatacao,
    consultar_registros_completos
)

criar_tabelas()

st.set_page_config(page_title="Processador de Laudos HVI", layout="wide")
st.title("\U0001F4C4 Sistema de Formatação de Laudos HVI")

st.sidebar.title("Menu")
opcao = st.sidebar.radio("Ir para:", ["Processar PDF", "Histórico de Formatações", "Exportar do Banco"])

if opcao == "Processar PDF":
    modelo = st.selectbox("Selecione o modelo de laudo:", ["Abapa", "Outro modelo (em breve)"])
    uploaded_files = st.file_uploader("Envie um ou mais arquivos PDF de laudos HVI", type=["pdf"], accept_multiple_files=True)

    produtor_input = st.text_input("Nome do produtor", value="GELCI ZANCANARO E OUTROS")
    corretora_input = st.text_input("Nome da corretora", value="CORRETORA XYZ")

    if st.button("\U0001F504 Novo Upload (Limpar Tela)"):
        st.session_state.clear()
        st.experimental_rerun()

    df_consolidado = pd.DataFrame()

    if uploaded_files and modelo:
        for uploaded_file in uploaded_files:
            with pdfplumber.open(uploaded_file) as pdf:
                linhas_dados = []
                numero_lote = "Desconhecido"
                safra = "Desconhecida"
                data_hvi = "Desconhecida"

                for page in pdf.pages:
                    texto = page.extract_text()

                    if "Lote:" in texto:
                        for linha in texto.split("\n"):
                            if "Lote:" in linha:
                                partes = linha.split("Lote:")
                                if len(partes) > 1:
                                    numero_lote = partes[1].strip().split()[0]
                            if "Safra:" in linha:
                                safra = linha.split("Safra:")[1].strip().split()[0]
                            if "Data:" in linha:
                                data_hvi = linha.split("Data:")[1].strip().split()[0]

                    for linha in texto.split("\n"):
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

            formatacao_id = inserir_formatacao(numero_lote, data_hvi, safra, produtor_input)
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

        nome_arquivo = f"Resumo Oferta_{datetime.now().strftime('%Y-%m-%d')}_{produtor_input}_{corretora_input}.xlsx".replace(" ", "_")
        buffer = BytesIO()
        df_export.to_excel(buffer, index=False, engine='openpyxl')
        buffer.seek(0)

        st.download_button(
            label="\U0001F4C5 Baixar Excel Consolidado",
            data=buffer,
            file_name=nome_arquivo,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

elif opcao == "Histórico de Formatações":
    st.subheader("\U0001F4CA Histórico de Formatações Realizadas")
    dados = listar_formatacoes()

    if not dados:
        st.info("Nenhuma formatação registrada ainda.")
    else:
        df_historico = pd.DataFrame(dados, columns=[
            "ID", "Lote", "Safra", "Produtor", "Data do HVI", "Data da Formatação", "Total de Fardos"
        ])
        st.dataframe(df_historico)

        formatacao_selecionada = st.selectbox(
            "Selecione uma formatação para ver os fardos:",
            options=df_historico["ID"]
        )

        df_fardos = listar_fardos_por_formatacao(formatacao_selecionada)
        st.write(f"\U0001F50D Mostrando {len(df_fardos)} fardos do lote selecionado:")
        st.dataframe(df_fardos)

elif opcao == "Exportar do Banco":
    st.subheader("\U0001F4C4 Exportar Dados Salvos no Banco")

    df_banco = consultar_registros_completos()

    if df_banco.empty:
        st.info("Ainda não há registros salvos no banco de dados.")
    else:
        safra = st.selectbox("Filtrar por Safra (ou deixe em branco)", [""] + sorted(df_banco["Safra"].unique()))
        produtor = st.selectbox("Filtrar por Produtor (ou deixe em branco)", [""] + sorted(df_banco["Produtor"].unique()))
        lote = st.selectbox("Filtrar por Lote (ou deixe em branco)", [""] + sorted(df_banco["LOTE"].unique()))

        df_filtrado = df_banco.copy()
        if safra:
            df_filtrado = df_filtrado[df_filtrado["Safra"] == safra]
        if produtor:
            df_filtrado = df_filtrado[df_filtrado["Produtor"] == produtor]
        if lote:
            df_filtrado = df_filtrado[df_filtrado["LOTE"] == lote]

        def mm_para_pol(valor):
            try:
                return round(float(valor) / 1000 * 39.3701, 2)
            except:
                return "-"

        def multiplicar_mat(valor):
            try:
                return int(round(float(valor) * 100))
            except:
                return valor

        df_filtrado["UHML"] = df_filtrado["UHML_mm"].apply(mm_para_pol)
        df_filtrado["MAT"] = df_filtrado["MAT"].apply(multiplicar_mat)
        df_filtrado["CG"] = df_filtrado["CG"].astype(str).str.replace("-", ".", regex=False)
        df_filtrado["PESO"] = ""
        df_filtrado["Tipo"] = ""

        df_export = df_filtrado[[
            "LOTE", "FARDO", "MICRONAIR", "UHML", "RES", "PESO", "SFI", "UNF", "CSP", "ELG",
            "RD", "+B", "LEAF", "SCI", "MAT", "CG", "Produtor", "Tipo"
        ]]

        st.success(f"{len(df_export)} registros encontrados.")
        st.dataframe(df_export)

        buffer = BytesIO()
        df_export.to_excel(buffer, index=False, engine='openpyxl')
        buffer.seek(0)

        nome_excel = f"Resumo Banco_{datetime.now().strftime('%Y-%m-%d')}.xlsx"

        st.download_button(
            label="\U0001F4C5 Baixar Excel com dados do banco",
            data=buffer,
            file_name=nome_excel,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )





