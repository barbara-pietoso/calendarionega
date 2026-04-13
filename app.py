# =====================================================
# 📌 DETALHES DO EVENTO (ATUALIZADO)
# =====================================================
if st.session_state.evento_id:

    evento = pd.read_sql(
        "SELECT * FROM eventos WHERE id = ?",
        conn,
        params=(st.session_state.evento_id,)
    ).iloc[0]

    st.divider()
    st.subheader(f"📌 {evento['nome']}")

    # ---------------------------
    # TABS INTERNAS
    # ---------------------------
    tab_part, tab_edit = st.tabs(["👥 Participantes", "✏️ Editar Evento"])

    # =====================================================
    # 👥 PARTICIPANTES (PRIMEIRO)
    # =====================================================
    with tab_part:

        st.subheader("👥 Participantes")

        pessoas = pd.read_sql("SELECT * FROM pessoas", conn)

        participacoes = pd.read_sql("""
            SELECT pa.id, p.nome, pa.papel, pa.presenca
            FROM participacoes pa
            JOIN pessoas p ON pa.pessoa_id = p.id
            WHERE pa.evento_id = ?
        """, conn, params=(evento["id"],))

        # LISTA DE PARTICIPANTES
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

        # ---------------------------
        # BOTÃO PARA MOSTRAR FORMULÁRIO
        # ---------------------------
        if "mostrar_add_part" not in st.session_state:
            st.session_state.mostrar_add_part = False

        if st.button("➕ Gerenciar participantes"):
            st.session_state.mostrar_add_part = not st.session_state.mostrar_add_part

        # ---------------------------
        # FORMULÁRIO (APENAS SE ATIVADO)
        # ---------------------------
        if st.session_state.mostrar_add_part:

            st.divider()

            if not pessoas.empty:
                pessoa_dict = dict(zip(pessoas["nome"], pessoas["id"]))
                pessoa_nome = st.selectbox("Pessoa", list(pessoa_dict.keys()), key="select_pessoa_evento")

                papel = st.selectbox("Papel", ["Participante", "Responsável", "Apoio"], key="papel_evento")
                presenca = st.selectbox("Presença", ["Confirmado", "Pendente", "Ausente"], key="presenca_evento")

                if st.button("Adicionar", key="add_participante_evento"):
                    c.execute("""
                        INSERT INTO participacoes (pessoa_id, evento_id, papel, presenca)
                        VALUES (?, ?, ?, ?)
                    """, (pessoa_dict[pessoa_nome], evento["id"], papel, presenca))
                    conn.commit()
                    st.rerun()
            else:
                st.warning("Cadastre pessoas primeiro.")

    # =====================================================
    # ✏️ EDITAR EVENTO
    # =====================================================
    with tab_edit:

        st.subheader("✏️ Editar Evento")

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
