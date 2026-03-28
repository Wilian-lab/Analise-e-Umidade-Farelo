from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


BASE_DIR = Path(__file__).resolve().parents[1]
ARQUIVO_EXCEL = BASE_DIR / "data" / "Acompanhamento_indicadores.xlsx"
OUT_DIR = BASE_DIR / "logs" / "analise_umidade"
FIG_DIR = OUT_DIR / "figuras"


def preparar_base(df: pd.DataFrame, valor_col: str, novo_nome: str) -> pd.DataFrame:
    df = df.copy()
    df["Date"] = pd.to_datetime(df["Date"])
    df["hora_real"] = pd.to_timedelta(df["Unnamed: 12"].astype(str))
    df["data_hora"] = df["Date"] + df["hora_real"]
    df["data_ref"] = df["Date"].dt.date
    df["hora_ref"] = df["data_hora"].dt.time
    df = df.rename(columns={valor_col: novo_nome})
    return df


def salvar_grafico(fig, nome_arquivo: str) -> str:
    caminho = FIG_DIR / nome_arquivo
    fig.savefig(caminho, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return str(caminho)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    sns.set_theme(style="whitegrid")

    xl = pd.ExcelFile(ARQUIVO_EXCEL)

    df_umidade = preparar_base(pd.read_excel(ARQUIVO_EXCEL, sheet_name=1), "Valor_numero", "umidade_final_farelo")
    df_proteina = preparar_base(pd.read_excel(ARQUIVO_EXCEL, sheet_name=3), "Valor_numero", "proteina_casca_seca")
    df_hsw = preparar_base(pd.read_excel(ARQUIVO_EXCEL, sheet_name=4), "Valor_numero", "vazao_hsw")
    df_pressao1 = preparar_base(pd.read_excel(ARQUIVO_EXCEL, sheet_name=6), "Valor_numero", "pressao_vapor_1")
    df_pressao3 = preparar_base(pd.read_excel(ARQUIVO_EXCEL, sheet_name=7), "Valor_numero", "pressao_vapor_3")
    df_temp1 = preparar_base(pd.read_excel(ARQUIVO_EXCEL, sheet_name=8), "Valor_numero", "temperatura_saida_1")
    df_temp3 = preparar_base(pd.read_excel(ARQUIVO_EXCEL, sheet_name=9), "Valor_numero", "temperatura_saida_3")
    df_retorno3 = preparar_base(pd.read_excel(ARQUIVO_EXCEL, sheet_name=10), "Valor_numero", "vazao_retorno_3")

    df_hsw["modo_moagem"] = (
        df_hsw["Indicador"].astype(str).str.replace("Vazão de HSW - ", "", regex=False).str.strip()
    )

    df_master = df_umidade[
        [
            "data_hora",
            "data_ref",
            "hora_ref",
            "Date",
            "Hora",
            "umidade_final_farelo",
            "Fato",
            "Causa",
            "Acao",
        ]
    ].copy()

    merges = [
        (df_hsw[["data_hora", "data_ref", "hora_ref", "modo_moagem", "vazao_hsw"]], "hsw"),
        (df_proteina[["data_hora", "data_ref", "hora_ref", "proteina_casca_seca"]], "proteina"),
        (df_pressao1[["data_hora", "data_ref", "hora_ref", "pressao_vapor_1"]], "pressao1"),
        (df_pressao3[["data_hora", "data_ref", "hora_ref", "pressao_vapor_3"]], "pressao3"),
        (df_temp1[["data_hora", "data_ref", "hora_ref", "temperatura_saida_1"]], "temp1"),
        (df_temp3[["data_hora", "data_ref", "hora_ref", "temperatura_saida_3"]], "temp3"),
        (df_retorno3[["data_hora", "data_ref", "hora_ref", "vazao_retorno_3"]], "retorno3"),
    ]

    for merge_df, _ in merges:
        df_master = df_master.merge(merge_df, on=["data_hora", "data_ref", "hora_ref"], how="left")

    df_master["status_umidade"] = "ruim"
    df_master.loc[df_master["umidade_final_farelo"].between(9, 12, inclusive="both"), "status_umidade"] = "bom"
    df_master["data_ref"] = pd.to_datetime(df_master["data_ref"])

    numericas = [
        "umidade_final_farelo",
        "proteina_casca_seca",
        "vazao_hsw",
        "pressao_vapor_1",
        "pressao_vapor_3",
        "temperatura_saida_1",
        "temperatura_saida_3",
        "vazao_retorno_3",
    ]

    comparativo = (
        df_master.groupby("status_umidade")[numericas]
        .agg(["mean", "median", "std", "min", "max"])
        .round(3)
    )

    medianas = df_master.groupby("status_umidade")[numericas[1:]].median().round(3)
    diferencas = medianas.T.copy()
    diferencas["delta_ruim_menos_bom"] = (diferencas["ruim"] - diferencas["bom"]).round(3)
    diferencas["delta_abs"] = diferencas["delta_ruim_menos_bom"].abs().round(3)
    diferencas = diferencas.sort_values("delta_abs", ascending=False)

    correlacoes = (
        df_master[numericas]
        .corr(numeric_only=True)["umidade_final_farelo"]
        .drop("umidade_final_farelo")
        .sort_values(key=lambda s: s.abs(), ascending=False)
        .round(3)
    )

    resumo_dia = (
        df_master.groupby("data_ref")
        .agg(
            total_medicoes=("umidade_final_farelo", "count"),
            media_umidade=("umidade_final_farelo", "mean"),
            min_umidade=("umidade_final_farelo", "min"),
            max_umidade=("umidade_final_farelo", "max"),
            qtd_bom=("status_umidade", lambda s: (s == "bom").sum()),
            qtd_ruim=("status_umidade", lambda s: (s == "ruim").sum()),
        )
        .reset_index()
    )
    resumo_dia["pct_bom"] = (resumo_dia["qtd_bom"] / resumo_dia["total_medicoes"]).round(3)
    resumo_dia["pct_ruim"] = (resumo_dia["qtd_ruim"] / resumo_dia["total_medicoes"]).round(3)
    resumo_dia["classificacao_dia"] = "dia_misto"
    resumo_dia.loc[resumo_dia["pct_bom"] >= 0.8, "classificacao_dia"] = "dia_bom"
    resumo_dia.loc[resumo_dia["pct_ruim"] >= 0.8, "classificacao_dia"] = "dia_ruim"

    top_bons = (
        resumo_dia.sort_values(["pct_bom", "media_umidade"], ascending=[False, True]).head(10).copy()
    )
    top_ruins = (
        resumo_dia.sort_values(["pct_ruim", "media_umidade"], ascending=[False, True]).head(10).copy()
    )

    casos_ruins = (
        df_master[df_master["status_umidade"] == "ruim"][
            [
                "data_hora",
                "umidade_final_farelo",
                "modo_moagem",
                "proteina_casca_seca",
                "vazao_hsw",
                "pressao_vapor_1",
                "pressao_vapor_3",
                "temperatura_saida_1",
                "temperatura_saida_3",
                "vazao_retorno_3",
                "Fato",
                "Causa",
                "Acao",
            ]
        ]
        .sort_values("data_hora")
        .copy()
    )

    modo_status = (
        df_master.groupby(["status_umidade", "modo_moagem"]).size().reset_index(name="qtd").sort_values(
            ["status_umidade", "qtd"], ascending=[True, False]
        )
    )

    df_master.to_csv(OUT_DIR / "df_master.csv", index=False, encoding="utf-8-sig")
    resumo_dia.to_csv(OUT_DIR / "resumo_dia.csv", index=False, encoding="utf-8-sig")
    diferencas.to_csv(OUT_DIR / "diferencas_variaveis.csv", encoding="utf-8-sig")
    casos_ruins.to_csv(OUT_DIR / "casos_ruins_detalhados.csv", index=False, encoding="utf-8-sig")

    fig, ax = plt.subplots(figsize=(10, 7))
    sns.heatmap(df_master[numericas].corr(numeric_only=True), annot=True, cmap="coolwarm", center=0, ax=ax)
    ax.set_title("Correlacao entre umidade e parametros")
    heatmap_path = salvar_grafico(fig, "heatmap_correlacao.png")

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    pares = [
        ("temperatura_saida_3", "Temperatura de saida 3"),
        ("pressao_vapor_3", "Pressao de vapor 3"),
        ("vazao_hsw", "Vazao de HSW"),
        ("temperatura_saida_1", "Temperatura de saida 1"),
    ]
    for ax, (col, titulo) in zip(axes.flatten(), pares):
        sns.boxplot(data=df_master, x="status_umidade", y=col, ax=ax)
        ax.set_title(titulo)
    boxplot_path = salvar_grafico(fig, "boxplots_status_umidade.png")

    fig, ax = plt.subplots(figsize=(10, 6))
    sns.scatterplot(
        data=df_master,
        x="temperatura_saida_3",
        y="umidade_final_farelo",
        hue="status_umidade",
        style="modo_moagem",
        s=90,
        ax=ax,
    )
    ax.axhline(9, color="orange", linestyle="--", linewidth=1)
    ax.axhline(12, color="orange", linestyle="--", linewidth=1)
    ax.set_title("Umidade x temperatura de saida 3")
    scatter_path = salvar_grafico(fig, "scatter_umidade_temp3.png")

    fig, ax = plt.subplots(figsize=(12, 6))
    resumo_plot = resumo_dia.sort_values("data_ref").copy()
    ax.plot(resumo_plot["data_ref"], resumo_plot["pct_bom"], marker="o", label="pct_bom")
    ax.plot(resumo_plot["data_ref"], resumo_plot["pct_ruim"], marker="o", label="pct_ruim")
    ax.set_title("Percentual diario de medicoes boas e ruins")
    ax.legend()
    ax.tick_params(axis="x", rotation=45)
    serie_path = salvar_grafico(fig, "serie_pct_diario.png")

    linhas_relatorio = []
    linhas_relatorio.append("# Analise consolidada de umidade\n")
    linhas_relatorio.append(f"Abas utilizadas: {', '.join(xl.sheet_names[1:])}\n")
    linhas_relatorio.append(f"Total de medicoes: {len(df_master)}")
    linhas_relatorio.append(f"Medicoes boas: {(df_master['status_umidade'] == 'bom').sum()}")
    linhas_relatorio.append(f"Medicoes ruins: {(df_master['status_umidade'] == 'ruim').sum()}\n")

    linhas_relatorio.append("## Parametros que mais se diferenciaram entre os contextos de umidade boa e ruim (mediana)\n")
    linhas_relatorio.append(diferencas.to_string())
    linhas_relatorio.append("\n")

    linhas_relatorio.append("## Correlacoes com a umidade\n")
    linhas_relatorio.append(correlacoes.to_string())
    linhas_relatorio.append("\n")

    linhas_relatorio.append("## Top 10 dias bons\n")
    linhas_relatorio.append(top_bons.to_string(index=False))
    linhas_relatorio.append("\n")

    linhas_relatorio.append("## Top 10 dias ruins\n")
    linhas_relatorio.append(top_ruins.to_string(index=False))
    linhas_relatorio.append("\n")

    linhas_relatorio.append("## Contexto de moagem por status\n")
    linhas_relatorio.append(modo_status.to_string(index=False))
    linhas_relatorio.append("\n")

    hipoteses = []
    for variavel in diferencas.head(3).index.tolist():
        delta = diferencas.loc[variavel, "delta_ruim_menos_bom"]
        sinal = "acima" if delta > 0 else "abaixo"
        hipoteses.append(
            f"- Os dados sugerem que `{variavel}` tende a operar {sinal} do contexto bom nos casos ruins."
        )

    linhas_relatorio.append("## Hipoteses operacionais iniciais\n")
    linhas_relatorio.append(
        "Observacao metodologica: os parametros abaixo nao sao classificados como bons ou ruins. "
        "Eles aparecem apenas como contexto operacional observado quando a umidade ficou dentro ou fora da especificacao."
    )
    linhas_relatorio.extend(hipoteses)
    linhas_relatorio.append("")

    linhas_relatorio.append("## Observacoes sobre os casos ruins\n")
    linhas_relatorio.append(
        "As colunas `Fato`, `Causa` e `Acao` foram mantidas na base mestra e salvas em `casos_ruins_detalhados.csv` para leitura qualitativa dos horarios fora de especificacao."
    )
    linhas_relatorio.append("")

    linhas_relatorio.append("## Graficos gerados\n")
    linhas_relatorio.append(f"- {heatmap_path}")
    linhas_relatorio.append(f"- {boxplot_path}")
    linhas_relatorio.append(f"- {scatter_path}")
    linhas_relatorio.append(f"- {serie_path}")
    linhas_relatorio.append("")

    relatorio_md = "\n".join(linhas_relatorio)
    (OUT_DIR / "relatorio_analise_umidade.md").write_text(relatorio_md, encoding="utf-8")
    (OUT_DIR / "relatorio_analise_umidade.txt").write_text(relatorio_md, encoding="utf-8")

    print(f"Arquivos gerados em: {OUT_DIR}")


if __name__ == "__main__":
    main()
