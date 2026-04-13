import streamlit as st
import sqlite3
import pandas as pd
from streamlit_calendar import calendar

# ---------------------------
# CONFIG
# ---------------------------
st.set_page_config(page_title="Agenda", layout="wide")

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
# ESTADO
# ---------------------------
if "evento_id" not in st.session_state:
    st.session_state.evento_id = None

# =====================================================
# 📅 CALENDÁRIO
# =====================================================
st.title("📅 Agenda de Eventos")

eventos_df = pd.read_sql("SELECT * FROM eventos", conn)

eventos_calendar = [
    {"title": row["nome"], "start": row["data"], "id": str(row["id"])}
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

if state.get("eventClick"):
    st.session_state.evento_id = int(state["eventClick"]["event"]["id"])

# =====================================================
# 📌 DETALHES DO EVENTO
# =====================================================
if st.session_state.evento_id:

    evento = pd.read_sql(
        "SELECT * FROM eventos WHERE id = ?",
        conn,
        params=(st.session_state.evento_id,)
    ).iloc[0]

    st.divider()
    st.subheader("📌 Editar Evento")

    nome = st.text_input("Nome", evento["nome"], key="edit_nome")
    data = st.date_input("Data", pd.to_datetime(evento["data"]), key="edit_data")
    local = st.text_input("Local", evento["local"], key="edit_local")
    descricao = st.text_area("Descrição", evento["descricao"], key="edit_desc")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("💾 Salvar", key="btn_salvar_evento"):
            c.execute("""
                UPDATE eventos
                SET nome=?, data=?, local=?, descricao=?
                WHERE id=?
            """, (nome, str(data), local, descricao, evento["id"]))
            conn.commit()
            st.success("Evento atualizado!")
            st.rerun()

    with col2:
        if st.button("🗑️ Excluir Evento", key="btn_excluir_evento"):
            c.execute("DELETE FROM eventos WHERE id = ?", (evento["id"],))
            conn.commit()
            st.session_state.evento_id = None
            st.warning("Evento excluído!")
            st.rerun()

    # ---------------------------
    # PARTICIPANTES
    # ---------------------------
    st.subheader("👥 Participantes")

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

    if not pessoas.empty:
        pessoa_dict = dict(zip(pessoas["nome"], pessoas["id"]))
        pessoa_nome = st.selectbox("Adicionar pessoa", list(pessoa_dict.keys()), key="select_pessoa")

        papel = st.selectbox("Papel", ["Participante", "Responsável", "Apoio"], key="papel")
        presenca = st.selectbox("Presença", ["Confirmado", "Pendente", "Ausente"], key="presenca")

        if st.button("➕ Adicionar participante", key="add_participante"):
            c.execute("""
                INSERT INTO participacoes (pessoa_id, evento_id, papel, presenca)
                VALUES (?, ?, ?, ?)
            """, (pessoa_dict[pessoa_nome], evento["id"], papel, presenca))
            conn.commit()
            st.rerun()

# =====================================================
# 📂 ABAS
# =====================================================
st.divider()
tab1, tab2 = st.tabs(["👤 Pessoas", "📌 Novo Evento"])

# ---------------------------
# 👤 PESSOAS
# ---------------------------
with tab1:
    st.header("👤 Cadastro de Pessoas")

    nome = st.text_input("Nome", key="p_nome")
    email = st.text_input("Email", key="p_email")
    funcao = st.text_input("Função", key="p_funcao")

    if st.button("Salvar Pessoa", key="btn_salvar_pessoa"):
        try:
            c.execute(
                "INSERT INTO pessoas (nome, email, funcao) VALUES (?, ?, ?)",
                (nome, email, funcao)
            )
            conn.commit()
            st.success("Pessoa cadastrada!")
            st.rerun()
        except:
            st.warning("Pessoa já existe.")

    st.subheader("📋 Pessoas cadastradas")

    pessoas_df = pd.read_sql("SELECT * FROM pessoas", conn)

    for _, row in pessoas_df.iterrows():
        with st.expander(f"{row['nome']}"):
            novo_nome = st.text_input("Nome", row["nome"], key=f"nome_{row['id']}")
            novo_email = st.text_input("Email", row["email"], key=f"email_{row['id']}")
            nova_funcao = st.text_input("Função", row["funcao"], key=f"funcao_{row['id']}")

            col1, col2 = st.columns(2)

            with col1:
                if st.button("💾 Salvar", key=f"save_p_{row['id']}"):
                    c.execute("""
                        UPDATE pessoas
                        SET nome=?, email=?, funcao=?
                        WHERE id=?
                    """, (novo_nome, novo_email, nova_funcao, row["id"]))
                    conn.commit()
                    st.success("Atualizado!")
                    st.rerun()

            with col2:
                if st.button("🗑️ Excluir", key=f"del_p_{row['id']}"):
                    c.execute("DELETE FROM pessoas WHERE id = ?", (row["id"],))
                    conn.commit()
                    st.warning("Pessoa excluída!")
                    st.rerun()

# ---------------------------
# 📌 NOVO EVENTO
# ---------------------------
with tab2:
    st.header("📌 Criar Evento")

    nome = st.text_input("Nome do Evento", key="novo_nome")
    data = st.date_input("Data", key="novo_data")
    local = st.text_input("Local", key="novo_local")
    descricao = st.text_area("Descrição", key="novo_desc")

    if st.button("Salvar Evento", key="btn_salvar_evento_novo"):
        c.execute("""
            INSERT INTO eventos (nome, data, local, descricao)
            VALUES (?, ?, ?, ?)
        """, (nome, str(data), local, descricao))
        conn.commit()
        st.success("Evento criado!")
        st.rerun()
