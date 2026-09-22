# Metodologia de tratamento

Gerado em: `2026-09-14T10:51:15`

## Fonte e colunas confirmadas

- Fonte imutavel: `data/raw/Dados_Estatisticos.csv`.
- Cabecalho na segunda linha, separador `;` e encoding UTF-8 com BOM, conforme a auditoria.
- O arquivo possui uma unica coluna de codigo por aeroporto (`AEROPORTO_DE_ORIGEM_SIGLA` e `AEROPORTO_DE_DESTINO_SIGLA`). Nao ha colunas separadas de ICAO e IATA, portanto o pipeline preserva os nomes reais sem atribuir um padrao de codigo nao documentado.

| conceito | coluna_real |
| --- | --- |
| ano | ANO |
| mes | MES |
| empresa_aerea | EMPRESA_NOME |
| sigla_empresa | EMPRESA_SIGLA |
| aeroporto_origem | AEROPORTO_DE_ORIGEM_NOME |
| codigo_origem | AEROPORTO_DE_ORIGEM_SIGLA |
| uf_origem | AEROPORTO_DE_ORIGEM_UF |
| regiao_origem | AEROPORTO_DE_ORIGEM_REGIAO |
| pais_origem | AEROPORTO_DE_ORIGEM_PAIS |
| aeroporto_destino | AEROPORTO_DE_DESTINO_NOME |
| codigo_destino | AEROPORTO_DE_DESTINO_SIGLA |
| uf_destino | AEROPORTO_DE_DESTINO_UF |
| regiao_destino | AEROPORTO_DE_DESTINO_REGIAO |
| pais_destino | AEROPORTO_DE_DESTINO_PAIS |
| natureza | NATUREZA |
| grupo_de_voo | GRUPO_DE_VOO |
| passageiros_pagos | PASSAGEIROS_PAGOS |
| passageiros_gratis | PASSAGEIROS_GRATIS |
| assentos | ASSENTOS |
| decolagens | DECOLAGENS |
| ask | ASK |
| rpk | RPK |
| distancia_voada | DISTANCIA_VOADA_KM |
| combustivel | COMBUSTIVEL_LITROS |
| horas_voadas | HORAS_VOADAS |

## Definicao do universo analitico

Valores e volumes encontrados antes de qualquer recorte:

| NATUREZA | GRUPO_DE_VOO | LINHAS | COM_EVIDENCIA_PASSAGEIROS | PASSAGEIROS_PAGOS_SOMA |
| --- | --- | --- | --- | --- |
| DOMÉSTICA | IMPRODUTIVO | 83794 | 19211 | 748613 |
| DOMÉSTICA | NÃO IDENTIFICADO | 4 | 0 | 0 |
| DOMÉSTICA | NÃO REGULAR | 190157 | 154112 | 66960431 |
| DOMÉSTICA | REGULAR | 534044 | 505335 | 1745436822 |
| INTERNACIONAL |  | 2 | 0 | 0 |
| INTERNACIONAL | IMPRODUTIVO | 12537 | 2658 | 36024 |
| INTERNACIONAL | NÃO IDENTIFICADO | 7 | 0 | 0 |
| INTERNACIONAL | NÃO REGULAR | 84132 | 33220 | 14309062 |
| INTERNACIONAL | REGULAR | 191877 | 119348 | 413912435 |

`GRUPO_DE_VOO = REGULAR` identifica com seguranca a regularidade da operacao. Entretanto, a coluna nao distingue sozinha voos regulares de passageiros de voos regulares exclusivamente cargueiros. `NATUREZA` distingue `DOMESTICA` e `INTERNACIONAL`, mas o escopo do mercado brasileiro nao determina, por si so, que voos internacionais devam ser descartados.

Por isso, nenhuma linha foi excluida. O recorte recomendado para o MVP foi implementado como flags:

- `FLAG_VOO_REGULAR`: `GRUPO_DE_VOO = REGULAR`.
- `FLAG_EVIDENCIA_TRANSPORTE_PASSAGEIROS`: ao menos uma entre `PASSAGEIROS_PAGOS`, `PASSAGEIROS_GRATIS`, `ASSENTOS`, `ASK` ou `RPK` e maior que zero.
- `FLAG_UNIVERSO_MVP`: as duas condicoes anteriores simultaneamente.

Assim, o futuro aplicativo pode aplicar o recorte sem perda irreversivel. `IMPRODUTIVO`, `NAO REGULAR`, `NAO IDENTIFICADO` e os dois registros sem `GRUPO_DE_VOO` permanecem disponiveis e explicitamente classificados.

## Chaves analiticas

- `ROTA_DIRECIONAL`: concatenacao dos codigos reais de origem e destino com `>`. Exemplo: `SBBE>SBGR`. A direcao e preservada. Se qualquer codigo estiver ausente, a chave permanece nula.
- `EMPRESA_ID`: concatenacao exata de `EMPRESA_SIGLA` e `EMPRESA_NOME` com `|`. Isso evita misturar empresas que reutilizam a mesma sigla.
- Grao final: `PERIODO` + `ROTA_DIRECIONAL` + `EMPRESA_ID` + atributos aeroportuarios + `NATUREZA` + `GRUPO_DE_VOO`. As duas ultimas dimensoes permanecem no grao para impedir a mistura de categorias operacionais diferentes.

