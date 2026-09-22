# Métricas oficiais do AVScope

Todas as funções estão em `src/metrics.py` e operam exclusivamente sobre `data/processed/avscope_mvp_domestic.parquet` ou sobre um `DataFrame`/`LazyFrame` Polars já carregado. O CSV bruto nunca é consultado pelo módulo.

## Totais

`basic_metrics` retorna somas de `PASSAGEIROS_PAGOS`, `ASSENTOS`, `DECOLAGENS`, `ASK` e `RPK`, além de contagens distintas de `EMPRESA_ID` e `ROTA_DIRECIONAL`. As funções nominais `total_passengers`, `total_seats`, `total_departures`, `total_ask`, `total_rpk`, `number_of_companies` e `number_of_routes` expõem os mesmos cálculos. A unidade segue a definição ANAC: passageiros, assentos ofertados, decolagens, assento-quilômetro ofertado e passageiro-quilômetro pago.

Uma soma é nula quando todos os valores do recorte são nulos. Zero observado permanece zero. Um recorte sem linhas retorna métricas nulas e contagens iguais a zero.

## Load Factor

`LOAD_FACTOR_PCT = SUM(RPK) / SUM(ASK) * 100`.

Não se usa média de percentuais mensais. O resultado é nulo se RPK ou ASK agregados forem nulos, ou se ASK for menor ou igual a zero. Valores acima de 100% são preservados, conforme a ressalva metodológica da ANAC para certos níveis de desagregação.

## Passageiros por decolagem

`PASSAGEIROS_POR_DECOLAGEM = SUM(PASSAGEIROS_PAGOS) / SUM(DECOLAGENS)`.

O resultado é nulo se passageiros ou decolagens forem nulos, ou se as decolagens forem menores ou iguais a zero.

## Market share e HHI

`market_share_by_company` aceita rota, um `period` específico ou intervalo `start`/`end`, agrega passageiros por `EMPRESA_ID`, preserva `EMPRESA_SIGLA` e `EMPRESA_NOME`, e calcula `PASSAGEIROS_PAGOS_DA_COMPANHIA / PASSAGEIROS_PAGOS_TOTAL_DA_ROTA * 100`. Se o total da rota for nulo ou não positivo, os shares são nulos.

`market_hhi` calcula a soma dos quadrados dos shares na escala 0–100. Não há classificação concorrencial embutida.

## Crescimento, ano e YTD

`growth_percent = (valor_atual - valor_anterior) / valor_anterior * 100`. O retorno é nulo se qualquer valor estiver ausente ou se o anterior for zero; infinito nunca é retornado.

`period_coverage` identifica período mínimo/máximo, último ano, último mês e completude anual. `annual_comparison` compara anos completos quando existem 12 meses de janeiro a dezembro. Para ano parcial, usa YTD: janeiro até o último mês disponível no ano atual contra exatamente os mesmos meses do ano anterior. Na base atual, compara jan–jul/2026 com jan–jul/2025.

## Série e filtros

`monthly_route_series` recebe origem ICAO, destino ICAO, datas inicial/final e `EMPRESA_ID` opcional. Retorna uma linha por mês, em ordem cronológica, com as cinco métricas e Load Factor. `filter_data`, `available_origins`, `available_destinations`, `available_companies` e `period_coverage` centralizam a lógica que será reutilizada pelo app.

As rotas são direcionais: `SBBE>SBGR` e `SBGR>SBBE` nunca são combinadas.

## Qualidade

O Parquet oficial mantém flags para `RPK > ASK`, passageiros pagos acima de assentos, ASK zero com RPK positivo, decolagens zero com passageiros positivos e assentos zero com passageiros positivos. `quality_summary` conta essas ocorrências no recorte, e a série mensal propaga as flags por mês. Nenhuma anomalia é excluída ou truncada automaticamente.

