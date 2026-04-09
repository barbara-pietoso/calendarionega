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
    CREATE TABLE IF NOT EXISTS projetos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS eventos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        data TEXT,
        local TEXT,
        descricao TEXT,
        projeto_id INTEGER,
        FOREIGN KEY (projeto_id) REFERENCES projetos(id)
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
# PRÉ-CADASTRO (executa só uma vez)
# ---------------------------
def seed_data():
    pessoas = pd.read_sql("SELECT * FROM pessoas", conn)
    if pessoas.empty:
        c.execute("INSERT INTO pessoas (nome, email, funcao) VALUES ('João', 'joao@email.com', 'Aluno')")
        c.execute("INSERT INTO pessoas (nome, email, funcao) VALUES ('Maria', 'maria@email.com', 'Professora')")
        conn.commit()

seed_data()

# ---------------------------
# Interface
# ---------------------------
st.title("📅 Agenda Inteligente")

menu = ["Calendário", "Pessoas", "Projetos", "Eventos", "Participações"]
choice = st.sidebar.selectbox("Menu", menu)

# ---------------------------
# CALENDÁRIO
# ---------------------------
if choice == "Calendário":
    st.subheader("📅 Visualização de Eventos")

    query = """
    SELECT e.nome, e.data, e.local, pr.nome as projeto
    FROM eventos e
    LEFT JOIN projetos pr ON e.projeto_id = pr.id
    """
    df = pd.read_sql(query, conn)

    if not df.empty:
        df["data"] = pd.to_datetime(df["data"])
        df = df.sort_values("data")

        st.dataframe(df)

        st.subheader("📆 Calendário")
        st.write("Use o filtro abaixo:")

        data_selecionada = st.date_input("Escolha uma data")

        filtro = df[df["data"] == pd.to_datetime(data_selecionada)]
        st.dataframe(filtro)
    else:
        st.info("Nenhum evento cadastrado.")

# ---------------------------
# PESSOAS
# ---------------------------
elif choice == "Pessoas":
    st.subheader("👤 Cadastro de Pessoas")

    nome = st.text_input("Nome")
    email = st.text_input("Email")
    funcao = st.text_input("Função")

    if st.button("Salvar Pessoa"):
        c.execute("INSERT INTO pessoas (nome, email, funcao) VALUES (?, ?, ?)",
                  (nome, email, funcao))
        conn.commit()
        st.success("Pessoa cadastrada!")

    df = pd.read_sql("SELECT * FROM pessoas", conn)
    st.dataframe(df)

# ---------------------------
# PROJETOS
# ---------------------------
elif choice == "Projetos":
    st.subheader("📁 Cadastro de Projetos")

    nome = st.text_input("Nome do Projeto")

    if st.button("Salvar Projeto"):
        c.execute("INSERT INTO projetos (nome) VALUES (?)", (nome,))
        conn.commit()
        st.success("Projeto criado!")

    df = pd.read_sql("SELECT * FROM projetos", conn)
    st.dataframe(df)

# ---------------------------
# EVENTOS
# ---------------------------
elif choice == "Eventos":
    st.subheader("📌 Criar Evento")

    nome = st.text_input("Nome do Evento")
    data = st.date_input("Data")
    local = st.text_input("Local")
    descricao = st.text_area("Descrição")

    projetos = pd.read_sql("SELECT * FROM projetos", conn)
    projeto_dict = dict(zip(projetos["nome"], projetos["id"]))

    projeto_nome = st.selectbox("Projeto", list(projeto_dict.keys()))

    if st.button("Salvar Evento"):
        c.execute("""
        INSERT INTO eventos (nome, data, local, descricao, projeto_id)
        VALUES (?, ?, ?, ?, ?)
        """, (nome, str(data), local, descricao, projeto_dict[projeto_nome]))
        conn.commit()
        st.success("Evento criado!")

    df = pd.read_sql("SELECT * FROM eventos", conn)
    st.dataframe(df)

# ---------------------------
# PARTICIPAÇÕES
# ---------------------------
elif choice == "Participações":
    st.subheader("🔗 Vincular Pessoa a Evento")

    pessoas = pd.read_sql("SELECT * FROM pessoas", conn)
    eventos = pd.read_sql("SELECT * FROM eventos", conn)

    pessoa_dict = dict(zip(pessoas["nome"], pessoas["id"]))
    evento_dict = dict(zip(eventos["nome"], eventos["id"]))

    pessoa_nome = st.selectbox("Pessoa", list(pessoa_dict.keys()))
    evento_nome = st.selectbox("Evento", list(evento_dict.keys()))

    papel = st.selectbox("Papel", ["Participante", "Responsável", "Apoio"])
    presenca = st.selectbox("Presença", ["Pendente", "Confirmado", "Ausente"])

    if st.button("Adicionar"):
        c.execute("""
        INSERT INTO participacoes (pessoa_id, evento_id, papel, presenca)
        VALUES (?, ?, ?, ?)
        """, (pessoa_dict[pessoa_nome], evento_dict[evento_nome], papel, presenca))
        conn.commit()
        st.success("Participação registrada!")
