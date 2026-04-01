from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import dashboard_analise_umidade as base


BASE_DIR = Path(__file__).resolve().parents[1]
APP_DATA_DIR = BASE_DIR / "app_data"
MASTER_PATH = APP_DATA_DIR / "df_master.csv"
RESUMO_PATH = APP_DATA_DIR / "resumo_dia.csv"
MASTER_FALLBACK_PATH = BASE_DIR / "logs" / "analise_umidade" / "df_master.csv"
RESUMO_FALLBACK_PATH = BASE_DIR / "logs" / "analise_umidade" / "resumo_dia.csv"

MODOS_GRAFICO = ["Moagem A", "Moagem B", "Ambas"]
MAPA_TEMPERATURAS = [
    ("temperatura_saida_3", "Secador 3"),
    ("temperatura_saida_1", "Secador 1"),
]
PARAMETROS_MEDIA_LABELS = {
    "temperatura_saida_3": "Temp. S3",
    "temperatura_saida_1": "Temp. S1",
    "pressao_vapor_3": "Vapor 3",
    "pressao_vapor_1": "Vapor 1",
    "vazao_hsw": "Vazao HSW",
}
PARAMETROS_MEDIA_ORDEM = [
    "temperatura_saida_3",
    "pressao_vapor_3",
    "vazao_hsw",
]
PARAMETROS_MEDIA_ORDEM_AMBAS = [
    "temperatura_saida_3",
    "temperatura_saida_1",
    "pressao_vapor_3",
    "pressao_vapor_1",
    "vazao_hsw",
]


st.set_page_config(
    page_title=" Umidade e Parametros de Secagem Farelo ",
    page_icon="U",
    layout="wide",
)


def construir_hover_secador(row: pd.Series) -> str:
    status_umidade = "Dentro da faixa" if row["status_umidade"] == "bom" else "Fora da faixa"
    return (
        f"<b>{row['data_hora']:%d/%m/%Y %H:%M}</b><br>"
        f"<span style='color:#DADFE8'><b>Modo de moagem:</b></span> {formatar_texto(row['modo_moagem'])}<br>"
        f"<span style='color:#DADFE8'><b>Secador:</b></span> {row['secador']}<br>"
        f"<span style='color:#DADFE8'><b>Status da umidade:</b></span> {status_umidade}<br>"
        f"<span style='color:#6EC1FF'><b>Umidade final:</b></span> {formatar_numero(row['umidade_final_farelo'])}%<br>"
        f"<span style='color:#FFD166'><b>Temperatura observada:</b></span> {formatar_numero(row['temperatura'])} C<br>"
        f"<span style='color:#DADFE8'><b>Contexto:</b></span> {formatar_texto(row['contexto_secagem'])}<br>"
        "<extra></extra>"
    )


def construir_base_scatter_secadores(df_base: pd.DataFrame, modo: str) -> pd.DataFrame:
    df_modo = df_base[df_base["modo_moagem"] == modo].copy()
    if df_modo.empty:
        return pd.DataFrame()

    partes = []
    for coluna_temp, secador in MAPA_TEMPERATURAS:
        colunas = [
            "data_hora",
            "modo_moagem",
            "contexto_secagem",
            "status_umidade",
            "umidade_final_farelo",
            coluna_temp,
        ]
        parte = df_modo[colunas].copy()
        parte = parte[parte[coluna_temp].notna()].copy()
        if parte.empty:
            continue

        parte = parte.rename(columns={coluna_temp: "temperatura"})
        parte["secador"] = secador
        partes.append(parte)

    if not partes:
        return pd.DataFrame()

    df_plot = pd.concat(partes, ignore_index=True)
    df_plot = df_plot.sort_values(["data_hora", "secador"]).copy()
    df_plot["hover_secador"] = df_plot.apply(construir_hover_secador, axis=1)
    return df_plot


