# Qualidade da base processada

Gerado em: `2026-09-14T10:51:15`

## Controles de execucao

- Linhas brutas: `1096554`.
- Linhas utilizadas: `1096554`.
- Linhas excluidas: `0`.
- Motivos de exclusao: nenhum; categorias ambiguas ou fora do recorte sugerido foram preservadas com flags.
- Linhas na tabela agregada: `1096554`.
- Soma de `QTD_REGISTROS_FONTE`: `1096554`; maximo por grupo: `1`.
- Grupos que combinaram mais de uma linha fonte: `0`.
- Periodo: `2000-01-01` a `2026-07-01`.
- Companhias por `EMPRESA_ID`: `328`.
- Aeroportos distintos na uniao origem/destino: `1181`.
- Aeroportos de origem: `1107`; de destino: `1129`.
- Rotas direcionais com chave nao nula: `17090`.
- Linhas brutas marcadas para o universo sugerido do MVP: `624683`.
- Grupos agregados marcados para o universo sugerido do MVP: `624683`.
- Tamanho do Parquet: `20910279` bytes.
- Impressao digital logica do conteudo: `06e62fc17ffa782f8903586cacd85e79dcafc327dfefbf0de0550e427b3b9ec8`.
- SHA-256 bruto antes: `270b815c5ded4a254aea3a2f8ebd731e53a2cb8eeb9f1689d013ddb6eda4ec92`.
- SHA-256 bruto depois: `270b815c5ded4a254aea3a2f8ebd731e53a2cb8eeb9f1689d013ddb6eda4ec92`.
- Arquivo bruto preservado: `True`.

## Metricas principais

| METRICA | NULOS | NEGATIVOS | ZEROS |
| --- | --- | --- | --- |
| PASSAGEIROS_PAGOS | 40353 | 0 | 288341 |
| ASSENTOS | 237941 | 0 | 188355 |
| DECOLAGENS | 237940 | 0 | 1856 |
| ASK | 238521 | 0 | 195306 |
| RPK | 238008 | 0 | 227692 |

## Reconciliacao das somas

| METRICA | SOMA_BRUTA | SOMA_PROCESSADA | DIFERENCA |
| --- | --- | --- | --- |
| PASSAGEIROS_PAGOS | 2241403387 | 2241403387 | 0 |
| ASSENTOS | 3252236849 | 3252236849 | 0 |
| DECOLAGENS | 22959447 | 22959447 | 0 |
| ASK | 5663577135228 | 5663577135228 | 0 |
| RPK | 4396588532094 | 4396588532094 | 0 |

As cinco metricas aditivas reconciliam exatamente entre a fonte e o Parquet.

## Consistencias cruzadas

- Casos com `RPK > ASK`: `2498`.
- Casos com `PASSAGEIROS_PAGOS > ASSENTOS`: `22144`. A comparacao e feita no mesmo grao mensal, rota, companhia, natureza e grupo de voo.
- Rotas com origem igual ao destino: `23513`.
- Grupos com codigo de origem ou destino ausente: `5212`.
- Grupos afetados por combustivel negativo: `27`.
- Chaves `PERIODO + ROTA_DIRECIONAL + EMPRESA_ID` com mais de uma categoria operacional: `169696`; maximo de `3` categorias por chave.

## Possiveis outliers

O criterio exploratorio usa limite superior `Q3 + 3 x IQR` em cada metrica principal. Ele apenas sinaliza extremos; nenhum registro foi removido.

| METRICA | LIMITE_IQR_3X | CANDIDATOS | P99 | P99_9 | MAX |
| --- | --- | --- | --- | --- | --- |
| PASSAGEIROS_PAGOS | 8044.0 | 79228 | 22853.0 | 46416.0 | 92357.0 |
| ASSENTOS | 18702.0 | 33113 | 34177.0 | 80354.0 | 154845.0 |
| DECOLAGENS | 118.0 | 34104 | 208.0 | 564.0 | 918.0 |
| ASK | 19751202.0 | 74703 | 89937040.0 | 166110606.0 | 340016292.0 |
| RPK | 13631360.0 | 81432 | 74954700.0 | 141432390.0 | 293260198.0 |

