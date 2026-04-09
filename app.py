import streamlit as st
import sqlite3
import pandas as pd

# ---------------------------
# CONFIG
# ---------------------------
st.set_page_config(page_title="Agenda", layout="wide")

# ---------------------------
# CONEXÃO COM BANCO
# ---------------------------
@st.cache_resource
def get_connection():
    return sqlite3.connect("database.db", check_same_thread=False)

conn = get_connection()
c = conn.cursor()

# ---------------------------
# CRIAR TABELAS
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
        nome TEXT UNIQUE
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
# PRÉ-CADASTRO (EDITAR AQUI 👇)
# ---------------------------
def seed_data():

    # 🔹 INSIRA NOMES AQUI
    pessoas_iniciais = [
        ("Cláudia Zeferino", "sem@email.com", "Professora"),
        ("Lara Machado", "sem@email.com", "Doutora"),
        ("Bruno", "sem@email.com", "Doutor"),
        ("Laisa Zatti", "sem@email.com", "Mestre"),
        ("Giulia Sichelero", "sem@email.com", "Mestre"),
        ("Laura Flores", "sem@email.comm", "Mestre"),
        ("Mileny", "sem@email.com", "Mestre"),
        ("Ruan", "sem@email.com", "Voluntário"),
        ("Ismael", "sem@email.com", "Bolsista"),
        ("Bárbara", "sem@email.com", "Bolsista"),
        ("Ismael", "sem@email.com", "Bolsista"),
        ("Francine", "sem@email.com", "Bolsista"),
        ("Adriane", "sem@email.com", "Bolsista"),
        
        # 👉 ADICIONE MAIS PESSOAS AQUI
    ]

    for nome, email, funcao in pessoas_iniciais:
        try:
            c.execute("INSERT INTO pessoas (nome, email, funcao) VALUES (?, ?, ?)",
                      (nome, email, funcao))
        except:
            pass

    # 🔹 INSIRA PROJETOS AQUI
    projetos_iniciais = [
        ("Projeto A",),
        ("Projeto B",),
        # 👉 ADICIONE MAIS PROJETOS AQUI
    ]

    for projeto in projetos_iniciais:
        try:
            c.execute("INSERT INTO projetos (nome) VALUES (?)", projeto)
        except:
            pass

    conn.commit()

seed_data()

# ---------------------------
# MENU
# ---------------------------
st.title("📅 Agenda de Eventos")

menu = ["Calendário", "Pessoas", "Projetos", "Eventos", "Participações"]
choice = st.sidebar.selectbox("Menu", menu)

# ---------------------------
# CALENDÁRIO
# ---------------------------
if choice == "Calendário":
    st.subheader("📅 Eventos")

    query = """
    SELECT e.id, e.nome, e.data, e.local,
           COALESCE(p.nome, 'Sem projeto') as projeto
    FROM eventos e
    LEFT JOIN projetos p ON e.projeto_id = p.id
    """

    df = pd.read_sql(query, conn)

    if not df.empty:
        df["data"] = pd.to_datetime(df["data"])
        df = df.sort_values("data")

        st.dataframe(df, use_container_width=True)

        st.subheader("🔎 Filtrar por data")
        data = st.date_input("Escolha uma data")

        filtro = df[df["data"] == pd.to_datetime(data)]
        st.dataframe(filtro, use_container_width=True)

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
        try:
            c.execute("INSERT INTO pessoas (nome, email, funcao) VALUES (?, ?, ?)",
                      (nome, email, funcao))
            conn.commit()
            st.success("Pessoa cadastrada!")
        except:
            st.warning("Pessoa já existe.")

    df = pd.read_sql("SELECT * FROM pessoas", conn)
    st.dataframe(df, use_container_width=True)

# ---------------------------
# PROJETOS
# ---------------------------
elif choice == "Projetos":
    st.subheader("📁 Cadastro de Projetos")

    nome = st.text_input("Nome do Projeto")

    if st.button("Salvar Projeto"):
        try:
            c.execute("INSERT INTO projetos (nome) VALUES (?)", (nome,))
            conn.commit()
            st.success("Projeto criado!")
        except:
            st.warning("Projeto já existe.")

    df = pd.read_sql("SELECT * FROM projetos", conn)
    st.dataframe(df, use_container_width=True)

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

    if not projetos.empty:
        projeto_dict = dict(zip(projetos["nome"], projetos["id"]))
        projeto_nome = st.selectbox("Projeto", list(projeto_dict.keys()))
    else:
        st.warning("Cadastre um projeto primeiro.")
        projeto_nome = None

    if st.button("Salvar Evento") and projeto_nome:
        c.execute("""
        INSERT INTO eventos (nome, data, local, descricao, projeto_id)
        VALUES (?, ?, ?, ?, ?)
        """, (nome, str(data), local, descricao, projeto_dict[projeto_nome]))
        conn.commit()
        st.success("Evento criado!")

    df = pd.read_sql("SELECT * FROM eventos", conn)
    st.dataframe(df, use_container_width=True)

# ---------------------------
# PARTICIPAÇÕES
# ---------------------------
elif choice == "Participações":
    st.subheader("🔗 Vincular Pessoa a Evento")

    pessoas = pd.read_sql("SELECT * FROM pessoas", conn)
    eventos = pd.read_sql("SELECT * FROM eventos", conn)

    if not pessoas.empty and not eventos.empty:
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

    else:
        st.warning("Cadastre pessoas e eventos primeiro.")
