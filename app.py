import altair as alt
import pandas as pd
import streamlit as st

from src.data_loader import load_data

st.set_page_config(
    page_title="Avaliação de Correlação entre Variáveis Quantitativas do Online Shoppers Dataset",
    layout="wide",
)

st.title("Avaliação de Correlação entre Variáveis Quantitativas do Online Shoppers Dataset")

df = load_data()

# Variáveis quantitativas do estudo (mesma lista VARS_QUANT do notebook de EDA)
VARS_QUANT = [
    "paginas_administrativas", "tempo_administrativas_seg", "paginas_informativas", "tempo_informativas_seg",
    "paginas_produto", "tempo_produto_seg", "taxa_rejeicao", "taxa_saida", "valor_pagina",
]
# Subconjunto que já vem selecionado (mesma lista VARS_CORE do notebook)
VARS_CORE = ["paginas_produto", "tempo_produto_seg", "taxa_rejeicao", "taxa_saida", "valor_pagina"]

# Coluna alvo ("Não comprou" / "Comprou"), criada no notebook a partir de Revenue
CLASSE = "comprou"

# Sidebar: filtros (variáveis + intervalo)
with st.sidebar:
    st.header("Filtros")

    variaveis = st.multiselect(
        "Variáveis Quantitativas",
        options=VARS_QUANT,
        default=VARS_CORE,
        help="Selecione as variáveis quantitativas que deseja analisar no dashboard.",
    )

    separar_por_classe = st.toggle(
        "Distinguir por Classe",
        value=False,
        help="Colore a distribuição pela classe (comprou: Não comprou ou Comprou).",
    )

    # Um slider de intervalo para cada variável selecionada
    intervalos = {}
    for var in variaveis:
        if pd.api.types.is_integer_dtype(df[var]):
            minimo, maximo, passo = int(df[var].min()), int(df[var].max()), 1
        else:
            # Passo proporcional à escala: taxas vão de 0 a 0,2, durações chegam a dezenas de milhares de segundos
            minimo, maximo = float(df[var].min()), float(df[var].max())
            passo = float(f"{(maximo - minimo) / 200:.1g}")
        intervalos[var] = st.slider(
            f"Intervalo de {var}",
            min_value=minimo,
            max_value=maximo,
            value=(minimo, maximo),
            step=passo,
            key=f"intervalo_{var}",
        )

# Mantém só as sessões dentro de todos os intervalos escolhidos
df_filtrado = df
for var, (inicio, fim) in intervalos.items():
    df_filtrado = df_filtrado[df_filtrado[var].between(inicio, fim)]

st.caption(f"{len(df_filtrado)} de {len(df)} sessões dentro dos intervalos escolhidos.")

# Dashboard 1: correlação (heatmap) à esquerda, distribuição (histograma) à direita
col_correlacao, col_distribuicao = st.columns([1.3, 1.5])

# Cores do histograma, as mesmas do notebook de EDA: roxo para Comprou, rosa para Não comprou
COR_NAO_COMPROU = "#d8b4ad"
COR_COMPROU = "#2d223a"
COR_HISTOGRAMA = "#5b3f7a"
CORES_CLASSE = alt.Scale(domain=["Não comprou", "Comprou"], range=[COR_NAO_COMPROU, COR_COMPROU])

# Legenda das classes em texto, para caber no espaço livre da grade de histogramas
LEGENDA_CLASSE = (
    f"**Classe**  \n"
    f":color[■]{{foreground=\"{COR_NAO_COMPROU}\"}} Não comprou  \n"
    f":color[■]{{foreground=\"{COR_COMPROU}\"}} Comprou"
)