def montar_figura_scatter_secadores(
    df_base: pd.DataFrame,
    modo: str,
    secador_sel: str,
) -> go.Figure | None:
    df_plot = construir_base_scatter_secadores(df_base, modo)
    if df_plot.empty:
        return None

    if secador_sel != "Secadores 1 e 3":
        df_plot = df_plot[df_plot["secador"] == secador_sel].copy()
        if df_plot.empty:
            return None

    fig = px.scatter(
        df_plot,
        x="temperatura",
        y="umidade_final_farelo",
        color="status_umidade",
        symbol="secador",
        color_discrete_map=COR_STATUS,
        category_orders={
            "status_umidade": ["bom", "ruim"],
            "secador": ["Secador 3", "Secador 1"],
        },
        custom_data=["hover_secador"],
    )
    fig.add_hline(y=9, line_dash="dash", line_color="#D97706")
    fig.add_hline(y=12, line_dash="dash", line_color="#D97706")
    fig.update_traces(
        marker=dict(size=11, line=dict(width=1, color="#F8F9FA")),
        hovertemplate="%{customdata[0]}",
    )
    fig.update_layout(
        height=390,
        xaxis_title="Temperatura de saida do secador",
        yaxis_title="Umidade final",
        plot_bgcolor="#171A21",
        paper_bgcolor="#171A21",
        font=dict(color="#F5F7FA"),
        margin=dict(l=10, r=10, t=18, b=12),
        hoverlabel=dict(bgcolor="#1F2430", font_size=12, font_color="#F8F9FA"),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            title_text="",
            font=dict(size=11),
        ),
    )
    fig.for_each_trace(
        lambda trace: trace.update(
            name=trace.name.replace("status_umidade=", "").replace("secador=", "")
        )
    )
    return fig


def construir_hover_media_parametro(row: pd.Series) -> str:
    return (
        f"<b>{row['modo_moagem']}</b><br>"
        f"<span style='color:#DADFE8'><b>Status da umidade:</b></span> {row['status_label']}<br>"
        f"<span style='color:#DADFE8'><b>Parametro avaliado:</b></span> {row['parametro_label']}<br>"
        f"<span style='color:#DADFE8'><b>Media observada:</b></span> {row['media_formatada']}<br>"
        f"<span style='color:#DADFE8'><b>Analises consideradas:</b></span> {row['qtd_analises']}<br>"
        "<extra></extra>"
    )


def construir_base_medias_parametros(df_base: pd.DataFrame, modo: str) -> pd.DataFrame:
    df_modo = df_base[df_base["modo_moagem"] == modo].copy()
    if df_modo.empty:
        return pd.DataFrame()

    parametros = (
        PARAMETROS_MEDIA_ORDEM_AMBAS if modo == "Ambas" else PARAMETROS_MEDIA_ORDEM
    )
    tabela = (
        df_modo.groupby("status_umidade")[parametros]
        .mean(numeric_only=True)
        .reset_index()
    )
    contagens = (
        df_modo.groupby("status_umidade")
        .size()
        .reset_index(name="qtd_analises")
    )
    if tabela.empty:
        return pd.DataFrame()

    df_plot = tabela.melt(
        id_vars="status_umidade",
        value_vars=parametros,
        var_name="parametro",
        value_name="media",
    )
    df_plot = df_plot.merge(contagens, on="status_umidade", how="left")
    df_plot = df_plot[df_plot["media"].notna()].copy()
    if df_plot.empty:
        return pd.DataFrame()

    df_plot["modo_moagem"] = modo
    df_plot["parametro_label"] = df_plot["parametro"].map(PARAMETROS_MEDIA_LABELS)
    df_plot["status_label"] = df_plot["status_umidade"].map(
        {"bom": "Dentro da faixa (9 a 12)", "ruim": "Fora da faixa"}
    )
    df_plot["media_formatada"] = df_plot["media"].map(
        lambda x: f"{x:.2f}".replace(".", ",")
    )
    df_plot["hover_media"] = df_plot.apply(construir_hover_media_parametro, axis=1)
    return df_plot


