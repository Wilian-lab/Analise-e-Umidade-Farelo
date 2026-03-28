# Analise de Umidade do Farelo

Projeto de analise de indicadores industriais e visualizacao em Streamlit para acompanhar a umidade final do farelo no processo de secagem.

## Objetivo

O dashboard foi construido para responder de forma clara:

- quais parametros operacionais estavam presentes quando a umidade ficou dentro da faixa
- quais parametros operacionais estavam presentes quando a umidade ficou fora da faixa

A classificacao vale somente para `umidade_final_farelo`:

- `bom`: entre `9` e `12`
- `ruim`: abaixo de `9`

Temperaturas, pressoes, vazoes, retorno e modo de moagem aparecem como contexto operacional observado, sem julgamento de valor.

## Base da analise

Arquivo-base utilizado:

- `data/Acompanhamento_indicadores.xlsx`

Principais abas consideradas na consolidacao:

- `Umidade final farelo`
- `Proteina casca seca`
- `Vazao de HSW`
- `Pressao de vapor 1`
- `Pressao de vapor 3`
- `Temperatura de saida 1`
- `Temperatura de saida 3`
- `Vazao de retorno 3`

## Componentes do projeto

### Consolidacao de dados

Arquivo:

- `src/analise_umidade.py`

Responsavel por:

- ler os dados brutos do Excel
- padronizar `data_hora`
- relacionar a medicao de umidade com os parametros do mesmo horario
- classificar a umidade como `bom` ou `ruim`
- gerar a base consolidada para o dashboard

### Dashboard principal

Arquivo:

- `src/dashboard_analise_umidade.py`

Principais entregas visuais:

- KPIs principais da operacao
- comparacao entre contextos de umidade boa e ruim
- leitura diaria por horario
- destaque visual para a umidade por horario
- contexto observado por modo de moagem
- tabelas detalhadas para analise operacional

### Arquivos de apoio

- `src/dashboard_streamlit.py`
- `src/main.ipynb`

Esses arquivos apoiam a exploracao e o desenvolvimento do projeto.

## Principais pontos da analise

- a leitura acontece por horario
- o painel mostra contexto operacional observado, e nao causalidade
- quando `modo_moagem = Ambas`, o contexto pode envolver os dois secadores
- variacoes dentro do mesmo horario podem acontecer por transicao operacional
- a interpretacao correta sempre parte da umidade, e depois observa os parametros que estavam rodando naquele momento

## Estrutura principal

```text
Indicadores_Umidade/
  src/
    analise_umidade.py
    dashboard_analise_umidade.py
  requirements.txt
  requirements-dev.txt
  README.md
```

## Como executar

### 1. Instalar dependencias

```powershell
pip install -r requirements.txt
```

### 2. Gerar a base consolidada

```powershell
python src\analise_umidade.py
```

### 3. Rodar o dashboard

```powershell
streamlit run src\dashboard_analise_umidade.py
```

## Observacoes

- a planilha bruta nao deve ser exposta publicamente
- para execucao completa, a base consolidada precisa existir ou ser gerada antes
- a leitura do painel deve ser feita sempre como observacao operacional dos horarios analisados

## Status atual

O projeto esta estruturado para:

- validacao final dos numeros
- apresentacao da analise
- publicacao e deploy do dashboard principal
