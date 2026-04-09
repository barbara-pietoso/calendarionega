import streamlit as st
import sqlite3
import pandas as pd

# ---------------------------
# Banco de dados
# ---------------------------
conn = sqlite3.connect("database.db", check_same_thread=False)
c = conn.cursor()

def create_tables():
    c.execute("""
    CREATE TABLE IF NOT EXISTS pessoas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
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
        presenca TEXT,
        FOREIGN KEY (pessoa_id) REFERENCES pessoas(id),
        FOREIGN KEY (evento_id) REFERENCES eventos(id)
    )
    """)

    conn.commit()

create_tables()

# ---------------------------
# Interface
# ---------------------------
st.title("📅 Agenda com Participantes")

menu = ["Pessoas", "Eventos", "Participações", "Visualizar"]
choice = st.sidebar.selectbox("Menu", menu)

# ---------------------------
# PESSOAS
# ---------------------------
if choice == "Pessoas":
    st.subheader("Cadastrar Pessoa")

    nome = st.text_input("Nome")
    email = st.text_input("Email")
    funcao = st.text_input("Função")

    if st.button("Salvar Pessoa"):
        c.execute("INSERT INTO pessoas (nome, email, funcao) VALUES (?, ?, ?)",
                  (nome, email, funcao))
        conn.commit()
        st.success("Pessoa cadastrada!")

    st.subheader("Lista de Pessoas")
    df = pd.read_sql("SELECT * FROM pessoas", conn)
    st.dataframe(df)

# ---------------------------
# EVENTOS
# ---------------------------
elif choice == "Eventos":
    st.subheader("Criar Evento")

    nome = st.text_input("Nome do Evento")
    data = st.date_input("Data")
    local = st.text_input("Local")
    descricao = st.text_area("Descrição")

    if st.button("Salvar Evento"):
        c.execute("INSERT INTO eventos (nome, data, local, descricao) VALUES (?, ?, ?, ?)",
                  (nome, str(data), local, descricao))
        conn.commit()
        st.success("Evento criado!")

    st.subheader("Lista de Eventos")
    df = pd.read_sql("SELECT * FROM eventos", conn)
    st.dataframe(df)

# ---------------------------
# PARTICIPAÇÕES
# ---------------------------
elif choice == "Participações":
    st.subheader("Vincular Pessoa a Evento")

    pessoas = pd.read_sql("SELECT * FROM pessoas", conn)
    eventos = pd.read_sql("SELECT * FROM eventos", conn)

    pessoa_dict = dict(zip(pessoas["nome"], pessoas["id"]))
    evento_dict = dict(zip(eventos["nome"], eventos["id"]))

    pessoa_nome = st.selectbox("Pessoa", list(pessoa_dict.keys()))
    evento_nome = st.selectbox("Evento", list(evento_dict.keys()))

    papel = st.selectbox("Papel", ["Participante", "Responsável", "Apoio"])
    presenca = st.selectbox("Presença", ["Pendente", "Confirmado", "Ausente"])

    if st.button("Adicionar Participação"):
        c.execute("""
        INSERT INTO participacoes (pessoa_id, evento_id, papel, presenca)
        VALUES (?, ?, ?, ?)
        """, (pessoa_dict[pessoa_nome], evento_dict[evento_nome], papel, presenca))
        conn.commit()
        st.success("Participação registrada!")

# ---------------------------
# VISUALIZAÇÃO
# ---------------------------
elif choice == "Visualizar":
    st.subheader("Eventos com Participantes")

    query = """
    SELECT e.nome as Evento, e.data, e.local,
           p.nome as Pessoa, pa.papel, pa.presenca
    FROM participacoes pa
    JOIN pessoas p ON pa.pessoa_id = p.id
    JOIN eventos e ON pa.evento_id = e.id
    """

    df = pd.read_sql(query, conn)
    st.dataframe(df)

    st.subheader("Filtrar por Pessoa")

    pessoas = df["Pessoa"].unique()
    pessoa_filtro = st.selectbox("Escolha a pessoa", pessoas)

    df_filtrado = df[df["Pessoa"] == pessoa_filtro]
    st.dataframe(df_filtrado)
