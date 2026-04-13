import streamlit as st
import sqlite3
import pandas as pd
from streamlit_calendar import calendar

# ---------------------------
# CONFIG
# ---------------------------
st.set_page_config(
    page_title="Agenda NEGA/UFRGS", 
    page_icon='logo_nega.png',
    layout="wide"
)

# ---------------------------
# HEADER
# ---------------------------
col1, col2, col3 = st.columns([1,4,1])

with col1:
    st.image("logo_nega.png", width=200)

with col2:
    st.markdown("<h1 style='text-align: center;'>AGENDA NEGA</h1>", unsafe_allow_html=True)

with col3:
    st.image("logo_ufrgs.png", width=250)

# ---------------------------
# CONEXÃO
# ---------------------------
@st.cache_resource
def get_connection():
    return sqlite3.connect("database.db", check_same_thread=False)

conn = get_connection()
c = conn.cursor()

# ---------------------------
# TABELAS
# ---------------------------
def create_tables():
    c.execute("""
    CREATE TABLE IF NOT EXISTS pessoas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT UNIQUE,
        email TEXT,
        funcao TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS projetos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT UNIQUE,
        cor TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS eventos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        data TEXT,
        local TEXT,
        descricao TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS participacoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pessoa_id INTEGER,
        evento_id INTEGER,
        papel TEXT,
        presenca TEXT
    )
    """)

    conn.commit()

create_tables()

# ---------------------------
# MIGRAÇÃO
# ---------------------------
def atualizar_banco():
    try:
        c.execute("ALTER TABLE eventos ADD COLUMN projeto_id INTEGER")
        conn.commit()
    except:
        pass

atualizar_banco()

# ---------------------------
# ESTADO
# ---------------------------
if "evento_id" not in st.session_state:
    st.session_state.evento_id = None

if "fechar_evento_flag" not in st.session_state:
    st.session_state.fechar_evento_flag = False

# =====================================================
# 📅 CALENDÁRIO
# =====================================================
query = """
SELECT e.*, p.cor
FROM eventos e
LEFT JOIN projetos p ON e.projeto_id = p.id
"""

eventos_df = pd.read_sql(query, conn)

eventos_calendar = [
    {
        "title": row["nome"],
        "start": row["data"],
        "id": str(row["id"]),
        "color": row["cor"] if row["cor"] else "#3788d8"
    }
    for _, row in eventos_df.iterrows()
]

state = calendar(events=eventos_calendar, options={"initialView": "dayGridMonth", "locale": "pt-br", "height": 650})

if state.get("eventClick") and not st.session_state.fechar_evento_flag:
    st.session_state.evento_id = int(state["eventClick"]["event"]["id"])

if st.session_state.fechar_evento_flag:
    st.session_state.fechar_evento_flag = False

# =====================================================
# 📂 PROJETOS (EDITÁVEL)
# =====================================================
st.divider()

with st.expander("📁 Projetos", expanded=False):

    st.subheader("➕ Novo Projeto")

    novo_nome = st.text_input("Nome do Projeto")
    nova_cor = st.color_picker("Cor", "#3788d8", key="nova_cor")

    if st.button("Salvar Projeto"):
        try:
            c.execute("INSERT INTO projetos (nome, cor) VALUES (?, ?)", (novo_nome, nova_cor))
            conn.commit()
            st.success("Projeto criado!")
            st.rerun()
        except:
            st.warning("Projeto já existe.")

    st.divider()
    st.subheader("✏️ Editar Projetos")

    projetos_df = pd.read_sql("SELECT * FROM projetos", conn)

    for _, row in projetos_df.iterrows():

        with st.expander(f"{row['nome']}"):

            novo_nome_edit = st.text_input("Nome", row["nome"], key=f"proj_nome_{row['id']}")
            nova_cor_edit = st.color_picker("Cor", row["cor"], key=f"proj_cor_{row['id']}")

            col1, col2 = st.columns(2)

            with col1:
                if st.button("💾 Salvar", key=f"save_proj_{row['id']}"):
                    c.execute("""
                        UPDATE projetos
                        SET nome=?, cor=?
                        WHERE id=?
                    """, (novo_nome_edit, nova_cor_edit, row["id"]))
                    conn.commit()
                    st.success("Atualizado!")
                    st.rerun()

            with col2:
                if st.button("🗑️ Excluir", key=f"del_proj_{row['id']}"):
                    c.execute("DELETE FROM projetos WHERE id = ?", (row["id"],))
                    conn.commit()
                    st.warning("Projeto excluído!")
                    st.rerun()
