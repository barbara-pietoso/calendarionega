import streamlit as st
import sqlite3
import pandas as pd
from streamlit_calendar import calendar

# ---------------------------
# CONFIG
# ---------------------------
st.set_page_config(
    page_title="Agenda NEGA/UFRGS",
    page_icon="logo_nega.png",
    layout="wide"
)

# ---------------------------
# LOGIN SIMPLES
# ---------------------------
USERS = {
    "coordenadoras": "nega2026",
    "integrantes": "nega2026"
}

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "usuario" not in st.session_state:
    st.session_state.usuario = None

if not st.session_state.logged_in:

    st.title("🔐 Login")

    usuario = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")

    if st.button("Entrar"):

        if usuario in USERS and USERS[usuario] == senha:
            st.session_state.logged_in = True
            st.session_state.usuario = usuario
            st.rerun()

        else:
            st.error("Usuário ou senha inválidos.")

    st.stop()

# ---------------------------
# HEADER
# ---------------------------
col1, col2, col3 = st.columns([1, 4, 1])

with col1:
    st.image("logo_nega.png", width=200)

with col2:
    st.markdown(
        """
        <h1 style='text-align: center; margin-bottom: 0;'>
            AGENDA NEGA
        </h1>

        <div style='text-align: center; font-size: 0.95rem;'>
            <a href="https://www.ufrgs.br/nega/" target="_blank">
                Acessar site oficial ↗
            </a>
        </div>
        """,
        unsafe_allow_html=True
    )

with col3:
    st.image("logo_ufrgs.png", width=250)

    st.caption(f"👤 {st.session_state.usuario}")

    if st.button("Sair"):
        st.session_state.logged_in = False
        st.session_state.usuario = None
        st.rerun()

# ---------------------------
# CONEXÃO
# ---------------------------
@st.cache_resource
def get_connection():
    conn = sqlite3.connect(
        "database.db",
        check_same_thread=False
    )

    conn.execute("PRAGMA foreign_keys = ON")

    return conn


conn = get_connection()
c = conn.cursor()

# ---------------------------
# TABELAS
# ---------------------------
def create_tables():

    c.execute("""
    CREATE TABLE IF NOT EXISTS pessoas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        funcao TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS projetos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL UNIQUE,
        cor TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS eventos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        data TEXT NOT NULL,
        local TEXT,
        descricao TEXT,
        projeto_id INTEGER,

        FOREIGN KEY (projeto_id)
        REFERENCES projetos(id)
        ON DELETE SET NULL
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS participacoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,

        pessoa_id INTEGER NOT NULL,
        evento_id INTEGER NOT NULL,

        papel TEXT,
        presenca TEXT,

        FOREIGN KEY (pessoa_id)
        REFERENCES pessoas(id)
        ON DELETE CASCADE,

        FOREIGN KEY (evento_id)
        REFERENCES eventos(id)
        ON DELETE CASCADE,

        UNIQUE (pessoa_id, evento_id)
    )
    """)

    conn.commit()


create_tables()

# ---------------------------
# ESTADO DA SESSÃO
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
SELECT
    e.*,
    p.cor
FROM eventos e
LEFT JOIN projetos p
    ON e.projeto_id = p.id