def montar_figura_medias_parametros(df_base: pd.DataFrame, modo: str) -> go.Figure | None:
    df_plot = construir_base_medias_parametros(df_base, modo)
    if df_plot.empty:
        return None

    ordem_parametros = (
        PARAMETROS_MEDIA_ORDEM_AMBAS if modo == "Ambas" else PARAMETROS_MEDIA_ORDEM
    )
    fig = px.bar(
        df_plot,
        x="parametro_label",
        y="media",
        color="status_umidade",
        barmode="group",
        color_discrete_map=COR_STATUS,
        text="media_formatada",
        custom_data=["hover_media"],
        category_orders={
            "parametro_label": [PARAMETROS_MEDIA_LABELS[col] for col in ordem_parametros]
        },
    )
    fig.update_traces(
        hovertemplate="%{customdata[0]}",
        texttemplate="%{text}",
        textposition="outside",
        cliponaxis=False,
        marker_line_color="#F8F9FA",
        marker_line_width=1.1,
    )
    fig.update_layout(
        height=430,
        xaxis_title="Parametros",
        yaxis_title="Media do parametro",
        plot_bgcolor="#171A21",
        paper_bgcolor="#171A21",
        font=dict(color="#F5F7FA"),
        margin=dict(l=6, r=6, t=18, b=78),
        xaxis=dict(tickangle=0, tickfont=dict(size=11), automargin=True),
        yaxis=dict(gridcolor="#2A3140", tickfont=dict(size=11), automargin=True),
        hoverlabel=dict(bgcolor="#1F2430", font_size=12, font_color="#F8F9FA"),
        bargap=0.42,
        bargroupgap=0.18,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.03,
            xanchor="left",
            x=0,
            title_text="",
            font=dict(size=11),
        ),
    )
    return fig


def montar_resumo_operacional_modo(df_base: pd.DataFrame, modo: str) -> str:
    df_modo = df_base[df_base["modo_moagem"] == modo].copy()
    if df_modo.empty:
        return "Nao ha registros suficientes para resumir esta moagem."

    df_bom = df_modo[df_modo["status_umidade"] == "bom"].copy()
    df_ruim = df_modo[df_modo["status_umidade"] == "ruim"].copy()

    def resumo_status(df_status: pd.DataFrame, label: str) -> str:
        if df_status.empty:
            return f"Na faixa de umidade {label}, nao houve analises para esta moagem."

        media_umidade = formatar_numero(df_status["umidade_final_farelo"].mean(), 2)
        media_temp3 = formatar_numero(df_status["temperatura_saida_3"].mean(), 2)
        media_hsw = formatar_numero(df_status["vazao_hsw"].mean(), 2)
        media_pressao3 = formatar_numero(df_status["pressao_vapor_3"].mean(), 2)

        if modo == "Ambas":
            media_temp1 = formatar_numero(df_status["temperatura_saida_1"].mean(), 2)
            media_pressao1 = formatar_numero(df_status["pressao_vapor_1"].mean(), 2)
            return (
                f"Na faixa de umidade {label}, a operacao teve media de umidade em **{media_umidade}**, "
                f"com **Secador 3** em **{media_temp3} C**, **Secador 1** em **{media_temp1} C**, "
                f"**Vapor 3** em **{media_pressao3}**, **Vapor 1** em **{media_pressao1}** "
                f"e **Vazao HSW** em **{media_hsw}**."
            )

        return (
            f"Na faixa de umidade {label}, a operacao teve media de umidade em **{media_umidade}**, "
            f"com foco no **Secador 3** em **{media_temp3} C**, "
            f"**Vapor 3** em **{media_pressao3}** e **Vazao HSW** em **{media_hsw}**."
        )

    return "\n\n".join(
        [
            resumo_status(df_bom, "boa (9 a 12)"),
            resumo_status(df_ruim, "ruim (fora da faixa)"),
        ]
    )


