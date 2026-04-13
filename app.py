import streamlit as st
import sqlite3
import pandas as pd

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

# ---------------------------
# TABS
# ---------------------------
tab1, tab2, tab3 = st.tabs(["📅 Calendário", "👤 Pessoas", "📌 Novo Evento"])

# =====================================================
# 📅 CALENDÁRIO (SEMPRE VISÍVEL)
# =====================================================
with tab1:
    st.title("📅 Agenda de Eventos")

    eventos = pd.read_sql("SELECT * FROM eventos", conn)

    st.subheader("📅 Eventos")

    if eventos.empty:
        st.info("Nenhum evento ainda. Crie um novo na aba 'Novo Evento'.")
    else:
        eventos["data"] = pd.to_datetime(eventos["data"])
        eventos = eventos.sort_values("data")

        for _, row in eventos.iterrows():
            col1, col2 = st.columns([3, 1])

            with col1:
                if st.button(f"{row['data'].date()} - {row['nome']}", key=row["id"]):
                    st.session_state.evento_id = row["id"]

            with col2:
                st.write(row["local"])

    # ---------------------------
    # DETALHES DO EVENTO
    # ---------------------------
    if st.session_state.evento_id:
        st.divider()
        st.subheader("📌 Detalhes do Evento")

        evento = pd.read_sql(
            "SELECT * FROM eventos WHERE id = ?",
            conn,
            params=(st.session_state.evento_id,)
        ).iloc[0]

        nome = st.text_input("Nome", evento["nome"])
        data = st.date_input("Data", pd.to_datetime(evento["data"]))
        local = st.text_input("Local", evento["local"])
        descricao = st.text_area("Descrição", evento["descricao"])

        if st.button("💾 Salvar Alterações"):
            c.execute("""
            UPDATE eventos
            SET nome=?, data=?, local=?, descricao=?
            WHERE id=?
            """, (nome, str(data), local, descricao, evento["id"]))
            conn.commit()
            st.success("Atualizado!")

        # PARTICIPANTES
        st.subheader("👥 Participantes")

        pessoas = pd.read_sql("SELECT * FROM pessoas", conn)

        participacoes = pd.read_sql("""
            SELECT p.nome, pa.papel, pa.presenca
            FROM participacoes pa
            JOIN pessoas p ON pa.pessoa_id = p.id
            WHERE pa.evento_id = ?
        """, conn, params=(evento["id"],))

        st.dataframe(participacoes, use_container_width=True)

        # ADICIONAR PARTICIPANTE
        if not pessoas.empty:
            pessoa_dict = dict(zip(pessoas["nome"], pessoas["id"]))
            pessoa_nome = st.selectbox("Adicionar pessoa", list(pessoa_dict.keys()))

            papel = st.selectbox("Papel", ["Participante", "Responsável", "Apoio"])
            presenca = st.selectbox("Presença", ["Confirmado", "Pendente", "Ausente"])

            if st.button("➕ Adicionar participante"):
                c.execute("""
                    INSERT INTO participacoes (pessoa_id, evento_id, papel, presenca)
                    VALUES (?, ?, ?, ?)
                """, (pessoa_dict[pessoa_nome], evento["id"], papel, presenca))
                conn.commit()
                st.success("Adicionado!")
        else:
            st.warning("Cadastre pessoas primeiro.")

# =====================================================
# 👤 PESSOAS
# =====================================================
with tab2:
    st.header("👤 Cadastro de Pessoas")

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
            st.success("Pessoa cadastrada!")
        except:
            st.warning("Pessoa já existe.")

    st.subheader("📋 Lista de Pessoas")
    df_pessoas = pd.read_sql("SELECT * FROM pessoas", conn)
    st.dataframe(df_pessoas, use_container_width=True)

# =====================================================
# 📌 NOVO EVENTO
# =====================================================
with tab3:
    st.header("📌 Criar Evento")

    nome = st.text_input("Nome do Evento")
    data = st.date_input("Data")
    local = st.text_input("Local")
    descricao = st.text_area("Descrição")

    if st.button("Salvar Evento"):
        c.execute("""
            INSERT INTO eventos (nome, data, local, descricao)
            VALUES (?, ?, ?, ?)
        """, (nome, str(data), local, descricao))
        conn.commit()
        st.success("Evento criado!")
        
