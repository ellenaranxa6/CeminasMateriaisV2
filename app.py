# =========================================================
# CEMINAS - GERADOR DE RELAÇÃO DE MATERIAIS (v2.2)
# ---------------------------------------------------------
# - Correção interativa (planilha) com estado persistente
# - Formulário manual coerente (selects encadeados + quantidade)
# - Remoção de itens via data_editor
# =========================================================

import streamlit as st
import pandas as pd
import os
from io import BytesIO

# ============== CONFIG PÁGINA (primeiro comando Streamlit) ==============
st.set_page_config(page_title="Ceminas - Lista de Materiais", page_icon="⚡", layout="centered")

# ========================== ESTILO VISUAL ==========================
st.markdown("""
    <style>
        .main { background-color: #E6F0FF; }
        .title { text-align: center; font-size: 36px; font-weight: 800; color: #003366; margin-top: 10px; }
        .subtitle { text-align: center; font-size: 18px; color: #333; margin-bottom: 30px; }
        .stButton>button {
            background-color: #003366; color: #fff; font-weight: 700;
            border-radius: 8px; padding: .6em 1.2em; transition: 0.3s;
        }
        .stButton>button:hover { background-color: #0059b3; color: #fff; }
    </style>
""", unsafe_allow_html=True)

# ========================== CABEÇALHO ==========================
logo_path = "Logo Ceminas.jpeg"
if os.path.exists(logo_path):
    st.image(logo_path, use_column_width=False, width=250)
st.markdown('<div class="title">CEMINAS – Gerador de Relação de Materiais</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Ferramenta interna para consolidação de materiais de redes de distribuição</div>', unsafe_allow_html=True)
st.divider()

# ========================== AUTENTICAÇÃO ==========================
senha_correta = "Ceminas2025"
if "auth" not in st.session_state:
    st.session_state["auth"] = False
if not st.session_state["auth"]:
    senha = st.text_input("🔐 Digite a senha de acesso:", type="password")
    if senha == senha_correta:
        st.session_state["auth"] = True
        st.success("Acesso liberado! ✅")
        st.rerun()
    else:
        st.stop()

# ========================== ESTADOS GERAIS ==========================
st.session_state.setdefault("obra", "Nova Obra")
st.session_state.setdefault("manual_df", pd.DataFrame(columns=["ESTRUTURA","EQUIPAMENTO","CONDUTOR","POSTE","QUANTIDADE"]))

# Estados do fluxo de planilha (correções)
st.session_state.setdefault("faltantes_df", pd.DataFrame())
st.session_state.setdefault("correcoes_dict", {})
st.session_state.setdefault("pronto_para_gerar", False)  # após aplicar correções

# ========================== HELPERS ==========================
BANCO_PATH = "MateriaisEstrutura.xlsx"

