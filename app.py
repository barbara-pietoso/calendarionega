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
        descricao TEXT,
        projeto_id INTEGER
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
# ESTADO
# ---------------------------
if "evento_id" not in st.session_state:
    st.session_state.evento_id = None

if "mostrar_add_part" not in st.session_state:
    st.session_state.mostrar_add_part = False

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

state = calendar(
    events=eventos_calendar,
    options={"initialView": "dayGridMonth", "locale": "pt-br", "height": 650},
    key="calendar"
)

if state.get("eventClick") and not st.session_state.fechar_evento_flag:
    st.session_state.evento_id = int(state["eventClick"]["event"]["id"])
    st.session_state.mostrar_add_part = False

if st.session_state.fechar_evento_flag:
    st.session_state.fechar_evento_flag = False

# =====================================================
# 📌 DETALHES DO EVENTO
# =====================================================
if st.session_state.evento_id is not None:

    evento = pd.read_sql(
        "SELECT * FROM eventos WHERE id = ?",
        conn,
        params=(st.session_state.evento_id,)
    ).iloc[0]

    st.divider()

    col1, col2 = st.columns([5,1])

    with col1:
        st.subheader(f"📌 {evento['nome']}")

    with col2:
        if st.button("❌ Fechar", key="fechar_evento_btn"):
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

        if participacoes.empty:
            st.info("Nenhum participante ainda.")
        else:
            for _, row in participacoes.iterrows():
                colA, colB = st.columns([4,1])
                colA.write(f"{row['nome']} - {row['papel']} ({row['presenca']})")

                if colB.button("❌", key=f"del_part_{row['id']}"):
                    c.execute("DELETE FROM participacoes WHERE id=?", (row["id"],))
                    conn.commit()
                    st.rerun()

        if st.button("➕ Gerenciar participantes", key="btn_toggle_part"):
            st.session_state.mostrar_add_part = not st.session_state.mostrar_add_part

        if st.session_state.mostrar_add_part and not pessoas.empty:

            pessoa_dict = dict(zip(pessoas["nome"], pessoas["id"]))
            pessoa_nome = st.selectbox("Pessoa", list(pessoa_dict.keys()), key="select_pessoa_evento")

            papel = st.selectbox("Papel", ["Participante", "Responsável", "Apoio"], key="papel_evento")
            presenca = st.selectbox("Presença", ["Confirmado", "Pendente", "Ausente"], key="presenca_evento")

            if st.button("Adicionar participante", key="btn_add_part"):
                c.execute("""
                    INSERT INTO participacoes (pessoa_id, evento_id, papel, presenca)
                    VALUES (?, ?, ?, ?)
                """, (pessoa_dict[pessoa_nome], evento["id"], papel, presenca))
                conn.commit()
                st.rerun()

    # ✏️ EDITAR EVENTO
    with tab_edit:

        nome = st.text_input("Nome", evento["nome"], key="edit_nome")
        data = st.date_input("Data", pd.to_datetime(evento["data"]), key="edit_data")
        local = st.text_input("Local", evento["local"], key="edit_local")
        descricao = st.text_area("Descrição", evento["descricao"], key="edit_desc")

        projetos = pd.read_sql("SELECT * FROM projetos", conn)

        if not projetos.empty:
            projeto_dict = dict(zip(projetos["nome"], projetos["id"]))
            projeto_nome = st.selectbox("Projeto", list(projeto_dict.keys()), key="edit_projeto")

        if st.button("💾 Salvar", key="btn_salvar_evento"):
            c.execute("""
                UPDATE eventos
                SET nome=?, data=?, local=?, descricao=?, projeto_id=?
                WHERE id=?
            """, (nome, str(data), local, descricao, projeto_dict.get(projeto_nome), evento["id"]))
            conn.commit()
            st.rerun()

# =====================================================
# 📂 CADASTROS
# =====================================================
st.divider()

# 👤 PESSOAS
with st.expander("👤 Integrantes", expanded=False):

    tab1, tab2 = st.tabs(["➕ Cadastrar", "📋 Integrantes"])

    with tab1:
        nome = st.text_input("Nome", key="p_nome")
        email = st.text_input("Email", key="p_email")
        funcao = st.text_input("Função", key="p_funcao")

        if st.button("Salvar Pessoa", key="btn_salvar_pessoa"):
            try:
                c.execute("INSERT INTO pessoas (nome, email, funcao) VALUES (?, ?, ?)",
                          (nome, email, funcao))
                conn.commit()
                st.rerun()
            except:
                st.warning("Pessoa já existe.")

    with tab2:
        pessoas_df = pd.read_sql("SELECT * FROM pessoas", conn)

        for _, row in pessoas_df.iterrows():
            with st.expander(f"{row['nome']}"):
                st.write(row["email"])
                st.write(row["funcao"])

# 📁 PROJETOS
with st.expander("📁 Projetos", expanded=False):

    nome = st.text_input("Nome do Projeto", key="proj_nome")
    cor = st.color_picker("Cor", "#3788d8", key="proj_cor")

    if st.button("Salvar Projeto", key="btn_salvar_projeto"):
        try:
            c.execute("INSERT INTO projetos (nome, cor) VALUES (?, ?)", (nome, cor))
            conn.commit()
            st.rerun()
        except:
            st.warning("Projeto já existe.")

# 📌 NOVO EVENTO
with st.expander("📌 Novo Evento", expanded=False):

    nome = st.text_input("Nome do Evento", key="novo_nome")
    data = st.date_input("Data", key="novo_data")
    local = st.text_input("Local", key="novo_local")
    descricao = st.text_area("Descrição", key="novo_desc")

    projetos = pd.read_sql("SELECT * FROM projetos", conn)

    if not projetos.empty:
        projeto_dict = dict(zip(projetos["nome"], projetos["id"]))
        projeto_nome = st.selectbox("Projeto", list(projeto_dict.keys()), key="novo_projeto")

    if st.button("Salvar Evento", key="btn_salvar_evento_novo"):
        c.execute("""
            INSERT INTO eventos (nome, data, local, descricao, projeto_id)
            VALUES (?, ?, ?, ?, ?)
        """, (nome, str(data), local, descricao, projeto_dict.get(projeto_nome)))
        conn.commit()
        st.rerun()