A agregacao resultou em `1096554` linhas, igual ao bruto, com maximo de `1` registro fonte por grupo. Portanto, a fonte ja se encontra nesse grao quando todas as dimensoes necessarias sao preservadas. A etapa de agregacao continua explicita para garantir o comportamento em futuras atualizacoes do CSV.

Na chave minima `PERIODO + ROTA_DIRECIONAL + EMPRESA_ID`, `169696` combinacoes aparecem em mais de uma categoria operacional, com maximo de `3` categorias. Isso confirma que retirar `NATUREZA` e `GRUPO_DE_VOO` misturaria universos distintos.

## Empresas com siglas ambiguas

| EMPRESA_SIGLA | EMPRESA_NOME | LINHAS | ANO_MIN | ANO_MAX | PERIODO_MIN | PERIODO_MAX |
| --- | --- | --- | --- | --- | --- | --- |
| ABJ | ABAETÉ LINHAS AÉREAS S.A. | 1466 | 2000 | 2017 | 2000-01-01 | 2017-09-01 |
| ABJ | ATA - AEROTÁXI ABAETÉ LTDA. | 338 | 2021 | 2026 | 2021-12-01 | 2026-07-01 |
| ARU | AIR ARUBA | 3 | 2013 | 2013 | 2013-06-01 | 2013-07-01 |
| ARU | ARUBA AIRLINES | 44 | 2025 | 2026 | 2025-06-01 | 2026-07-01 |
| TSC | AIR TRANSAT A.T. INC | 77 | 2015 | 2021 | 2015-10-01 | 2021-10-01 |
| TSC | AIR TRANSAT A.T. INC DO BRASIL | 23 | 2022 | 2026 | 2022-02-01 | 2026-05-01 |

Os periodos nao se sobrepoem dentro de cada sigla, mas os nomes foram preservados na identificacao. Nenhuma consolidacao por sigla foi aplicada.

## Tipos, nulos e agregacao

- `ANO` e `MES`: `Int64`.
- `PERIODO`: `Date`, sempre no primeiro dia do mes.
- Metricas aditivas: `PASSAGEIROS_PAGOS`, `ASSENTOS`, `DECOLAGENS`, `ASK`, `RPK` e `COMBUSTIVEL_LITROS`.
- `HORAS_VOADAS`: convertido de texto com virgula decimal para `Float64` durante o tratamento, mas nao persistido por nao ser necessario ao MVP ou as chaves.
- `PASSAGEIROS_GRATIS` e `DISTANCIA_VOADA_KM`: tipados e usados na classificacao/validacao, mas nao persistidos na tabela enxuta.
- Uma soma e nula quando todos os valores do grupo sao nulos. Zeros informados permanecem zero.
- Load Factor nao foi persistido. Quando implementado, deve ser calculado como `SUM(RPK) / SUM(ASK)`.

## Combustivel negativo

Os `27` registros negativos nao foram excluidos. `COMBUSTIVEL_LITROS` permanece agregado, enquanto `FLAG_COMBUSTIVEL_NEGATIVO`, `QTD_REGISTROS_COMBUSTIVEL_NEGATIVO` e `COMBUSTIVEL_NEGATIVO_MIN` identificam os grupos afetados. Os valores originais e a linha fisica do CSV estao listados no relatorio de qualidade; a fonte bruta permanece imutavel.

## Colunas da base processada

- `ANO`
- `MES`
- `PERIODO`
- `EMPRESA_ID`
- `EMPRESA_SIGLA`
- `EMPRESA_NOME`
- `EMPRESA_NACIONALIDADE`
- `ROTA_DIRECIONAL`
- `AEROPORTO_DE_ORIGEM_SIGLA`
- `AEROPORTO_DE_ORIGEM_NOME`
- `AEROPORTO_DE_ORIGEM_UF`
- `AEROPORTO_DE_ORIGEM_REGIAO`
- `AEROPORTO_DE_ORIGEM_PAIS`
- `AEROPORTO_DE_DESTINO_SIGLA`
- `AEROPORTO_DE_DESTINO_NOME`
- `AEROPORTO_DE_DESTINO_UF`
- `AEROPORTO_DE_DESTINO_REGIAO`
- `AEROPORTO_DE_DESTINO_PAIS`
- `NATUREZA`
- `GRUPO_DE_VOO`
- `PASSAGEIROS_PAGOS`
- `ASSENTOS`
- `DECOLAGENS`
- `ASK`
- `RPK`
- `COMBUSTIVEL_LITROS`
- `QTD_REGISTROS_FONTE`
- `FLAG_VOO_REGULAR`
- `FLAG_EVIDENCIA_TRANSPORTE_PASSAGEIROS`
- `FLAG_UNIVERSO_MVP`
- `FLAG_COMBUSTIVEL_NEGATIVO`
- `QTD_REGISTROS_COMBUSTIVEL_NEGATIVO`
- `COMBUSTIVEL_NEGATIVO_MIN`
- `FLAG_POSSIVEL_OUTLIER`

## Reproducao

```powershell
python -m src.process_data
```

O pipeline usa leitura lazy com projecao apenas das colunas necessarias, agrega por streaming e grava Parquet com compressao Zstandard.