def renderizar_secao_temperatura_umidade_por_moagem(df_filtrado: pd.DataFrame) -> None:
    st.subheader("Temperatura de saida dos Secadores 1 e 3 x Umidade final")
    st.markdown(
        "Rascunho da alteracao: os graficos abaixo foram separados por modo de moagem "
        "e usam apenas os horarios reais registrados em cada analise."
    )
    st.markdown(
        """
        <style>
        .bloco-moagem {
            background: #171A21;
            border: 1px solid #232834;
            border-radius: 16px;
            padding: 14px 14px 10px 14px;
            min-height: 100%;
            margin-bottom: 8px;
        }
        .bloco-moagem h4 {
            margin: 0 0 8px 0;
            font-size: 1rem;
            color: #F5F7FA;
        }
        .bloco-moagem p {
            margin: 0;
            color: #C7CDD6;
            font-size: 0.88rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    colunas = st.columns(3)
    for coluna, modo in zip(colunas, MODOS_GRAFICO):
        df_modo = df_filtrado[df_filtrado["modo_moagem"] == modo].copy()
        with coluna:
            st.markdown(
                (
                    f"<div class='bloco-moagem'>"
                    f"<h4>{modo}</h4>"
                    f"<p>Secadores 1 e 3 x umidade final, usando somente os registros reais.</p>"
                    f"</div>"
                ),
                unsafe_allow_html=True,
            )
            if df_modo.empty:
                st.info(f"Nao ha registros para {modo} com os filtros atuais.")
                continue

            opcoes_secador = (
                ["Secadores 1 e 3", "Secador 3", "Secador 1"]
                if modo == "Ambas"
                else ["Secador 3", "Secador 1"]
            )
            secador_sel = st.radio(
                "Selecionar visualizacao",
                options=opcoes_secador,
                horizontal=True,
                key=f"secador_visual_{modo}",
                label_visibility="collapsed",
            )

            st.caption(f"{len(df_modo)} analises reais encontradas para {modo}.")
            with st.expander(f"Ver resumo operacional de {modo}", expanded=False):
                st.markdown(
                    f"**Quantidade de analises consideradas:** {len(df_modo)}  \n"
                    f"**Periodo observado:** {df_modo['data_hora'].min():%d/%m/%Y %H:%M} ate {df_modo['data_hora'].max():%d/%m/%Y %H:%M}"
                )
                st.markdown(montar_resumo_operacional_modo(df_filtrado, modo))

            figura = montar_figura_scatter_secadores(df_filtrado, modo, secador_sel)
            if figura is None:
                st.info(
                    f"Nao ha temperaturas validas para montar o grafico de {modo} em {secador_sel}."
                )
                continue

            st.plotly_chart(
                figura,
                use_container_width=True,
                config={"displayModeBar": False, "responsive": True},
            )


def renderizar_secao_medias_parametros_por_moagem(df_filtrado: pd.DataFrame) -> None:
    st.subheader("Medias de parametros identificadas por faixa de umidade")
    st.markdown(
        "Comparativo das medias dos parametros em cada moagem, separando os cenarios "
        "em que a umidade ficou dentro da faixa de 9 a 12 e quando ficou fora dela."
    )

    colunas = st.columns(3)
    for coluna, modo in zip(colunas, MODOS_GRAFICO):
        df_modo = df_filtrado[df_filtrado["modo_moagem"] == modo].copy()
        with coluna:
            st.markdown(
                (
                    f"<div class='bloco-moagem'>"
                    f"<h4>{modo}</h4>"
                    f"<p>Medias observadas para identificar parametros mais estaveis na faixa de umidade.</p>"
                    f"</div>"
                ),
                unsafe_allow_html=True,
            )
            if df_modo.empty:
                st.info(f"Nao ha registros para {modo} com os filtros atuais.")
                continue

            qtd_bom = int((df_modo["status_umidade"] == "bom").sum())
            qtd_ruim = int((df_modo["status_umidade"] == "ruim").sum())
            st.caption(
                f"Base real: {len(df_modo)} analises | faixa 9-12: {qtd_bom} | fora da faixa: {qtd_ruim}"
            )
            with st.expander(f"Ver composicao da media em {modo}", expanded=False):
                st.markdown(
                    f"**Analises dentro da faixa (9 a 12):** {qtd_bom}  \n"
                    f"**Analises fora da faixa:** {qtd_ruim}"
                )

            figura = montar_figura_medias_parametros(df_filtrado, modo)
            if figura is None:
                st.info(f"Nao ha parametros suficientes para montar o grafico de {modo}.")
                continue

            st.plotly_chart(
                figura,
                use_container_width=True,
                config={"displayModeBar": False, "responsive": True},
            )


def renderizar_secao_detalhe_dia(
    df_filtrado: pd.DataFrame,
) -> None:
    st.subheader("Detalhamento por dia")

    datas_disponiveis = sorted(df_filtrado["data_ref"].dt.date.unique().tolist())
    data_escolhida = st.selectbox(
        "Dia para detalhar",
        options=datas_disponiveis,
        index=(len(datas_disponiveis) - 1 if datas_disponiveis else 0),
        format_func=lambda d: pd.to_datetime(d).strftime("%d/%m/%Y"),
        key="data_detalhe_dashboard",
    )
    dia_plot = (
        df_filtrado[df_filtrado["data_ref"].dt.date == data_escolhida]
        .sort_values("data_hora")
        .copy()
    )
    dia_plot["hover_detalhado"] = dia_plot.apply(construir_hover_detalhado, axis=1)
    resumo_dia_sel = resumir_dia(dia_plot)

    with st.expander("Ver detalhe do dia selecionado", expanded=False):
        d1, d2, d3, d4 = st.columns(4)
        d1.metric("Medicoes do dia", resumo_dia_sel["total"])
        d2.metric("Medicoes boas", resumo_dia_sel["qtd_bom"])
        d3.metric("Medicoes ruins", resumo_dia_sel["qtd_ruim"])
        d4.metric("% dentro da faixa", resumo_dia_sel["pct_bom"])

        dia_bom = dia_plot[dia_plot["status_umidade"] == "bom"].copy()
        dia_ruim = dia_plot[dia_plot["status_umidade"] == "ruim"].copy()
        st.subheader("Resumo operacional do dia")
        st.markdown(montar_resumo_operacional_dia(dia_bom, "bom"))
        st.divider()
        st.markdown(montar_resumo_operacional_dia(dia_ruim, "ruim"))

        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Umidade por horario")
            st.plotly_chart(
                montar_figura_umidade_barras(dia_plot),
                use_container_width=True,
            )
        with c2:
            st.subheader("Temperaturas e vapor no tempo")
            st.plotly_chart(
                montar_figura_temperaturas_vapor(dia_plot),
                use_container_width=True,
            )

        st.subheader("Vazao de agua pesada por horario")
        st.plotly_chart(montar_figura_hsw(dia_plot), use_container_width=True)

        st.subheader("Analises boas do dia")
        tabela_bom = montar_tabela_status_dia(
            dia_plot[dia_plot["status_umidade"] == "bom"].copy()
        )
        if tabela_bom.empty:
            st.info("Nao houve analise boa neste dia.")
        else:
            st.dataframe(tabela_bom, use_container_width=True, hide_index=True)

        st.subheader("Analises ruins do dia")
        tabela_ruim = montar_tabela_status_dia(
            dia_plot[dia_plot["status_umidade"] == "ruim"].copy()
        )
        if tabela_ruim.empty:
            st.info("Nao houve analise ruim neste dia.")
        else:
            st.dataframe(tabela_ruim, use_container_width=True, hide_index=True)


def main() -> None:
    st.markdown(
        """
        <style>
        .stApp { background-color: #0F1117; color: #F5F7FA; }
        div[data-testid="stMetric"] {
            background: #171A21;
            border: 1px solid #232834;
            padding: 12px 16px;
            border-radius: 14px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    df_master, resumo_dia = carregar_dados()
    df_master = df_master.sort_values("data_hora").copy()
    df_master["contexto_secagem"] = df_master.apply(
        classificar_contexto_secagem, axis=1
    )
    modo_series = df_master["modo_moagem"].fillna("").astype(str)
    df_master["casca_umida_agora"] = modo_series.str.contains("casca", case=False)
    df_master["casca_umida_1h_ou_2h_antes"] = df_master["casca_umida_agora"].shift(
        1, fill_value=False
    ) | df_master["casca_umida_agora"].shift(2, fill_value=False)

    st.title("Analise de Umidade do Farelo e Parametros de Secagem")
    st.caption("Arquivo de rascunho para consolidacao antes de alterar o dashboard principal.")

    with st.sidebar:
        st.header("Filtros")
        intervalo = st.date_input(
            "Periodo",
            value=(
                df_master["data_ref"].min().date(),
                df_master["data_ref"].max().date(),
            ),
            min_value=df_master["data_ref"].min().date(),
            max_value=df_master["data_ref"].max().date(),
        )
        status_sel = st.multiselect(
            "Status da umidade",
            options=sorted(df_master["status_umidade"].dropna().unique().tolist()),
            default=sorted(df_master["status_umidade"].dropna().unique().tolist()),
        )
        modo_opcoes = sorted(
            x for x in df_master["modo_moagem"].dropna().unique().tolist() if x
        )
        modo_sel = st.multiselect(
            "Modo de moagem", options=modo_opcoes, default=modo_opcoes
        )
        contexto_opcoes = sorted(
            x for x in df_master["contexto_secagem"].dropna().unique().tolist() if x
        )
        contexto_sel = st.multiselect(
            "Contexto de secagem", options=contexto_opcoes, default=contexto_opcoes
        )

    data_ini = pd.to_datetime(intervalo[0])
    data_fim = pd.to_datetime(intervalo[1])
    df_filtrado = df_master[
        (df_master["data_ref"] >= data_ini)
        & (df_master["data_ref"] <= data_fim)
        & (df_master["status_umidade"].isin(status_sel))
    ].copy()

    if modo_sel:
        df_filtrado = df_filtrado[df_filtrado["modo_moagem"].isin(modo_sel)]
    if contexto_sel:
        df_filtrado = df_filtrado[df_filtrado["contexto_secagem"].isin(contexto_sel)]

    resumo_filtrado = resumo_dia[
        (resumo_dia["data_ref"] >= data_ini) & (resumo_dia["data_ref"] <= data_fim)
    ].copy()
    datas_validas = df_filtrado["data_ref"].dt.normalize().unique()
    resumo_filtrado = resumo_filtrado[resumo_filtrado["data_ref"].isin(datas_validas)]

    if df_filtrado.empty:
        st.warning("Nenhum registro encontrado com os filtros atuais.")
        st.stop()

    total = len(df_filtrado)
    qtd_bom = int((df_filtrado["status_umidade"] == "bom").sum())
    qtd_ruim = int((df_filtrado["status_umidade"] == "ruim").sum())
    media_umidade = round(df_filtrado["umidade_final_farelo"].mean(), 2) if total else 0.0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Medicoes no filtro", total)
    col2.metric("Medicoes boas", qtd_bom)
    col3.metric("Medicoes ruins", qtd_ruim)
    col4.metric("Media da umidade", media_umidade)

    st.subheader("O que estava rodando nas umidades boas vs. ruins")
    comp_esq, comp_dir = st.columns(2)
    with comp_esq:
        st.markdown("**Quando a umidade estava boa (9 a 12)**")
        st.dataframe(
            montar_tabela_contexto(df_filtrado, "bom"),
            use_container_width=True,
            hide_index=True,
        )
    with comp_dir:
        st.markdown("**Quando a umidade estava ruim (abaixo de 9)**")
        st.dataframe(
            montar_tabela_contexto(df_filtrado, "ruim"),
            use_container_width=True,
            hide_index=True,
        )

    st.markdown(
        "Os valores acima sao o contexto operacional observado em cada grupo de umidade. "
        "Variacoes entre modos de moagem sao esperadas; uma moagem e duas moagens operam em regimes diferentes."
    )

    renderizar_secao_temperatura_umidade_por_moagem(df_filtrado)
    renderizar_secao_medias_parametros_por_moagem(df_filtrado)
    renderizar_secao_detalhe_dia(df_filtrado)

    with st.expander("Faixas operacionais observadas nos horarios de umidade boa", expanded=False):
        st.caption(
            "Nao sao metas; sao os valores que estavam presentes quando a umidade ficou dentro da especificacao."
        )
        st.dataframe(
            montar_faixas_bons_por_modo(df_filtrado),
            use_container_width=True,
            hide_index=True,
        )

    st.subheader("Contexto observado por modo de moagem")
    contexto_hsw = (
        df_filtrado.groupby(["status_umidade", "contexto_secagem", "modo_moagem"])
        .agg(
            medicoes=("umidade_final_farelo", "count"),
            mediana_umidade=("umidade_final_farelo", "median"),
            mediana_vazao_hsw=("vazao_hsw", "median"),
            mediana_temp3=("temperatura_saida_3", "median"),
            mediana_temp1=("temperatura_saida_1", "median"),
            mediana_pressao3=("pressao_vapor_3", "median"),
            mediana_pressao1=("pressao_vapor_1", "median"),
        )
        .reset_index()
    )
    contexto_hsw = contexto_hsw[contexto_hsw["modo_moagem"].fillna("") != ""]
    contexto_hsw["hover_contexto"] = contexto_hsw.apply(
        construir_hover_contexto,
        axis=1,
    )
    fig_bar = px.bar(
        contexto_hsw,
        x="modo_moagem",
        y="mediana_vazao_hsw",
        color="status_umidade",
        barmode="group",
        text="medicoes",
        custom_data=["hover_contexto"],
        labels={
            "modo_moagem": "Modo de moagem observado",
            "mediana_vazao_hsw": "Mediana da vazao de HSW",
            "status_umidade": "Status da umidade",
        },
        color_discrete_map=COR_STATUS,
    )
    fig_bar.update_traces(textposition="outside", hovertemplate="%{customdata[0]}")
    fig_bar.update_layout(
        height=420,
        yaxis_title="Mediana da vazao de HSW",
        xaxis_title="",
        legend_title_text="Status da umidade",
        plot_bgcolor="#171A21",
        paper_bgcolor="#171A21",
        font=dict(color="#F5F7FA"),
        margin=dict(l=20, r=20, t=40, b=20),
        hoverlabel=dict(bgcolor="#1F2430", font_size=12, font_color="#F8F9FA"),
    )
    st.plotly_chart(fig_bar, use_container_width=True)

    with st.expander("Dias em destaque", expanded=False):
        col_bons, col_ruins = st.columns(2)
        top_bons = montar_top_dias_descritivo(
            resumo_filtrado,
            df_filtrado,
            "bom",
            top_n=10,
        )
        top_ruins = montar_top_dias_descritivo(
            resumo_filtrado,
            df_filtrado,
            "ruim",
            top_n=10,
        )
        with col_bons:
            st.markdown("**Top 10 dias bons**")
            st.dataframe(top_bons, use_container_width=True, hide_index=True)
        with col_ruins:
            st.markdown("**Top 10 dias ruins**")
            st.dataframe(top_ruins, use_container_width=True, hide_index=True)

    with st.expander("Casos ruins com observacao operacional", expanded=False):
        casos_ruins = df_filtrado[df_filtrado["status_umidade"] == "ruim"].copy()
        casos_ruins["Fato"] = casos_ruins["Fato"].apply(formatar_texto)
        casos_ruins["Causa"] = casos_ruins["Causa"].apply(formatar_texto)
        casos_ruins["Acao"] = casos_ruins["Acao"].apply(formatar_texto)
        st.dataframe(
            casos_ruins[
                [
                    "data_hora",
                    "umidade_final_farelo",
                    "modo_moagem",
                    "contexto_secagem",
                    "temperatura_saida_3",
                    "temperatura_saida_1",
                    "pressao_vapor_3",
                    "pressao_vapor_1",
                    "vazao_hsw",
                    "vazao_retorno_3",
                    "casca_umida_1h_ou_2h_antes",
                    "Fato",
                    "Causa",
                    "Acao",
                ]
            ].sort_values("data_hora"),
            use_container_width=True,
            hide_index=True,
        )


if __name__ == "__main__":
    main()

