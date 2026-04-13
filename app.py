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
# MIGRAÇÃO (ADICIONA COLUNA)
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

if "mostrar_add_part" not in st.session_state:
    st.session_state.mostrar_add_part = False

if "fechar_evento_flag" not in st.session_state:
    st.session_state.fechar_evento_flag = False

# =====================================================
# 📅 CALENDÁRIO COM CORES
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

state = calendar(
    events=eventos_calendar,
    options={
        "initialView": "dayGridMonth",
        "locale": "pt-br",
        "height": 650
    },
    key="calendar"
)

if state.get("eventClick") and not st.session_state.fechar_evento_flag:
    st.session_state.evento_id = int(state["eventClick"]["event"]["id"])
    st.session_state.mostrar_add_part = False

if st.session_state.fechar_evento_flag:
    st.session_state.fechar_evento_flag = False

# =====================================================
# 📌 DETALHES EVENTO
# =====================================================
if st.session_state.evento_id is not None:

    evento = pd.read_sql(
        "SELECT * FROM eventos WHERE id = ?",
        conn,
        params=(st.session_state.evento_id,)
    ).iloc[0]

    st.divider()

    col_title, col_close = st.columns([5,1])

    with col_title:
        st.subheader(f"📌 {evento['nome']}")

    with col_close:
        if st.button("❌ Fechar"):
            st.session_state.evento_id = None
            st.session_state.fechar_evento_flag = True
            st.rerun()

    tab_part, tab_edit = st.tabs(["👥 Participantes", "✏️ Editar Evento"])

    # 👥 PARTICIPANTES
    with tab_part:

        pessoas = pd.read_sql("SELECT * FROM pessoas", conn)

        participacoes = pd.read_sql("""
            SELECT pa.id, p.nome, pa.papel, pa.presenca
            FROM participacoes pa
            JOIN pessoas p ON pa.pessoa_id = p.id
            WHERE pa.evento_id = ?
        """, conn, params=(evento["id"],))

        for _, row in participacoes.iterrows():
            col1, col2 = st.columns([4,1])
            col1.write(f"{row['nome']} - {row['papel']} ({row['presenca']})")

            if col2.button("❌", key=f"del_part_{row['id']}"):
                c.execute("DELETE FROM participacoes WHERE id = ?", (row["id"],))
                conn.commit()
                st.rerun()

    # ✏️ EDITAR EVENTO
    with tab_edit:

        nome = st.text_input("Nome", evento["nome"])
        data = st.date_input("Data", pd.to_datetime(evento["data"]))
        local = st.text_input("Local", evento["local"])
        descricao = st.text_area("Descrição", evento["descricao"])

        projetos = pd.read_sql("SELECT * FROM projetos", conn)

        if not projetos.empty:
            projeto_dict = dict(zip(projetos["nome"], projetos["id"]))
            projeto_nome = st.selectbox("Projeto", list(projeto_dict.keys()))

        if st.button("Salvar"):
            c.execute("""
                UPDATE eventos
                SET nome=?, data=?, local=?, descricao=?, projeto_id=?
                WHERE id=?
            """, (
                nome, str(data), local, descricao,
                projeto_dict.get(projeto_nome),
                evento["id"]
            ))
            conn.commit()
            st.rerun()

# =====================================================
# 📂 SEÇÕES
# =====================================================
st.divider()

# 👤 PESSOAS
with st.expander("👤 Pessoas", expanded=False):

    nome = st.text_input("Nome")
    email = st.text_input("Email")
    funcao = st.text_input("Função")

    if st.button("Salvar Pessoa"):
        try:
            c.execute(
                "INSERT INTO pessoas (nome, email, funcao) VALUES (?, ?, ?)",
                (nome, email, funcao)
            )
            conn.commit()
            st.rerun()
        except:
            st.warning("Pessoa já existe.")

# 📁 PROJETOS
with st.expander("📁 Projetos", expanded=False):

    nome = st.text_input("Nome do Projeto")
    cor = st.color_picker("Cor", "#3788d8")

    if st.button("Salvar Projeto"):
        try:
            c.execute("INSERT INTO projetos (nome, cor) VALUES (?, ?)", (nome, cor))
            conn.commit()
            st.rerun()
        except:
            st.warning("Projeto já existe.")

    st.dataframe(pd.read_sql("SELECT * FROM projetos", conn))

# 📌 NOVO EVENTO
with st.expander("📌 Novo Evento", expanded=False):

    nome = st.text_input("Nome do Evento")
    data = st.date_input("Data")
    local = st.text_input("Local")
    descricao = st.text_area("Descrição")

    projetos = pd.read_sql("SELECT * FROM projetos", conn)

    if not projetos.empty:
        projeto_dict = dict(zip(projetos["nome"], projetos["id"]))
        projeto_nome = st.selectbox("Projeto", list(projeto_dict.keys()))
    else:
        projeto_nome = None

    if st.button("Salvar Evento") and projeto_nome:
        c.execute("""
            INSERT INTO eventos (nome, data, local, descricao, projeto_id)
            VALUES (?, ?, ?, ?, ?)
        """, (nome, str(data), local, descricao, projeto_dict[projeto_nome]))
        conn.commit()
        st.success("Evento criado!")
        st.rerun()
