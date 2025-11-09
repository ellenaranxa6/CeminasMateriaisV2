# ---------------------------------------------------------
# MODO DE ENTRADA: Planilha ou Inserção Manual
# ---------------------------------------------------------
st.header("📦 Escolha o modo de entrada dos dados do projeto")

modo_entrada = st.radio(
    "Selecione o modo de entrada:",
    ("📥 Enviar planilha de estruturas (.xlsx)", "🧱 Inserir manualmente as estruturas"),
    horizontal=True
)

banco_estruturas = "MateriaisEstrutura.xlsx"

# =============================
# 🔹 MODO 1 - UPLOAD (FLUXO ATUAL)
# =============================
if modo_entrada == "📥 Enviar planilha de estruturas (.xlsx)":
    st.header("📤 Enviar planilha de estruturas do projeto")
    uploaded_file = st.file_uploader("Envie o arquivo **EstruturasProjeto.xlsx**", type=["xlsx"])

    if uploaded_file is not None:
        st.success("✅ Arquivo recebido com sucesso!")
        projeto_path = "EstruturasProjeto.xlsx"
        with open(projeto_path, "wb") as f:
            f.write(uploaded_file.read())

        st.divider()
        st.header("🏗️ Configuração da Obra")
        st.session_state["obra"] = st.text_input("Nome da obra:", st.session_state["obra"])
        obra_limpa = "".join(c for c in st.session_state["obra"] if c.isalnum() or c in (" ", "-", "_")).strip()
        arquivo_saida = f"Ceminas - Materiais - {obra_limpa}.xlsx"

        iniciar = st.button("⚙️ Validar e Gerar Relação")
        if iniciar:
            st.session_state["pending_generate"] = True
            st.session_state["corrections_submitted"] = False
            st.session_state["correcoes_dict"] = {}
            st.session_state["correcoes_choices"] = {}
            st.rerun()

# =============================
# 🔹 MODO 2 - INSERÇÃO MANUAL
# =============================
else:
    st.header("🧱 Inserção Manual de Estruturas")
    st.info("Preencha as estruturas do projeto diretamente na plataforma. Apenas combinações existentes no banco são permitidas.")

    try:
        banco = pd.read_excel(banco_estruturas, engine="openpyxl")
        banco.columns = banco.columns.str.strip().str.upper()
        for col in ["ESTRUTURA", "EQUIPAMENTO", "CONDUTOR", "POSTE"]:
            banco[col] = banco[col].fillna("").astype(str).str.strip().str.upper()
    except Exception as e:
        st.error(f"❌ Erro ao carregar banco de estruturas: {e}")
        st.stop()

    # Cria dataframe base se não existir
    if "manual_df" not in st.session_state:
        st.session_state["manual_df"] = pd.DataFrame(columns=["ESTRUTURA", "EQUIPAMENTO", "CONDUTOR", "POSTE", "QUANTIDADE"])

    df = st.session_state["manual_df"]

    # Interface de entrada
    with st.form("inserir_estrutura"):
        estrutura = st.selectbox("Estrutura:", sorted(banco["ESTRUTURA"].unique()))
        eq_opts = sorted(banco[banco["ESTRUTURA"] == estrutura]["EQUIPAMENTO"].unique())
        equipamento = st.selectbox("Equipamento:", eq_opts)

        cond_opts = sorted(banco[(banco["ESTRUTURA"] == estrutura) & (banco["EQUIPAMENTO"] == equipamento)]["CONDUTOR"].unique())
        condutor = st.selectbox("Condutor:", cond_opts)

        poste_opts = sorted(banco[(banco["ESTRUTURA"] == estrutura) & (banco["EQUIPAMENTO"] == equipamento) & (banco["CONDUTOR"] == condutor)]["POSTE"].unique())
        poste = st.selectbox("Poste:", poste_opts)

        quantidade = st.number_input("Quantidade:", min_value=1, value=1, step=1)

        adicionar = st.form_submit_button("➕ Adicionar Estrutura")

    # Ao adicionar, salva na sessão
    if adicionar:
        nova_linha = pd.DataFrame([{
            "ESTRUTURA": estrutura,
            "EQUIPAMENTO": equipamento,
            "CONDUTOR": condutor,
            "POSTE": poste,
            "QUANTIDADE": quantidade
        }])
        st.session_state["manual_df"] = pd.concat([df, nova_linha], ignore_index=True)
        st.success(f"✅ Estrutura {estrutura} adicionada com sucesso!")

    # Mostrar tabela
    if not st.session_state["manual_df"].empty:
        st.subheader("📋 Estruturas Inseridas")
        st.dataframe(st.session_state["manual_df"], use_container_width=True)

        # Botão para limpar
        if st.button("🗑️ Limpar Lista"):
            st.session_state["manual_df"] = pd.DataFrame(columns=["ESTRUTURA", "EQUIPAMENTO", "CONDUTOR", "POSTE", "QUANTIDADE"])
            st.rerun()

        # Geração
        st.divider()
        gerar_manual = st.button("⚙️ Gerar Relação de Materiais")

        if gerar_manual:
            projeto_corrigido = st.session_state["manual_df"].copy()
            obra_limpa = "".join(c for c in st.session_state["obra"] if c.isalnum() or c in (" ", "-", "_")).strip()
            arquivo_saida = f"Ceminas - Materiais - {obra_limpa}.xlsx"

            materiais_lista = []
            for _, row in projeto_corrigido.iterrows():
                flt = (
                    (banco["ESTRUTURA"] == row["ESTRUTURA"]) &
                    (banco["EQUIPAMENTO"] == row["EQUIPAMENTO"]) &
                    (banco["CONDUTOR"] == row["CONDUTOR"]) &
                    (banco["POSTE"] == row["POSTE"])
                )
                encontrados = banco.loc[flt].copy()
                if not encontrados.empty:
                    encontrados["QTD_PROJETO"] = row["QUANTIDADE"]
                    materiais_lista.append(encontrados)

            if materiais_lista:
                materiais = pd.concat(materiais_lista, ignore_index=True)
                materiais["QTD_TOTAL"] = materiais["QUANTIDADE"] * materiais["QTD_PROJETO"]
                relacao = (
                    materiais.groupby(["CODIGO", "DESCRIÇÃO", "UNIDADE"], as_index=False)["QTD_TOTAL"]
                    .sum()
                    .sort_values("DESCRIÇÃO")
                )

                buffer = BytesIO()
                relacao.to_excel(buffer, index=False)
                st.success(f"✅ Relação consolidada gerada com sucesso para {st.session_state['obra']}")
                st.download_button(
                    label="📥 Baixar planilha gerada",
                    data=buffer.getvalue(),
                    file_name=arquivo_saida,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            else:
                st.warning("⚠️ Nenhuma estrutura válida encontrada para geração da relação.")
