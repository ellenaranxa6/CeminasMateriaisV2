# =========================================================
# CEMINAS - GERADOR DE RELAÇÃO DE MATERIAIS (v2.0)
# Interface Web Interativa (Streamlit Cloud)
# ---------------------------------------------------------
# Autor: Ellen Lousada / Engenharia Ceminas
# Versão: 2025.11 (Entrada Manual + Upload)
# =========================================================

import streamlit as st
import pandas as pd
import os
from io import BytesIO

# ---------------------------------------------------------
# ⚙️ CONFIGURAÇÃO DE PÁGINA
# ---------------------------------------------------------
st.set_page_config(page_title="Ceminas - Lista de Materiais", page_icon="⚡", layout="centered")

# ---------------------------------------------------------
# ESTILO VISUAL
# ---------------------------------------------------------
st.markdown("""
    <style>
        .main { background-color: #E6F0FF; }
        .title { text-align: center; font-size: 36px; font-weight: 800; color: #003366; margin-top: 10px; }
        .subtitle { text-align: center; font-size: 18px; color: #333; margin-bottom: 30px; }
        .stButton>button {
            background-color: #003366;
            color: #fff;
            font-weight: 700;
            border-radius: 8px;
            padding: .6em 1.2em;
            transition: 0.3s;
        }
        .stButton>button:hover { background-color: #0059b3; color: #fff; }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# LOGOTIPO E CABEÇALHO
# ---------------------------------------------------------
logo_path = "Logo Ceminas.jpeg"
if os.path.exists(logo_path):
    st.image(logo_path, use_column_width=False, width=250)
st.markdown('<div class="title">CEMINAS – Gerador de Relação de Materiais</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Ferramenta interna para consolidação de materiais de redes de distribuição</div>', unsafe_allow_html=True)
st.divider()

# ---------------------------------------------------------
# AUTENTICAÇÃO
# ---------------------------------------------------------
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

# ---------------------------------------------------------
# ESTADOS GLOBAIS
# ---------------------------------------------------------
st.session_state.setdefault("obra", "Nova Obra")
st.session_state.setdefault("manual_df", pd.DataFrame(columns=["ESTRUTURA", "EQUIPAMENTO", "CONDUTOR", "POSTE", "QUANTIDADE"]))

# ---------------------------------------------------------
# MODO DE ENTRADA
# ---------------------------------------------------------
st.header("📦 Escolha o modo de entrada dos dados do projeto")
modo_entrada = st.radio(
    "Selecione o modo de entrada:",
    ("📥 Enviar planilha de estruturas (.xlsx)", "🧱 Inserir manualmente as estruturas"),
    horizontal=True
)

banco_estruturas = "MateriaisEstrutura.xlsx"

# ---------------------------------------------------------
# 🔹 MODO 1 - UPLOAD (Fluxo existente)
# ---------------------------------------------------------
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

        gerar = st.button("⚙️ Gerar Relação de Materiais (Planilha)")

        if gerar:
            try:
                estruturas = pd.read_excel(banco_estruturas, engine="openpyxl")
                projeto = pd.read_excel(projeto_path, engine="openpyxl")

                for df in [estruturas, projeto]:
                    df.columns = df.columns.str.strip().str.upper()
                    for col in df.select_dtypes(include=["object"]).columns:
                        df[col] = df[col].astype(str).str.strip().str.upper()

                materiais_lista = []
                for _, row in projeto.iterrows():
                    flt = (
                        (estruturas["ESTRUTURA"] == row["ESTRUTURA"]) &
                        (estruturas["EQUIPAMENTO"] == row["EQUIPAMENTO"]) &
                        (estruturas["CONDUTOR"] == row["CONDUTOR"]) &
                        (estruturas["POSTE"] == row["POSTE"])
                    )
                    encontrados = estruturas.loc[flt].copy()
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
                    st.warning("⚠️ Nenhuma estrutura válida encontrada.")
            except Exception as e:
                st.error(f"❌ Erro: {e}")

# ---------------------------------------------------------
# 🔹 MODO 2 - INSERÇÃO MANUAL
# ---------------------------------------------------------
else:
    st.header("🧱 Inserção Manual de Estruturas")
    st.info("Preencha as estruturas do projeto diretamente na plataforma. Apenas combinações existentes no banco são permitidas.")

    try:
        banco = pd.read_excel(banco_estruturas, engine="openpyxl")
        banco.columns = banco.columns.str.strip().str.upper()
        for col in ["ESTRUTURA", "EQUIPAMENTO", "CONDUTOR", "POSTE"]:
            banco[col] = banco[col].fillna("").astype(str).str.strip().str.upper()
    except Exception as e:
        st.error(f"❌ Erro ao carregar banco: {e}")
        st.stop()

    with st.form("inserir_estrutura"):
        estrutura = st.selectbox("Estrutura:", sorted(banco["ESTRUTURA"].unique()))
        eq_opts = sorted(banco[banco["ESTRUTURA"] == estrutura]["EQUIPAMENTO"].unique())
        equipamento = st.selectbox("Equipamento:", eq_opts)

        cond_opts = sorted(banco[(banco["ESTRUTURA"] == estrutura) &
                                 (banco["EQUIPAMENTO"] == equipamento)]["CONDUTOR"].unique())
        condutor = st.selectbox("Condutor:", cond_opts)

        poste_opts = sorted(banco[(banco["ESTRUTURA"] == estrutura) &
                                  (banco["EQUIPAMENTO"] == equipamento) &
                                  (banco["CONDUTOR"] == condutor)]["POSTE"].unique())
        poste = st.selectbox("Poste:", poste_opts)

        quantidade = st.number_input("Quantidade:", min_value=1, value=1, step=1)
        adicionar = st.form_submit_button("➕ Adicionar Estrutura")

    if adicionar:
        nova_linha = pd.DataFrame([{
            "ESTRUTURA": estrutura,
            "EQUIPAMENTO": equipamento,
            "CONDUTOR": condutor,
            "POSTE": poste,
            "QUANTIDADE": quantidade
        }])
        st.session_state["manual_df"] = pd.concat([st.session_state["manual_df"], nova_linha], ignore_index=True)
        st.success(f"✅ Estrutura {estrutura} adicionada com sucesso!")

    if not st.session_state["manual_df"].empty:
        st.subheader("📋 Estruturas Inseridas")
        st.dataframe(st.session_state["manual_df"], use_container_width=True)

        if st.button("🗑️ Limpar Lista"):
            st.session_state["manual_df"] = pd.DataFrame(columns=["ESTRUTURA", "EQUIPAMENTO", "CONDUTOR", "POSTE", "QUANTIDADE"])
            st.rerun()

        st.divider()
        gerar_manual = st.button("⚙️ Gerar Relação de Materiais (Manual)")

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
                st.warning("⚠️ Nenhuma estrutura válida encontrada.")