"""

eventos_df = pd.read_sql(query, conn)

eventos_calendar = [
    {
        "title": row["nome"],
        "start": row["data"],
        "id": str(row["id"]),
        "color": (
            row["cor"]
            if row["cor"]
            else "#3788d8"
        )
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

if (
    state.get("eventClick")
    and not st.session_state.fechar_evento_flag
):

    st.session_state.evento_id = int(
        state["eventClick"]["event"]["id"]
    )

    st.session_state.mostrar_add_part = False

if st.session_state.fechar_evento_flag:
    st.session_state.fechar_evento_flag = False

# =====================================================
# 📌 DETALHES DO EVENTO
# =====================================================
if st.session_state.evento_id is not None:

    evento_df = pd.read_sql(
        """
        SELECT *
        FROM eventos
        WHERE id = ?
        """,
        conn,
        params=(st.session_state.evento_id,)
    )

    if not evento_df.empty:

        evento = evento_df.iloc[0]

        st.divider()

        col1, col2 = st.columns([5, 1])

        with col1:
            st.subheader(f"📌 {evento['nome']}")

        with col2:
            if st.button(
                "❌ Fechar",
                key="fechar_evento_btn"
            ):
                st.session_state.evento_id = None
                st.session_state.fechar_evento_flag = True
                st.rerun()

        tab_part, tab_edit = st.tabs(
            [
                "👥 Participantes",
                "✏️ Editar Evento"
            ]
        )

        # =====================================================
        # 👥 PARTICIPANTES
        # =====================================================
        with tab_part:

            pessoas = pd.read_sql(
                """
                SELECT *
                FROM pessoas
                ORDER BY nome
                """,
                conn
            )

            participacoes = pd.read_sql(
                """
                SELECT
                    pa.id,
                    p.nome,
                    pa.papel,
                    pa.presenca
                FROM participacoes pa
                INNER JOIN pessoas p
                    ON pa.pessoa_id = p.id
                WHERE pa.evento_id = ?
                ORDER BY p.nome
                """,
                conn,
                params=(evento["id"],)
            )

            if participacoes.empty:

                st.info(
                    "Nenhum participante cadastrado neste evento."
                )

            else:

                for _, row in participacoes.iterrows():

                    colA, colB = st.columns([5, 1])

                    with colA:
                        st.write(
                            f"• {row['nome']} "
                            f"- {row['papel']} "
                            f"({row['presenca']})"
                        )

                    with colB:

                        if st.button(
                            "❌",
                            key=f"del_part_{row['id']}"
                        ):

                            c.execute(
                                """
                                DELETE FROM participacoes
                                WHERE id = ?
                                """,
                                (row["id"],)
                            )

                            conn.commit()

                            st.success(
                                "Participante removido."
                            )

                            st.rerun()

            if st.button(
                "➕ Gerenciar participantes",
                key="btn_toggle_part"
            ):

                st.session_state.mostrar_add_part = (
                    not st.session_state.mostrar_add_part
                )

            if (
                st.session_state.mostrar_add_part
                and not pessoas.empty
            ):

                st.divider()

                pessoa_dict = dict(
                    zip(
                        pessoas["nome"],
                        pessoas["id"]
                    )
                )

                pessoa_nome = st.selectbox(
                    "Pessoa",
                    list(pessoa_dict.keys()),
                    key="select_pessoa_evento"
                )

                papel = st.selectbox(
                    "Papel",
                    [
                        "Participante",
                        "Responsável",
                        "Apoio"
                    ],
                    key="papel_evento"
                )

                presenca = st.selectbox(
                    "Presença",
                    [
                        "Confirmado",
                        "Pendente",
                        "Ausente"
                    ],
                    key="presenca_evento"
                )

                if st.button(
                    "Adicionar participante",
                    key="btn_add_part"
                ):

                    try:

                        c.execute(
                            """
                            INSERT INTO participacoes (
                                pessoa_id,
                                evento_id,
                                papel,
                                presenca
                            )
                            VALUES (?, ?, ?, ?)
                            """,
                            (
                                pessoa_dict[pessoa_nome],
                                evento["id"],
                                papel,
                                presenca
                            )
                        )

                        conn.commit()

                        st.success(
                            "Participante adicionado."
                        )

                        st.rerun()

                    except sqlite3.IntegrityError:

                        st.warning(
                            "Esta pessoa já está vinculada "
                            "a este evento."
                        )

            elif pessoas.empty:

                st.warning(
                    "Cadastre integrantes antes "
                    "de adicioná-los aos eventos."
                )

        # =====================================================
        # ✏️ EDITAR EVENTO
        # =====================================================
        with tab_edit:

            nome = st.text_input(
                "Nome",
                value=evento["nome"],
                key="edit_nome"
            )

            data = st.date_input(
                "Data",
                value=pd.to_datetime(
                    evento["data"]
                ),
                key="edit_data"
            )

            local = st.text_input(
                "Local",
                value=evento["local"]
                if evento["local"]
                else "",
                key="edit_local"
            )

            descricao = st.text_area(
                "Descrição",
                value=evento["descricao"]
                if evento["descricao"]
                else "",
                key="edit_desc"
            )

            projetos = pd.read_sql(
                """
                SELECT *
                FROM projetos
                ORDER BY nome
                """,
                conn
            )

            projeto_id = evento["projeto_id"]

            projeto_nome = None
            projeto_dict = {}

            if not projetos.empty:

                projeto_dict = dict(
                    zip(
                        projetos["nome"],
                        projetos["id"]
                    )
                )

                nomes_projetos = list(
                    projeto_dict.keys()
                )

                indice = 0

                if projeto_id is not None:

                    for i, nome_proj in enumerate(
                        nomes_projetos
                    ):

                        if (
                            projeto_dict[nome_proj]
                            == projeto_id
                        ):
                            indice = i
                            break

                projeto_nome = st.selectbox(
                    "Projeto",
                    nomes_projetos,
                    index=indice,
                    key="edit_projeto"
                )

            if st.button(
                "💾 Salvar",
                key="btn_salvar_evento"
            ):

                c.execute(
                    """
                    UPDATE eventos
                    SET
                        nome = ?,
                        data = ?,
                        local = ?,
                        descricao = ?,
                        projeto_id = ?
                    WHERE id = ?
                    """,
                    (
                        nome,
                        str(data),
                        local,
                        descricao,
                        projeto_dict.get(
                            projeto_nome
                        )
                        if projeto_nome
                        else None,
                        evento["id"]
                    )
                )

                conn.commit()

                st.success(
                    "Evento atualizado."
                )

                st.rerun()



# =====================================================
# 📂 CADASTROS
# =====================================================

st.divider()

# =====================================================
# 👤 INTEGRANTES
# =====================================================
with st.expander("👤 Integrantes", expanded=False):

    tab1, tab2 = st.tabs(
        ["📋 Lista / Edição", "➕ Cadastro"]
    )

    # =================================================
    # 📋 LISTA / EDIÇÃO
    # =================================================
    with tab1:

        pessoas_df = pd.read_sql(
            """
            SELECT *
            FROM pessoas
            ORDER BY nome
            """,
            conn
        )

        if pessoas_df.empty:

            st.info("Nenhum integrante cadastrado.")

        else:

            for _, row in pessoas_df.iterrows():

                with st.expander(f"{row['nome']}"):

                    nome_edit = st.text_input(
                        "Nome",
                        value=row["nome"],
                        key=f"nome_{row['id']}"
                    )

                    email_edit = st.text_input(
                        "Email",
                        value=row["email"],
                        key=f"email_{row['id']}"
                    )

                    funcao_edit = st.text_input(
                        "Função",
                        value=row["funcao"] or "",
                        key=f"funcao_{row['id']}"
                    )

                    col1, col2 = st.columns(2)

                    with col1:

                        if st.button(
                            "💾 Salvar",
                            key=f"save_pessoa_{row['id']}"
                        ):

                            try:

                                c.execute(
                                    """
                                    UPDATE pessoas
                                    SET
                                        nome = ?,
                                        email = ?,
                                        funcao = ?
                                    WHERE id = ?
                                    """,
                                    (
                                        nome_edit.strip(),
                                        email_edit.strip().lower(),
                                        funcao_edit.strip(),
                                        row["id"]
                                    )
                                )

                                conn.commit()

                                st.success(
                                    "Integrante atualizado."
                                )

                                st.rerun()

                            except sqlite3.IntegrityError:

                                st.warning(
                                    "Já existe um integrante "
                                    "com este e-mail."
                                )

                    with col2:

                        if st.button(
                            "🗑️ Excluir",
                            key=f"del_pessoa_{row['id']}"
                        ):

                            c.execute(
                                """
                                DELETE FROM pessoas
                                WHERE id = ?
                                """,
                                (row["id"],)
                            )

                            conn.commit()

                            st.success(
                                "Integrante removido."
                            )

                            st.rerun()

    # =================================================
    # ➕ CADASTRO
    # =================================================
    with tab2:

        nome = st.text_input(
            "Nome",
            key="p_nome"
        )

        email = st.text_input(
            "Email",
            key="p_email"
        )

        funcao = st.text_input(
            "Função",
            key="p_funcao"
        )

        if st.button(
            "Salvar Integrante",
            key="btn_salvar_pessoa"
        ):

            if not nome.strip():

                st.warning("Informe o nome.")

            elif not email.strip():

                st.warning("Informe o e-mail.")

            else:

                try:

                    c.execute(
                        """
                        INSERT INTO pessoas (
                            nome,
                            email,
                            funcao
                        )
                        VALUES (?, ?, ?)
                        """,
                        (
                            nome.strip(),
                            email.strip().lower(),
                            funcao.strip()
                        )
                    )

                    conn.commit()

                    st.success(
                        "Integrante cadastrado."
                    )

                    st.rerun()

                except sqlite3.IntegrityError:

                    st.warning(
                        "Já existe um integrante "
                        "com este e-mail."
                    )

# =====================================================
# 📁 PROJETOS
# =====================================================
with st.expander("📁 Projetos", expanded=False):

    tab1, tab2 = st.tabs(
        ["📋 Lista / Edição", "➕ Cadastro"]
    )

    # =================================================
    # 📋 LISTA / EDIÇÃO
    # =================================================
    with tab1:

        projetos_df = pd.read_sql(
            """
            SELECT *
            FROM projetos
            ORDER BY nome
            """,
            conn
        )

        if projetos_df.empty:

            st.info("Nenhum projeto cadastrado.")

        else:

            for _, row in projetos_df.iterrows():

                with st.expander(row["nome"]):

                    nome_edit = st.text_input(
                        "Nome",
                        value=row["nome"],
                        key=f"proj_nome_{row['id']}"
                    )

                    cor_edit = st.color_picker(
                        "Cor",
                        value=row["cor"],
                        key=f"proj_cor_{row['id']}"
                    )

                    col1, col2 = st.columns(2)

                    with col1:

                        if st.button(
                            "💾 Salvar",
                            key=f"save_proj_{row['id']}"
                        ):

                            try:

                                c.execute(
                                    """
                                    UPDATE projetos
                                    SET
                                        nome = ?,
                                        cor = ?
                                    WHERE id = ?
                                    """,
                                    (
                                        nome_edit.strip(),
                                        cor_edit,
                                        row["id"]
                                    )
                                )

                                conn.commit()

                                st.success(
                                    "Projeto atualizado."
                                )

                                st.rerun()

                            except sqlite3.IntegrityError:

                                st.warning(
                                    "Já existe um projeto "
                                    "com este nome."
                                )

                    with col2:

                        if st.button(
                            "🗑️ Excluir",
                            key=f"del_proj_{row['id']}"
                        ):

                            c.execute(
                                """
                                DELETE FROM projetos
                                WHERE id = ?
                                """,
                                (row["id"],)
                            )

                            conn.commit()

                            st.success(
                                "Projeto removido."
                            )

                            st.rerun()

    # =================================================
    # ➕ CADASTRO
    # =================================================
    with tab2:

        nome = st.text_input(
            "Nome do Projeto",
            key="proj_nome"
        )

        cor = st.color_picker(
            "Cor",
            "#3788d8",
            key="proj_cor"
        )

        if st.button(
            "Salvar Projeto",
            key="btn_salvar_projeto"
        ):

            if not nome.strip():

                st.warning(
                    "Informe o nome do projeto."
                )

            else:

                try:

                    c.execute(
                        """
                        INSERT INTO projetos (
                            nome,
                            cor
                        )
                        VALUES (?, ?)
                        """,
                        (
                            nome.strip(),
                            cor
                        )
                    )

                    conn.commit()

                    st.success(
                        "Projeto cadastrado."
                    )

                    st.rerun()

                except sqlite3.IntegrityError:

                    st.warning(
                        "Já existe um projeto "
                        "com este nome."
                    )



# =====================================================
# 📌 EVENTOS
# =====================================================
with st.expander("📌 Eventos", expanded=False):

    tab1, tab2 = st.tabs(
        ["📋 Lista / Edição", "➕ Cadastro"]
    )

    # Inicializa estado de confirmação
    if "confirmar_exclusao_evento" not in st.session_state:
        st.session_state.confirmar_exclusao_evento = None

    # =================================================
    # 📋 LISTA / EDIÇÃO
    # =================================================
    with tab1:

        eventos_df = pd.read_sql(
            """
            SELECT *
            FROM eventos
            ORDER BY data DESC, nome
            """,
            conn
        )

        projetos_df = pd.read_sql(
            """
            SELECT *
            FROM projetos
            ORDER BY nome
            """,
            conn
        )

        projeto_dict = {}
        projeto_nomes = []

        if not projetos_df.empty:
            projeto_dict = dict(
                zip(
                    projetos_df["nome"],
                    projetos_df["id"]
                )
            )

            projeto_nomes = list(
                projeto_dict.keys()
            )

        if eventos_df.empty:

            st.info(
                "Nenhum evento cadastrado."
            )

        else:

            for _, row in eventos_df.iterrows():

                titulo = (
                    f"{row['data']} - "
                    f"{row['nome']}"
                )

                with st.expander(titulo):

                    nome_edit = st.text_input(
                        "Nome",
                        value=row["nome"],
                        key=f"ev_nome_{row['id']}"
                    )

                    data_edit = st.date_input(
                        "Data",
                        value=pd.to_datetime(
                            row["data"]
                        ),
                        key=f"ev_data_{row['id']}"
                    )

                    local_edit = st.text_input(
                        "Local",
                        value=row["local"] or "",
                        key=f"ev_local_{row['id']}"
                    )

                    descricao_edit = st.text_area(
                        "Descrição",
                        value=row["descricao"] or "",
                        key=f"ev_desc_{row['id']}"
                    )

                    projeto_nome = None

                    if projeto_nomes:

                        indice = 0

                        if row["projeto_id"] is not None:

                            for i, nome_proj in enumerate(
                                projeto_nomes
                            ):
                                if (
                                    projeto_dict[nome_proj]
                                    == row["projeto_id"]
                                ):
                                    indice = i
                                    break

                        projeto_nome = st.selectbox(
                            "Projeto",
                            projeto_nomes,
                            index=indice,
                            key=f"ev_proj_{row['id']}"
                        )

                    col1, col2 = st.columns(2)

                    # -------------------------
                    # SALVAR
                    # -------------------------
                    with col1:

                        if st.button(
                            "💾 Salvar",
                            key=f"save_evento_{row['id']}"
                        ):

                            projeto_id = None

                            if (
                                projeto_nome
                                and projeto_nome
                                in projeto_dict
                            ):
                                projeto_id = (
                                    projeto_dict[
                                        projeto_nome
                                    ]
                                )

                            c.execute(
                                """
                                UPDATE eventos
                                SET
                                    nome = ?,
                                    data = ?,
                                    local = ?,
                                    descricao = ?,
                                    projeto_id = ?
                                WHERE id = ?
                                """,
                                (
                                    nome_edit.strip(),
                                    str(data_edit),
                                    local_edit.strip(),
                                    descricao_edit.strip(),
                                    projeto_id,
                                    row["id"]
                                )
                            )

                            conn.commit()

                            st.success(
                                "Evento atualizado."
                            )

                            st.rerun()

                    # -------------------------
                    # EXCLUIR
                    # -------------------------
                    with col2:

                        if (
                            st.session_state
                            .confirmar_exclusao_evento
                            == row["id"]
                        ):

                            st.warning(
                                "Tem certeza?"
                            )

                            col_conf1, col_conf2 = (
                                st.columns(2)
                            )

                            with col_conf1:

                                if st.button(
                                    "✅ Confirmar",
                                    key=f"confirm_del_{row['id']}"
                                ):

                                    c.execute(
                                        """
                                        DELETE FROM eventos
                                        WHERE id = ?
                                        """,
                                        (row["id"],)
                                    )

                                    conn.commit()

                                    if (
                                        st.session_state.evento_id
                                        == row["id"]
                                    ):
                                        st.session_state.evento_id = None

                                    st.session_state.confirmar_exclusao_evento = None

                                    st.success(
                                        "Evento excluído."
                                    )

                                    st.rerun()

                            with col_conf2:

                                if st.button(
                                    "Cancelar",
                                    key=f"cancel_del_{row['id']}"
                                ):

                                    st.session_state.confirmar_exclusao_evento = None

                                    st.rerun()

                        else:

                            if st.button(
                                "🗑️ Excluir",
                                key=f"del_evento_{row['id']}"
                            ):

                                st.session_state.confirmar_exclusao_evento = (
                                    row["id"]
                                )

                                st.rerun()

    # =================================================
    # ➕ CADASTRO
    # =================================================
    with tab2:

        nome = st.text_input(
            "Nome do Evento",
            key="novo_nome"
        )

        data = st.date_input(
            "Data",
            key="novo_data"
        )

        local = st.text_input(
            "Local",
            key="novo_local"
        )

        descricao = st.text_area(
            "Descrição",
            key="novo_desc"
        )

        projetos = pd.read_sql(
            """
            SELECT *
            FROM projetos
            ORDER BY nome
            """,
            conn
        )

        projeto_dict = {}
        projeto_nome = None

        if not projetos.empty:

            projeto_dict = dict(
                zip(
                    projetos["nome"],
                    projetos["id"]
                )
            )

            projeto_nome = st.selectbox(
                "Projeto",
                list(projeto_dict.keys()),
                key="novo_projeto"
            )

        else:

            st.info(
                "Nenhum projeto cadastrado. "
                "O evento será criado sem projeto."
            )

        if st.button(
            "Salvar Evento",
            key="btn_salvar_evento_novo"
        ):

            if not nome.strip():

                st.warning(
                    "Informe o nome do evento."
                )

            else:

                projeto_id = None

                if (
                    projeto_nome
                    and projeto_nome
                    in projeto_dict
                ):
                    projeto_id = (
                        projeto_dict[
                            projeto_nome
                        ]
                    )

                c.execute(
                    """
                    INSERT INTO eventos (
                        nome,
                        data,
                        local,
                        descricao,
                        projeto_id
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        nome.strip(),
                        str(data),
                        local.strip(),
                        descricao.strip(),
                        projeto_id
                    )
                )

                conn.commit()

                st.success(
                    "Evento criado."
                )

                st.rerun()





