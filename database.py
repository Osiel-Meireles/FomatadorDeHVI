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
        tipo TEXT,
        regiao TEXT,
        senha_temporaria INTEGER
    )""")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS formatacoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lote TEXT,
        data_formatacao TEXT,
        data_hvi TEXT,
        safra TEXT,
        produtor TEXT,
        usuario_id INTEGER
    )""")

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
    )""")

    conn.commit()
    conn.close()

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
