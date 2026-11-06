"""Painel Streamlit: dados (silver), modelo, simulador e previsões salvas (gold)."""
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st
from sklearn.metrics import accuracy_score, confusion_matrix

from src.extract import Extract
from src.load import Load
from src.model import Classificador, Features

st.set_page_config(page_title="Vacinação Recife", layout="wide")
st.title("Vacinação COVID-19 em Recife")

# colunas do perfil gravado na gold (mesmo formato do prever.py)
COLUNAS_PERFIL = ["perfil_id", "idade", "dose", "data_vacinacao", "sexo", "raca_cor",
                  "distrito_sanitario", "unidade_saude", "sistema_origem", "grupo",
                  "categoria", "faixa_etaria", "municipio"]


@st.cache_data(ttl=600)
def carregar_silver():
    return Extract().ler_silver()


@st.cache_resource
def carregar_modelo():
    return Classificador().carregar_final(Classificador.carregar())


@st.cache_data
def avaliar_teste(df):
    """Reproduz a divisão 80/20 do train.py e prevê no conjunto de teste."""
    ref = Classificador()
    X, y = ref.preparar(df)
    ref.dividir(X, y)
    return ref.y_treino, ref.y_teste, ref.X_teste_full


df = carregar_silver()
classificador = carregar_modelo()

aba_dados, aba_modelo, aba_simulador, aba_gold = st.tabs(
    ["Os dados", "O modelo", "Simulador", "Previsões salvas"]
)

# ---------------------------------------------------------------- Os dados
with aba_dados:
    c1, c2, c3 = st.columns(3)
    c1.metric("Registros na silver", len(df))
    c2.metric("Idade média", f"{df['idade'].mean():.0f} anos")
    c3.metric("Doses de reforço", f"{(df['dose'] >= 3).mean():.0%}")

    dados = df.copy()
    dados["mes_ano"] = pd.to_datetime(dados["data_vacinacao"]).dt.strftime("%Y-%m")
    por_mes = dados.groupby(["mes_ano", "vacina"]).size().reset_index(name="doses")
    st.plotly_chart(px.bar(por_mes, x="mes_ano", y="doses", color="vacina", title="Doses por mês"))
    st.plotly_chart(px.box(dados, x="vacina", y="idade", title="Idade de quem recebeu cada vacina"))

# --------------------------------------------------------------- O modelo
with aba_modelo:
    y_treino, y_teste, X_teste_full = avaliar_teste(df)
    X_teste = Features.selecionar(X_teste_full, classificador.grupos_final).reindex(
        columns=classificador.colunas_final, fill_value=0)
    previsto = classificador.modelo.predict(X_teste)
    mais_comum = y_treino.mode()[0]

    c1, c2 = st.columns(2)
    c1.metric("Acurácia no teste", f"{accuracy_score(y_teste, previsto):.1%}")
    c2.metric("Linha de base", f"{(y_teste == mais_comum).mean():.1%}")

    classes = [str(c) for c in classificador.modelo.classes_]
    matriz = confusion_matrix(y_teste, previsto, labels=classificador.modelo.classes_)
    st.plotly_chart(px.imshow(matriz, x=classes, y=classes, text_auto=True,
                              color_continuous_scale="Oranges",
                              labels={"x": "prevista", "y": "real"}, title="Matriz de confusão"))

    importancia = pd.Series(classificador.modelo.feature_importances_, index=classificador.colunas_final)
    top = importancia.nlargest(8).sort_values()
    st.plotly_chart(px.bar(top, orientation="h", title="Colunas mais importantes"))

# -------------------------------------------------------------- Simulador
with aba_simulador:
    def opcoes(coluna):
        return sorted(df[coluna].dropna().unique())

    with st.form("perfil"):
        c1, c2, c3 = st.columns(3)
        idade = c1.number_input("Idade", min_value=0, max_value=110, value=30)
        dose = c2.selectbox("Dose", sorted(df["dose"].dropna().astype(int).unique()))
        data = c3.date_input("Data da vacinação", value=pd.Timestamp("2022-03-01"))
        sexo = c1.selectbox("Sexo", opcoes("sexo"))
        raca = c2.selectbox("Raça/cor", opcoes("raca_cor"))
        distrito = c3.selectbox("Distrito sanitário", opcoes("distrito_sanitario"))
        with st.expander("Mais colunas usadas pelo modelo"):
            e1, e2, e3 = st.columns(3)
            unidade = e1.selectbox("Unidade de saúde", opcoes("unidade_saude"))
            sistema = e2.selectbox("Sistema de origem", opcoes("sistema_origem"))
            grupo = e3.selectbox("Grupo", opcoes("grupo"))
            categoria = e1.selectbox("Categoria", opcoes("categoria"))
            faixa = e2.selectbox("Faixa etária", opcoes("faixa_etaria"))
            municipio = e3.selectbox("Município", opcoes("municipio"))
        gravar = st.checkbox("Gravar a previsão na camada gold")
        enviar = st.form_submit_button("Prever")

    if enviar:
        perfil = pd.DataFrame([{
            "perfil_id": f"simulador-{datetime.now():%Y%m%d%H%M%S}",
            "idade": idade, "dose": int(dose), "data_vacinacao": str(data),
            "sexo": sexo, "raca_cor": raca, "distrito_sanitario": distrito,
            "unidade_saude": unidade, "sistema_origem": sistema, "grupo": grupo,
            "categoria": categoria, "faixa_etaria": faixa, "municipio": municipio,
        }])[COLUNAS_PERFIL]
        resultado = classificador.prever(perfil)
        st.success(f"Vacina prevista: {resultado['vacina_prevista'].iloc[0]} "
                   f"(confiança {resultado['confianca'].iloc[0]:.0%})")

        probs = classificador.probabilidades(perfil).iloc[0].sort_values()
        st.plotly_chart(px.bar(probs, orientation="h", title="Probabilidade de cada vacina"))

        if gravar:
            Load().salvar_gold_previsoes(pd.concat([perfil, resultado], axis=1))
            st.info("Previsão gravada na gold.")

# ---------------------------------------------------------- Previsões salvas
with aba_gold:
    try:
        gold = Extract().ler_gold()
    except Exception:
        st.info("Ainda não há previsões na gold. Use o simulador ou rode o prever.py.")
    else:
        st.metric("Previsões salvas", len(gold))
        st.plotly_chart(px.histogram(gold, x="vacina_prevista", title="Previsões por vacina"))
        st.dataframe(gold.sort_values("data_previsao", ascending=False))
