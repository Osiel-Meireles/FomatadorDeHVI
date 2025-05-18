import sqlite3
from datetime import datetime
import pandas as pd

DB_NAME = "laudos.db"

def conectar():
    return sqlite3.connect(DB_NAME)

def criar_tabelas():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        email TEXT UNIQUE,
        senha_hash TEXT,
        tipo TEXT,  -- 'admin' ou 'usuario'
        regiao TEXT,  -- 'MT' ou 'BA'
        senha_temporaria INTEGER  -- 1 se temporária, 0 se definitiva
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS formatacoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lote TEXT,
        data_formatacao TEXT,
        data_hvi TEXT,
        safra TEXT,
        produtor TEXT,
        usuario_id INTEGER
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS fardos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        formatacao_id INTEGER,
        fardo_id TEXT,
        uhml_mm REAL,
        uhml_pol REAL,
        ui REAL,
        sfi REAL,
        str REAL,
        elg REAL,
        mic REAL,
        mat REAL,
        rd REAL,
        b REAL,
        cgrd TEXT,
        trcnt INTEGER,
        trar REAL,
        trid TEXT,
        sci INTEGER,
        csp INTEGER
    )
    """)

    conn.commit()
    conn.close()

def inserir_formatacao(lote, data_hvi, safra, produtor, usuario_id):
    conn = conectar()
    cursor = conn.cursor()
    data_formatacao = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO formatacoes (lote, data_formatacao, data_hvi, safra, produtor, usuario_id)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (lote, data_formatacao, data_hvi, safra, produtor, usuario_id))
    conn.commit()
    formatacao_id = cursor.lastrowid
    conn.close()
    return formatacao_id

def inserir_fardos(formatacao_id, df):
    conn = conectar()
    cursor = conn.cursor()
    for _, row in df.iterrows():
        cursor.execute("""
            INSERT INTO fardos (
                formatacao_id, fardo_id, uhml_mm, uhml_pol, ui, sfi, str, elg, mic, mat,
                rd, b, cgrd, trcnt, trar, trid, sci, csp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            formatacao_id, row["FardoID"], row["UHML_mm"], row["UHML_pol"], row["UI"], row["SFI"],
            row["STR"], row["ELG"], row["MIC"], row["Mat"], row["Rd"], row["+b"], row["CGrd"],
            row["TrCnt"], row["TrAr"], row["TrID"], row["SCI"], row["CSP"]
        ))
    conn.commit()
    conn.close()

def listar_formatacoes():
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT f.id, f.lote, f.safra, f.produtor, f.data_hvi, f.data_formatacao, f.usuario_id,
               COUNT(fa.id) as total_fardos
        FROM formatacoes f
        LEFT JOIN fardos fa ON f.id = fa.formatacao_id
        GROUP BY f.id
        ORDER BY f.id DESC
    """)
    resultado = cursor.fetchall()
    conn.close()
    return resultado

def listar_fardos_por_formatacao(formatacao_id):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT fardo_id, uhml_mm, uhml_pol, ui, sfi, str, elg, mic, mat,
               rd, b, cgrd, trcnt, trar, trid, sci, csp
        FROM fardos
        WHERE formatacao_id = ?
    """, (formatacao_id,))
    colunas = [
        "FardoID", "UHML_mm", "UHML_pol", "UI", "SFI", "STR", "ELG", "MIC", "Mat",
        "Rd", "+b", "CGrd", "TrCnt", "TrAr", "TrID", "SCI", "CSP"
    ]
    rows = cursor.fetchall()
    conn.close()
    return pd.DataFrame(rows, columns=colunas)

def consultar_registros_completos():
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT f.lote, fa.fardo_id, fa.mic, fa.uhml_mm, fa.str, fa.sfi, fa.ui, fa.csp, fa.elg,
               fa.rd, fa.b, fa.trid, fa.sci, fa.mat, fa.cgrd,
               ft.produtor, ft.safra
        FROM fardos fa
        JOIN formatacoes ft ON fa.formatacao_id = ft.id
        JOIN formatacoes f ON fa.formatacao_id = f.id
    """)
    rows = cursor.fetchall()
    conn.close()
    colunas = [
        "LOTE", "FARDO", "MICRONAIR", "UHML_mm", "RES", "SFI", "UNF", "CSP", "ELG",
        "RD", "+B", "LEAF", "SCI", "MAT", "CG", "Produtor", "Safra"
    ]
    return pd.DataFrame(rows, columns=colunas)
