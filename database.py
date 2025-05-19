import sqlite3
from datetime import datetime
import pandas as pd

DB_NAME = "laudos.db"

def conectar():
    return sqlite3.connect(DB_NAME)

def criar_tabelas():
    with conectar() as conn:
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
                trcnt REAL,
                trar REAL,
                trid TEXT,
                sci REAL,
                csp REAL
            )
        """)
        conn.commit()

def inserir_formatacao(lote, data_hvi, safra, produtor, usuario_id):
    with conectar() as conn:
        cursor = conn.cursor()
        data_formatacao = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO formatacoes (lote, data_formatacao, data_hvi, safra, produtor, usuario_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (lote, data_formatacao, data_hvi, safra, produtor, usuario_id))
        conn.commit()
        return cursor.lastrowid

def inserir_fardos(formatacao_id, df):
    with conectar() as conn:
        cursor = conn.cursor()
        for _, row in df.iterrows():
            cursor.execute("""
                INSERT INTO fardos (
                    formatacao_id, fardo_id, uhml_mm, uhml_pol, ui, sfi, str, elg, mic, mat,
                    rd, b, cgrd, trcnt, trar, trid, sci, csp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                formatacao_id,
                str(row["FardoID"]),
                float(row["UHML_mm"]),
                float(row["UHML_pol"]),
                float(row["UI"]),
                float(row["SFI"]),
                float(row["STR"]),
                float(row["ELG"]),
                float(row["MIC"]),
                float(row["Mat"]),
                float(row["Rd"]),
                float(row["+b"]),
                str(row["CGrd"]),
                float(row["TrCnt"]),
                float(row["TrAr"]),
                str(row["TrID"]),
                float(row["SCI"]),
                float(row["CSP"])
            ))
        conn.commit()

def listar_formatacoes():
    with conectar() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT f.id, f.lote, f.safra, f.produtor, f.data_hvi, f.data_formatacao, f.usuario_id,
                   COUNT(fa.id) as total_fardos
            FROM formatacoes f
            LEFT JOIN fardos fa ON f.id = fa.formatacao_id
            GROUP BY f.id
            ORDER BY f.id DESC
        """)
        return cursor.fetchall()

def listar_fardos_por_formatacao(formatacao_id):
    with conectar() as conn:
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
        return pd.DataFrame(rows, columns=colunas)

def consultar_registros_completos():
    with conectar() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT f.lote, fa.fardo_id, fa.mic, fa.uhml_mm, fa.str, fa.sfi, fa.ui, fa.csp, fa.elg,
                   fa.rd, fa.b, fa.trid, fa.sci, fa.mat, fa.cgrd,
                   ft.produtor, ft.safra, u.nome AS usuario_nome
            FROM fardos fa
            JOIN formatacoes ft ON fa.formatacao_id = ft.id
            JOIN usuarios u ON ft.usuario_id = u.id
            JOIN formatacoes f ON fa.formatacao_id = f.id
        """)
        rows = cursor.fetchall()
        colunas = [
            "LOTE", "FARDO", "MICRONAIR", "UHML_mm", "RES", "SFI", "UNF", "CSP", "ELG",
            "RD", "+B", "LEAF", "SCI", "MAT", "CG", "Produtor", "Safra", "Usuário"
        ]
        return pd.DataFrame(rows, columns=colunas)