def normalize_text_df(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = df.columns.str.strip().str.upper()
    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = df[col].astype(str).str.strip().str.upper()
    return df

def carregar_banco() -> pd.DataFrame:
    banco = pd.read_excel(BANCO_PATH, engine="openpyxl")
    banco = normalize_text_df(banco)
    for col in ["ESTRUTURA","EQUIPAMENTO","CONDUTOR","POSTE"]:
        banco[col] = banco[col].fillna("").astype(str)
    return banco

def gerar_relacao(estruturas_df: pd.DataFrame, projeto_df: pd.DataFrame) -> pd.DataFrame:
    """Retorna a relação final consolidada (CODIGO, DESCRIÇÃO, UNIDADE, QTD_TOTAL)."""
    materiais_lista = []
    for _, row in projeto_df.iterrows():
        flt = (
            (estruturas_df["ESTRUTURA"] == row["ESTRUTURA"]) &
            (estruturas_df["EQUIPAMENTO"] == row["EQUIPAMENTO"]) &
            (estruturas_df["CONDUTOR"] == row["CONDUTOR"]) &
            (estruturas_df["POSTE"] == row["POSTE"])
        )
        encontrados = estruturas_df.loc[flt].copy()
        if not encontrados.empty:
            encontrados["QTD_PROJETO"] = int(row["QUANTIDADE"])
            materiais_lista.append(encontrados)

    if not materiais_lista:
        return pd.DataFrame()

    materiais = pd.concat(materiais_lista, ignore_index=True)
    # QUANTIDADE (do banco) * QTD_PROJETO (inserida/planilha)
    materiais["QTD_TOTAL"] = materiais["QUANTIDADE"].astype(float) * materiais["QTD_PROJETO"].astype(float)
    relacao = (
        materiais.groupby(["CODIGO","DESCRIÇÃO","UNIDADE"], as_index=False)["QTD_TOTAL"]
        .sum()
        .sort_values("DESCRIÇÃO")
    )
    return relacao

def limpar_estado_planilha():
    st.session_state["faltantes_df"] = pd.DataFrame()
    st.session_state["correcoes_dict"] = {}
    st.session_state["pronto_para_gerar"] = False

# ========================== MODO DE ENTRADA ==========================
st.header("📦 Escolha o modo de entrada dos dados do projeto")
modo_entrada = st.radio(
    "Selecione o modo de entrada:",
    ("📥 Enviar planilha de estruturas (.xlsx)", "🧱 Inserir manualmente as estruturas"),
    horizontal=True
)

# ========================== MODO 1: PLANILHA + CORREÇÃO ==========================
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

        # BOTÃO ÚNICO: valida, corrige (se precisar) e gera
        if st.button("⚙️ Validar / Corrigir / Gerar Relação"):
            try:
                estruturas = carregar_banco()
                projeto = normalize_text_df(pd.read_excel(projeto_path, engine="openpyxl"))
                # Verifica colunas mínimas
                cols_min = {"ESTRUTURA","EQUIPAMENTO","CONDUTOR","POSTE","QUANTIDADE"}
                if not cols_min.issubset(set(projeto.columns)):
                    st.error("❌ A planilha do projeto deve ter as colunas: ESTRUTURA, EQUIPAMENTO, CONDUTOR, POSTE, QUANTIDADE.")
                    st.stop()

                # Monta faltantes
                keys = ["ESTRUTURA","EQUIPAMENTO","CONDUTOR","POSTE"]
                chaves_banco = estruturas[keys].drop_duplicates()
                chaves_proj  = projeto[keys].drop_duplicates()

                faltantes = (
                    chaves_proj.merge(chaves_banco, on=keys, how="left", indicator=True)
                    .query('_merge == "left_only"')
                    .drop(columns="_merge")
                    .reset_index(drop=True)
                )

                st.session_state["faltantes_df"] = faltantes
                st.session_state["correcoes_dict"] = {}  # zera correções anteriores
                st.session_state["pronto_para_gerar"] = False

            except Exception as e:
                st.error(f"❌ Erro ao validar: {e}")
                st.stop()

        # Se há faltantes, abre painel de correções
        if not st.session_state["faltantes_df"].empty and not st.session_state["pronto_para_gerar"]:
            faltantes = st.session_state["faltantes_df"]
            estruturas = carregar_banco()

            st.warning(f"⚠️ Foram encontradas {len(faltantes)} combinações inexistentes no banco.")
            st.markdown("Selecione como tratar cada uma (escolher uma alternativa válida **da mesma estrutura** ou **ignorar**):")

            with st.form("corrigir_faltantes_form"):
                for i, row in faltantes.iterrows():
                    estrutura, equipamento, condutor, poste = row["ESTRUTURA"], row["EQUIPAMENTO"], row["CONDUTOR"], row["POSTE"]
                    st.markdown(f"**❌ Estrutura:** {estrutura} | **Equip:** {equipamento} | **Cond.:** {condutor} | **Poste:** {poste}")

                    sugestoes = (
                        estruturas[estruturas["ESTRUTURA"] == estrutura][["EQUIPAMENTO","CONDUTOR","POSTE"]]
                        .drop_duplicates()
                        .sort_values(by=["EQUIPAMENTO","CONDUTOR","POSTE"])
                        .reset_index(drop=True)
                    )
                    if sugestoes.empty:
                        st.info("🔹 Nenhuma variação cadastrada — esta estrutura será ignorada se mantida sem alternativa.")
                        continue

                    opcoes = ["Ignorar esta estrutura"] + [
                        f"{r['EQUIPAMENTO']} | {r['CONDUTOR']} | {r['POSTE']}"
                        for _, r in sugestoes.iterrows()
                    ]
                    escolha = st.selectbox(
                        f"Alternativa para {estrutura}:",
                        options=opcoes,
                        key=f"falt_{i}"
                    )
                    # Salva escolha no dict
                    if escolha != "Ignorar esta estrutura":
                        eq, cond, pst = [x.strip() for x in escolha.split("|")]
                        st.session_state["correcoes_dict"][(estrutura, equipamento, condutor, poste)] = {
                            "EQUIPAMENTO": eq, "CONDUTOR": cond, "POSTE": pst
                        }
                submitted = st.form_submit_button("✅ Aplicar Correções e Gerar")

            if submitted:
                try:
                    # Recarrega insumo
                    estruturas = carregar_banco()
                    projeto = normalize_text_df(pd.read_excel("EstruturasProjeto.xlsx", engine="openpyxl"))

                    # Aplica correções
                    if st.session_state["correcoes_dict"]:
                        for idx, row in projeto.iterrows():
                            chave = (row["ESTRUTURA"], row["EQUIPAMENTO"], row["CONDUTOR"], row["POSTE"])
                            if chave in st.session_state["correcoes_dict"]:
                                novo = st.session_state["correcoes_dict"][chave]
                                projeto.loc[idx, ["EQUIPAMENTO","CONDUTOR","POSTE"]] = [novo["EQUIPAMENTO"], novo["CONDUTOR"], novo["POSTE"]]

                    # Remove linhas que continuam não existentes (usuário ignorou)
                    keys = ["ESTRUTURA","EQUIPAMENTO","CONDUTOR","POSTE"]
                    projeto = projeto.merge(estruturas[keys].drop_duplicates(), on=keys, how="inner")

                    relacao = gerar_relacao(estruturas, projeto)
                    if relacao.empty:
                        st.warning("⚠️ Após as correções/ignores, não restaram estruturas válidas.")
                    else:
                        buf = BytesIO()
                        relacao.to_excel(buf, index=False)
                        st.success(f"✅ Relação consolidada gerada com sucesso para {st.session_state['obra']}")
                        st.download_button(
                            label="📥 Baixar planilha gerada",
                            data=buf.getvalue(),
                            file_name=f"Ceminas - Materiais - {''.join(c for c in st.session_state['obra'] if c.isalnum() or c in (' ','-','_')).strip()}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    st.session_state["pronto_para_gerar"] = True
                except Exception as e:
                    st.error(f"❌ Erro ao aplicar correções/gerar: {e}")

        # Se não há faltantes e já foi validado, tentar gerar direto
        if st.session_state["faltantes_df"].empty and st.session_state["pronto_para_gerar"] is False:
            # Usuário clicou validar, não havia faltantes. Gerar direto.
            try:
                estruturas = carregar_banco()
                projeto = normalize_text_df(pd.read_excel("EstruturasProjeto.xlsx", engine="openpyxl"))
                relacao = gerar_relacao(estruturas, projeto)
                if relacao.empty:
                    st.warning("⚠️ Nenhuma estrutura válida encontrada.")
                else:
                    buf = BytesIO()
                    relacao.to_excel(buf, index=False)
                    st.success(f"✅ Relação consolidada gerada com sucesso para {st.session_state['obra']}")
                    st.download_button(
                        label="📥 Baixar planilha gerada",
                        data=buf.getvalue(),
                        file_name=f"Ceminas - Materiais - {''.join(c for c in st.session_state['obra'] if c.isalnum() or c in (' ','-','_')).strip()}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                st.session_state["pronto_para_gerar"] = True
            except Exception as e:
                st.error(f"❌ Erro ao gerar relação: {e}")

        # Botão para reiniciar ciclo de planilha
        if st.session_state["pronto_para_gerar"]:
            if st.button("🔄 Novo arquivo / Reiniciar fluxo"):
                limpar_estado_planilha()
                st.rerun()

# ========================== MODO 2: INSERÇÃO MANUAL ==========================
else:
    st.header("🧱 Inserção Manual de Estruturas (com validação)")
    st.info("Selecione somente combinações existentes no banco. Os campos são encadeados e coerentes.")

    try:
        banco = carregar_banco()
    except Exception as e:
        st.error(f"❌ Erro ao carregar o banco: {e}")
        st.stop()

    # ---- Callbacks para resetar filhos quando pai muda ----
    def on_change_estrutura():
        st.session_state.pop("MAN_EQUIPAMENTO", None)
        st.session_state.pop("MAN_CONDUTOR", None)
        st.session_state.pop("MAN_POSTE", None)

    def on_change_equip():
        st.session_state.pop("MAN_CONDUTOR", None)
        st.session_state.pop("MAN_POSTE", None)

    def on_change_cond():
        st.session_state.pop("MAN_POSTE", None)

    # ---- Seletor encadeado (fora do formulário) ----
    col1, col2 = st.columns([1,1])
    with col1:
        estrutura = st.selectbox(
            "Estrutura:",
            sorted(banco["ESTRUTURA"].unique()),
            key="MAN_ESTRUTURA",
            on_change=on_change_estrutura
        )
    with col2:
        eq_opts = sorted(banco[banco["ESTRUTURA"] == estrutura]["EQUIPAMENTO"].unique())
        equipamento = st.selectbox(
            "Equipamento:",
            eq_opts,
            key="MAN_EQUIPAMENTO",
            on_change=on_change_equip
        )

    col3, col4 = st.columns([1,1])
    with col3:
        cond_opts = sorted(banco[(banco["ESTRUTURA"] == estrutura) &
                                 (banco["EQUIPAMENTO"] == equipamento)]["CONDUTOR"].unique())
        condutor = st.selectbox(
            "Condutor:",
            cond_opts,
            key="MAN_CONDUTOR",
            on_change=on_change_cond
        )
    with col4:
        poste_opts = sorted(banco[(banco["ESTRUTURA"] == estrutura) &
                                  (banco["EQUIPAMENTO"] == equipamento) &
                                  (banco["CONDUTOR"] == condutor)]["POSTE"].unique())
        poste = st.selectbox(
            "Poste:",
            poste_opts,
            key="MAN_POSTE"
        )

    st.divider()
    st.subheader("➕ Adicionar Estrutura")

    # ---- Formulário apenas para quantidade e botão ----
    with st.form("form_manual_add"):
        qtd = st.number_input("Quantidade:", min_value=1, value=1, step=1, key="MAN_QTD")
        adicionou = st.form_submit_button("➕ Adicionar Estrutura")
        if adicionou:
            if any(len(opt) == 0 for opt in [eq_opts, cond_opts, poste_opts]):
                st.error("❌ Combinação inválida. Verifique os campos (alguma lista está vazia).")
            else:
                nova = pd.DataFrame([{
                    "ESTRUTURA": estrutura,
                    "EQUIPAMENTO": equipamento,
                    "CONDUTOR": condutor,
                    "POSTE": poste,
                    "QUANTIDADE": qtd
                }])
                st.session_state["manual_df"] = pd.concat([st.session_state["manual_df"], nova], ignore_index=True)
                st.success(f"✅ {qtd} un. de {estrutura} adicionada(s).")

    # ---- Lista e geração ----
    if not st.session_state["manual_df"].empty:
        st.subheader("📋 Estruturas Inseridas")
        df_show = st.session_state["manual_df"].copy()
        df_show["REMOVER"] = False
        edited = st.data_editor(df_show, num_rows="dynamic", use_container_width=True, hide_index=True)

        # Remove linhas marcadas
        if (edited["REMOVER"] == True).any():
            st.session_state["manual_df"] = edited.loc[edited["REMOVER"] != True, ["ESTRUTURA","EQUIPAMENTO","CONDUTOR","POSTE","QUANTIDADE"]]
            st.info("🗑️ Itens removidos. Lista atualizada.")

        colA, colB = st.columns([1,1])
        with colA:
            if st.button("🗑️ Limpar Lista"):
                st.session_state["manual_df"] = pd.DataFrame(columns=["ESTRUTURA","EQUIPAMENTO","CONDUTOR","POSTE","QUANTIDADE"])
                st.rerun()
        with colB:
            gerar_manual = st.button("⚙️ Gerar Relação de Materiais (Manual)")

        if gerar_manual:
            try:
                projeto_corrigido = normalize_text_df(st.session_state["manual_df"].copy())
                relacao = gerar_relacao(banco, projeto_corrigido)
                if relacao.empty:
                    st.warning("⚠️ Nenhuma estrutura válida encontrada.")
                else:
                    buf = BytesIO()
                    relacao.to_excel(buf, index=False)
                    obra_limpa = "".join(c for c in st.session_state["obra"] if c.isalnum() or c in (" ", "-", "_")).strip()
                    st.success(f"✅ Relação consolidada gerada com sucesso para {st.session_state['obra']}")
                    st.download_button(
                        label="📥 Baixar planilha gerada",
                        data=buf.getvalue(),
                        file_name=f"Ceminas - Materiais - {obra_limpa}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
            except Exception as e:
                st.error(f"❌ Erro ao gerar relação: {e}")
