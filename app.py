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

        if participacoes.empty:
            st.info("Nenhum participante ainda.")
        else:
            for _, row in participacoes.iterrows():
                col1, col2 = st.columns([4,1])
                col1.write(f"{row['nome']} - {row['papel']} ({row['presenca']})")

                if col2.button("❌", key=f"del_part_{row['id']}"):
                    c.execute("DELETE FROM participacoes WHERE id = ?", (row["id"],))
                    conn.commit()
                    st.rerun()

        if st.button("➕ Gerenciar participantes"):
            st.session_state.mostrar_add_part = not st.session_state.mostrar_add_part

        if st.session_state.mostrar_add_part and not pessoas.empty:

            pessoa_dict = dict(zip(pessoas["nome"], pessoas["id"]))
            pessoa_nome = st.selectbox("Pessoa", list(pessoa_dict.keys()))

            papel = st.selectbox("Papel", ["Participante", "Responsável", "Apoio"])
            presenca = st.selectbox("Presença", ["Confirmado", "Pendente", "Ausente"])

            if st.button("Adicionar"):
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
            projeto_nome = st.selectbox("Projeto", list(projeto_dict.keys()))

        if st.button("💾 Salvar"):
            c.execute("""
                UPDATE eventos
                SET nome=?, data=?, local=?, descricao=?, projeto_id=?
                WHERE id=?
            """, (nome, str(data), local, descricao, projeto_dict.get(projeto_nome), evento["id"]))
            conn.commit()
            st.rerun()

# =====================================================
# 📂 SEÇÕES RECOLHIDAS
# =====================================================
st.divider()

# 👤 PESSOAS
with st.expander("👤 Pessoas", expanded=False):

    nome = st.text_input("Nome", key="p_nome")
    email = st.text_input("Email", key="p_email")
    funcao = st.text_input("Função", key="p_funcao")

    if st.button("Salvar Pessoa"):
        try:
            c.execute("INSERT INTO pessoas (nome, email, funcao) VALUES (?, ?, ?)",
                      (nome, email, funcao))
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

    projetos_df = pd.read_sql("SELECT * FROM projetos", conn)

    for _, row in projetos_df.iterrows():
        with st.expander(f"{row['nome']}"):
            novo_nome = st.text_input("Nome", row["nome"], key=f"proj_nome_{row['id']}")
            nova_cor = st.color_picker("Cor", row["cor"], key=f"proj_cor_{row['id']}")

            if st.button("💾 Salvar", key=f"save_proj_{row['id']}"):
                c.execute("UPDATE projetos SET nome=?, cor=? WHERE id=?",
                          (novo_nome, nova_cor, row["id"]))
                conn.commit()
                st.rerun()

# 📌 NOVO EVENTO
with st.expander("📌 Novo Evento", expanded=False):

    nome = st.text_input("Nome do Evento", key="novo_nome")
    data = st.date_input("Data", key="novo_data")
    local = st.text_input("Local", key="novo_local")
    descricao = st.text_area("Descrição", key="novo_desc")

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