Grupos marcados em qualquer metrica por `FLAG_POSSIVEL_OUTLIER`: `123886`. A heterogeneidade entre rotas e tamanhos de empresa torna esses candidatos insuficientes, por si sos, para diagnosticar erro.

## Registros de combustivel negativo

| LINHA_ARQUIVO | ANO | MES | EMPRESA_SIGLA | EMPRESA_NOME | AEROPORTO_DE_ORIGEM_SIGLA | AEROPORTO_DE_DESTINO_SIGLA | NATUREZA | GRUPO_DE_VOO | PASSAGEIROS_PAGOS | ASSENTOS | DECOLAGENS | ASK | RPK | COMBUSTIVEL_LITROS |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 298226 | 2006 | 5 | TTL | TOTAL LINHAS AÉREAS S.A. | SBVT | SBGV | DOMÉSTICA | NÃO REGULAR | 6 | 45 | 1 | 10485 | 3728 | -1746 |
| 282341 | 2006 | 9 | PTB | PASSAREDO TRANSPORTES AÉREOS S.A. | SBRP | SIMK | DOMÉSTICA | REGULAR | 312 | 870 | 29 | 63510 | 38909 | -161061 |
| 282365 | 2006 | 10 | PTB | PASSAREDO TRANSPORTES AÉREOS S.A. | SBGR | SBRP | DOMÉSTICA | REGULAR | 1134 | 1860 | 62 | 537540 | 392173 | -8562 |
| 282375 | 2006 | 10 | PTB | PASSAREDO TRANSPORTES AÉREOS S.A. | SBRP | SIMK | DOMÉSTICA | REGULAR | 252 | 840 | 28 | 61320 | 30660 | -77664 |
| 282399 | 2006 | 11 | PTB | PASSAREDO TRANSPORTES AÉREOS S.A. | SBGR | SBRP | DOMÉSTICA | REGULAR | 1089 | 1830 | 61 | 528870 | 342465 | -9875 |
| 282409 | 2006 | 11 | PTB | PASSAREDO TRANSPORTES AÉREOS S.A. | SBRP | SIMK | DOMÉSTICA | REGULAR | 221 | 780 | 26 | 56940 | 27813 | -161510 |
| 282433 | 2006 | 12 | PTB | PASSAREDO TRANSPORTES AÉREOS S.A. | SBGR | SBRP | DOMÉSTICA | REGULAR | 815 | 1830 | 61 | 528870 | 279752 | -43253 |
| 282443 | 2006 | 12 | PTB | PASSAREDO TRANSPORTES AÉREOS S.A. | SBRP | SIMK | DOMÉSTICA | REGULAR | 192 | 570 | 19 | 41610 | 21316 | -113234 |
| 328134 | 2007 | 1 | PTB | PASSAREDO TRANSPORTES AÉREOS S.A. | SBGR | SBRP | DOMÉSTICA | REGULAR | 925 | 1860 | 62 | 537540 | 316744 | -70235 |
| 328144 | 2007 | 1 | PTB | PASSAREDO TRANSPORTES AÉREOS S.A. | SBRP | SIMK | DOMÉSTICA | REGULAR | 145 | 630 | 21 | 45990 | 20148 | -197121 |
| 306620 | 2007 | 2 | AMG | AIR MINAS LINHAS AÉREAS LTDA. | TNCC | SBEG | INTERNACIONAL | IMPRODUTIVO | 0 | 30 | 1 | 58770 | 0 | -10619 |
| 328170 | 2007 | 2 | PTB | PASSAREDO TRANSPORTES AÉREOS S.A. | SBGR | SBRP | DOMÉSTICA | REGULAR | 503 | 1140 | 38 | 329460 | 186983 | -8408 |
| 328180 | 2007 | 2 | PTB | PASSAREDO TRANSPORTES AÉREOS S.A. | SBRP | SIMK | DOMÉSTICA | REGULAR | 42 | 210 | 7 | 15330 | 5840 | -49023 |
| 306648 | 2007 | 3 | AMG | AIR MINAS LINHAS AÉREAS LTDA. | SBVG | SNDV | DOMÉSTICA | REGULAR | 8 | 630 | 21 | 106470 | 34983 | -6322 |
| 306737 | 2007 | 5 | AMG | AIR MINAS LINHAS AÉREAS LTDA. | SNDV | SBBH | DOMÉSTICA | REGULAR | 1 | 600 | 20 | 61800 | 8755 | -8979 |
| 306766 | 2007 | 6 | AMG | AIR MINAS LINHAS AÉREAS LTDA. | SBGR | SBVG | DOMÉSTICA | REGULAR | 87 | 630 | 21 | 144900 | 44850 | -2120 |
| 306790 | 2007 | 6 | AMG | AIR MINAS LINHAS AÉREAS LTDA. | SNDV | SBBH | DOMÉSTICA | REGULAR | 13 | 600 | 20 | 61800 | 10918 | -21223 |
| 306827 | 2007 | 7 | AMG | AIR MINAS LINHAS AÉREAS LTDA. | SBGR | SBVG | DOMÉSTICA | REGULAR | 66 | 600 | 20 | 138000 | 42780 | -3059 |
| 306828 | 2007 | 7 | AMG | AIR MINAS LINHAS AÉREAS LTDA. | SBGR | SNDV | DOMÉSTICA | REGULAR | 93 | 30 | 1 | 11940 | 3582 | -11947 |
| 306834 | 2007 | 7 | AMG | AIR MINAS LINHAS AÉREAS LTDA. | SBKP | SNDV | DOMÉSTICA | REGULAR | 9 | 30 | 1 | 11760 | 3528 | -12281 |
| 306853 | 2007 | 7 | AMG | AIR MINAS LINHAS AÉREAS LTDA. | SBVG | SNDV | DOMÉSTICA | REGULAR | 18 | 570 | 19 | 96330 | 35152 | -6439 |
| 306922 | 2007 | 9 | AMG | AIR MINAS LINHAS AÉREAS LTDA. | SNDV | SBBH | DOMÉSTICA | REGULAR | 22 | 300 | 10 | 30900 | 6489 | -10807 |
| 306928 | 2007 | 10 | AMG | AIR MINAS LINHAS AÉREAS LTDA. | SBAE | SBGR | DOMÉSTICA | REGULAR | 183 | 360 | 12 | 108720 | 55266 | -19061 |
| 352406 | 2008 | 4 | AMG | AIR MINAS LINHAS AÉREAS LTDA. | SBBH | SBBH | DOMÉSTICA | IMPRODUTIVO | 0 | 60 | 2 | 0 | 0 | -12064 |
| 352462 | 2008 | 7 | AMG | AIR MINAS LINHAS AÉREAS LTDA. | SBIP | SBBH | DOMÉSTICA | NÃO REGULAR | 0 | 30 | 1 | 4770 | 0 | -12687 |
| 352483 | 2008 | 8 | AMG | AIR MINAS LINHAS AÉREAS LTDA. | SBRJ | SBBH | DOMÉSTICA | NÃO REGULAR | 0 | 30 | 1 | 10500 | 0 | -12326 |
| 352499 | 2008 | 9 | AMG | AIR MINAS LINHAS AÉREAS LTDA. | SBGL | SBBH | DOMÉSTICA | NÃO REGULAR | 0 | 30 | 1 | 10110 | 0 | -12507 |

## Problemas remanescentes

- Existem nulos nas metricas principais; eles foram preservados para distinguir ausencia de informacao de zero.
- A coluna aeroportuaria `SIGLA` nao declara separadamente ICAO e IATA.
- Ha `5212` grupos sem codigo completo de rota.
- Ha `23513` grupos com origem igual ao destino, mantidos para investigacao.
- Ha `2498` casos com `RPK > ASK` e `22144` com passageiros pagos acima de assentos no mesmo grao.
- Extremos estatisticos foram sinalizados, nao removidos.
- A definicao de transporte regular de passageiros permanece uma regra analitica explicita por flags, pois `GRUPO_DE_VOO` nao separa sozinho operacoes de passageiros e carga.