with col_correlacao:
    st.subheader("Correlação (Spearman)")

    if len(variaveis) < 2:
        st.warning("Selecione pelo menos 2 variáveis para calcular a correlação.")
    elif len(df_filtrado) < 30:
        st.warning("Poucas sessões nos intervalos escolhidos para calcular a correlação.")
    else:
        # Matriz de correlação de Spearman das variáveis selecionadas, em formato longo (uma linha por célula)
        corr = (
            df_filtrado[variaveis]
            .corr(method="spearman")
            .rename_axis(index="var_y", columns="var_x")
            .stack()
            .rename("correlacao")
            .reset_index()
        )
        # Só o triângulo inferior, sem a diagonal (sempre 1): a matriz é simétrica, o resto é repetição
        ordem = {var: i for i, var in enumerate(variaveis)}
        corr = corr[corr["var_y"].map(ordem) > corr["var_x"].map(ordem)]

        base = alt.Chart(corr).encode(
            x=alt.X(
                "var_x:N",
                title=None,
                sort=variaveis[:-1],  # a última variável só aparece nas linhas
                # Rótulos inclinados: nomes como tempo_produto_seg não cabem na horizontal
                axis=alt.Axis(labelAngle=-40, labelFontSize=12, labelLimit=220, labelOverlap=False),
            ),
            y=alt.Y(
                "var_y:N",
                title=None,
                sort=variaveis[1:],  # a primeira só nas colunas
                axis=alt.Axis(labelFontSize=12, labelLimit=220),
            ),
        )
        heatmap = base.mark_rect().encode(
            color=alt.Color(
                "correlacao:Q",
                title="Spearman",
                scale=alt.Scale(scheme="redblue", domain=[-1, 1], reverse=True),
                legend=alt.Legend(titleFontSize=14, labelFontSize=13),
            ),
            tooltip=["var_x", "var_y", alt.Tooltip("correlacao:Q", format=".2f")],
        )
        valores = base.mark_text(fontSize=13).encode(
            text=alt.Text("correlacao:Q", format=".2f"),
            color=alt.condition(
                "abs(datum.correlacao) > 0.5", alt.value("white"), alt.value("black")
            ),
        )

        st.altair_chart(
            (heatmap + valores).properties(height=380),
            width="stretch",
            alt="Mapa de calor (triângulo inferior, sem a diagonal) da correlação de Spearman entre as variáveis quantitativas selecionadas",
        )

with col_distribuicao:
    st.subheader("Distribuição")

    if not variaveis:
        st.warning("Selecione pelo menos 1 variável para ver a distribuição.")
    elif df_filtrado.empty:
        st.warning("Nenhuma sessão dentro dos intervalos escolhidos.")
    else:
        # Com número par de variáveis não sobra espaço na grade: a legenda vai acima dela
        if separar_por_classe and len(variaveis) % 2 == 0:
            st.markdown(LEGENDA_CLASSE)

        # Um histograma por variável selecionada, em grade de 2 colunas (cada um com a sua escala)
        for inicio in range(0, len(variaveis), 2):
            colunas = st.columns(2)
            for coluna, var in zip(colunas, variaveis[inicio : inicio + 2]):
                histograma = (
                    alt.Chart(df_filtrado[[var, CLASSE]])
                    .mark_bar()
                    .encode(
                        x=alt.X(f"{var}:Q", bin=alt.Bin(maxbins=20), title=var),
                        y=alt.Y("count()", title="Sessões"),
                        tooltip=[alt.Tooltip("count()", title="Sessões")],
                    )
                    .properties(height=200)
                )
                if separar_por_classe:
                    histograma = histograma.encode(
                        color=alt.Color(
                            f"{CLASSE}:N",
                            title="Classe",
                            scale=CORES_CLASSE,
                            legend=None,
                        ),
                        tooltip=[CLASSE, alt.Tooltip("count()", title="Sessões")],
                    )
                else:
                    histograma = histograma.mark_bar(color=COR_HISTOGRAMA)

                with coluna:
                    st.altair_chart(histograma, width="stretch", alt=f"Histograma da variável {var}")

            # Número ímpar de variáveis: a legenda ocupa o espaço que sobrou na última linha
            if separar_por_classe and len(colunas) == 2 and len(variaveis[inicio : inicio + 2]) == 1:
                colunas[1].markdown(LEGENDA_CLASSE)

# TODO: Dashboard 2 — KPIs (Aula 22)
