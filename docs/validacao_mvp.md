# Validacao metodologica do universo do MVP

Gerado em: `2026-09-14T11:24:09`

Fonte: `data/processed/avscope_routes_monthly.parquet`. O arquivo principal nao foi alterado.

## Flags atuais

- `FLAG_VOO_REGULAR`: verdadeira quando `GRUPO_DE_VOO == "REGULAR"`; nulos viram `False`.
- `FLAG_EVIDENCIA_TRANSPORTE_PASSAGEIROS`: verdadeira quando pelo menos um destes campos e maior que zero: `PASSAGEIROS_PAGOS`, `PASSAGEIROS_GRATIS`, `ASSENTOS`, `ASK` ou `RPK`.
- `FLAG_UNIVERSO_MVP`: conjuncao de `FLAG_VOO_REGULAR` e `FLAG_EVIDENCIA_TRANSPORTE_PASSAGEIROS`.

A regra nao exige `PASSAGEIROS_PAGOS > 0`: uma etapa com zero passageiros pagos permanece quando ha oferta ou outra evidencia positiva. Entretanto, `DECOLAGENS` nao participa da expressao. Alem disso, a evidencia e avaliada linha a linha, o que elimina meses zerados de uma rota-companhia que possui operacao de passageiros comprovada em outros meses.

Nao e adequado simplesmente acrescentar `DECOLAGENS > 0` a regra da linha, porque operacoes exclusivamente cargueiras tambem decolam. A evidencia historica no mesmo par rota-companhia inclui a continuidade dos meses zerados sem transformar toda decolagem regular em transporte de passageiros.

A implementacao das flags persistidas confere com o codigo: `0` divergencias em `FLAG_VOO_REGULAR` e `0` em `FLAG_UNIVERSO_MVP`. A regra historica recupera `11416` meses no universo final, dos quais `3720` no universo candidato possuem decolagens positivas. Portanto, usar a flag atual como filtro definitivo causaria vies de selecao temporal.

## Universo recomendado

A validacao propoe duas camadas:

1. `FLAG_CANDIDATO_MVP_DOMESTICO`: `GRUPO_DE_VOO = REGULAR`, `NATUREZA = DOMÉSTICA`, ambos os paises iguais a `BRASIL` e evidencia positiva de passageiros em pelo menos um mes regular da mesma `ROTA_DIRECIONAL + EMPRESA_ID`.
2. `FLAG_UNIVERSO_MVP_RECOMENDADO`: camada anterior mais codigo de origem e destino presentes e origem diferente do destino.

Isso inclui meses com zero passageiros na continuidade de uma operacao de passageiros, exclui rotas puramente cargueiras sem evidencia historica e separa registros que nao representam um mercado origem-destino valido. Nenhum registro foi removido do Parquet principal.

### Comparacao de escopos

| UNIVERSO | REGISTROS | PASSAGEIROS_PAGOS | ROTAS | COMPANHIAS | AEROPORTOS | PERIODO_MIN | PERIODO_MAX |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CANDIDATO_DOMESTICO_ANTES_DA_VALIDACAO_OD | 517678 | 1745436822 | 5289 | 43 | 334 | 2000-01-01 | 2026-07-01 |
| MVP_DOMESTICO_RECOMENDADO | 515449 | 1745380380 | 5187 | 43 | 334 | 2000-01-01 | 2026-07-01 |
| REGULAR_PASSAGEIROS_INCLUINDO_INTERNACIONAL | 625868 | 2146655629 | 6700 | 143 | 572 | 2000-01-01 | 2026-07-01 |

O universo com internacional inclui rotas geograficamente domesticas e rotas com exatamente uma ponta no Brasil, desde que regulares, validas e com evidencia historica de passageiros. `DEMAIS_CASOS` nao entra.

## Codigos de aeroportos

| IATA_EXIBICAO | CODIGO_INTERNO_FONTE | NOME_NO_DATASET |
| --- | --- | --- |
| BEL | SBBE | BELÉM |
| GRU | SBGR | GUARULHOS |
| CGH | SBSP | SÃO PAULO |
| SDU | SBRJ | RIO DE JANEIRO |
| BSB | SBBR | BRASÍLIA |
| MAO | SBEG | MANAUS |

Os campos `AEROPORTO_DE_ORIGEM_SIGLA` e `AEROPORTO_DE_DESTINO_SIGLA` contem codigos de quatro letras compatíveis com designadores OACI/ICAO, como `SBBE` e `SBGR`. O dataset nao possui coluna IATA. A chave interna continua usando o codigo oficial de quatro letras da fonte; para exibicao, o futuro app deve juntar uma tabela aeroportuaria oficial OACI-IATA e mostrar o IATA com o nome. A tabela acima e apenas o mapeamento validado das seis localidades usadas neste teste.

Fontes metodologicas: [metadados dos Dados Estatisticos do Transporte Aereo da ANAC](https://www.anac.gov.br/acesso-a-informacao/dados-abertos/areas-de-atuacao/voos-e-operacoes-aereas/dados-estatisticos-do-transporte-aereo/48-dados-estatisticos-do-transporte-aereo) e [metadados de Aerodromos Publicos da ANAC](https://www.gov.br/anac/pt-br/acesso-a-informacao/dados-abertos/areas-de-atuacao/aerodromos/aerodromos-publicos/aerodromos-publicos-caracteristicas-gerais/metadados-aerodromos-publicos-caracteristicas-gerais).

## Rotas de teste

### `BEL -> GRU`
| ROTA_DIRECIONAL | PRIMEIRO_MES | ULTIMO_MES | MESES_COM_REGISTROS | QTD_COMPANHIAS | COMPANHIAS | PASSAGEIROS_PAGOS | ASSENTOS | DECOLAGENS | ASK | RPK |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SBBE>SBGR | 2000-01-01 | 2026-07-01 | 317 | 10 | AZU, BRB, GLO, ONE, PLY, TAM, TBA, TIB, VRG, VSP | 4668911 | 5504342 | 29698 | 13546185662 | 10949559952 |

Ultimos 12 meses disponiveis:
| PERIODO | COMPANHIAS_NO_MES | PASSAGEIROS_PAGOS | ASSENTOS | DECOLAGENS | ASK | RPK | LOAD_FACTOR_PCT | PASSAGEIROS_POR_DECOLAGEM |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2025-08-01 | 2 | 30610 | 34253 | 176 | 84296633 | 75331210 | 89.3644 | 173.9205 |
| 2025-09-01 | 2 | 32391 | 39983 | 210 | 98398163 | 79714251 | 81.0119 | 154.2429 |
| 2025-10-01 | 2 | 34321 | 41478 | 211 | 102077358 | 84030845 | 82.3207 | 162.6588 |
| 2025-11-01 | 2 | 35485 | 39440 | 200 | 97061840 | 87328585 | 89.9721 | 177.4250 |
| 2025-12-01 | 2 | 34523 | 42066 | 209 | 103524426 | 84454137 | 81.5789 | 165.1818 |
| 2026-01-01 | 2 | 38481 | 43360 | 220 | 106708960 | 94273527 | 88.3464 | 174.9136 |
| 2026-02-01 | 2 | 30901 | 34851 | 179 | 85768311 | 76032595 | 88.6488 | 172.6313 |
| 2026-03-01 | 2 | 33529 | 40266 | 208 | 99094626 | 82514869 | 83.2688 | 161.1971 |
| 2026-04-01 | 2 | 30592 | 38521 | 201 | 94800181 | 74846393 | 78.9517 | 152.1990 |
| 2026-05-01 | 2 | 31764 | 38609 | 200 | 95016749 | 77565798 | 81.6338 | 158.8200 |
| 2026-06-01 | 2 | 34350 | 42261 | 216 | 104004321 | 84535350 | 81.2806 | 159.0278 |
| 2026-07-01 | 2 | 36841 | 43049 | 230 | 105943589 | 90665701 | 85.5792 | 160.1783 |
### `GRU -> BEL`
| ROTA_DIRECIONAL | PRIMEIRO_MES | ULTIMO_MES | MESES_COM_REGISTROS | QTD_COMPANHIAS | COMPANHIAS | PASSAGEIROS_PAGOS | ASSENTOS | DECOLAGENS | ASK | RPK |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SBGR>SBBE | 2000-01-01 | 2026-07-01 | 312 | 11 | AZU, BRB, GLO, ONE, PLY, TAM, TBA, TIB, VRG, VRN, VSP | 4549725 | 5499374 | 30417 | 13533959414 | 10684089421 |

Ultimos 12 meses disponiveis:
| PERIODO | COMPANHIAS_NO_MES | PASSAGEIROS_PAGOS | ASSENTOS | DECOLAGENS | ASK | RPK | LOAD_FACTOR_PCT | PASSAGEIROS_POR_DECOLAGEM |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2025-08-01 | 2 | 28536 | 34226 | 198 | 84230186 | 70227096 | 83.3752 | 144.1212 |
| 2025-09-01 | 3 | 31888 | 40178 | 231 | 98878058 | 78176126 | 79.0632 | 138.0433 |
| 2025-10-01 | 2 | 33595 | 41610 | 235 | 102402210 | 82677295 | 80.7378 | 142.9574 |
| 2025-11-01 | 2 | 34166 | 39058 | 217 | 96121738 | 84082526 | 87.4750 | 157.4470 |
| 2025-12-01 | 2 | 37663 | 41935 | 224 | 103202035 | 93067637 | 90.1800 | 168.1384 |
| 2026-01-01 | 2 | 34358 | 43235 | 231 | 106401335 | 84555038 | 79.4680 | 148.7359 |
| 2026-02-01 | 2 | 27961 | 34711 | 196 | 85423771 | 68812021 | 80.5537 | 142.6582 |
| 2026-03-01 | 2 | 32447 | 40380 | 228 | 99375180 | 79852067 | 80.3541 | 142.3114 |
| 2026-04-01 | 2 | 29987 | 38913 | 223 | 95764893 | 73414091 | 76.6608 | 134.4709 |
| 2026-05-01 | 2 | 31335 | 39328 | 222 | 96786208 | 76495263 | 79.0353 | 141.1486 |
| 2026-06-01 | 2 | 34545 | 42415 | 233 | 104383315 | 85015245 | 81.4452 | 148.2618 |
| 2026-07-01 | 2 | 35774 | 42809 | 237 | 105352949 | 88039814 | 83.5665 | 150.9451 |
### `CGH -> SDU`
| ROTA_DIRECIONAL | PRIMEIRO_MES | ULTIMO_MES | MESES_COM_REGISTROS | QTD_COMPANHIAS | COMPANHIAS | PASSAGEIROS_PAGOS | ASSENTOS | DECOLAGENS | ASK | RPK |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SBSP>SBRJ | 2000-01-01 | 2026-07-01 | 319 | 16 | ACN, AZU, BLC, GLO, NES, ONE, PTB, PTN, RSL, TAM, TBA, TIM, VRG, VRN, VSP, WEB | 44905722 | 71353930 | 498158 | 26115538380 | 16442360046 |

Ultimos 12 meses disponiveis:
| PERIODO | COMPANHIAS_NO_MES | PASSAGEIROS_PAGOS | ASSENTOS | DECOLAGENS | ASK | RPK | LOAD_FACTOR_PCT | PASSAGEIROS_POR_DECOLAGEM |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2025-08-01 | 3 | 172108 | 222726 | 1579 | 81517716 | 62991528 | 77.2734 | 108.9981 |
| 2025-09-01 | 3 | 163192 | 212921 | 1502 | 77929086 | 59728272 | 76.6444 | 108.6498 |
| 2025-10-01 | 3 | 179434 | 230772 | 1632 | 84462552 | 65672844 | 77.7538 | 109.9473 |
| 2025-11-01 | 3 | 172626 | 211179 | 1482 | 77291514 | 63124386 | 81.6705 | 116.4818 |
| 2025-12-01 | 3 | 174529 | 200710 | 1413 | 73459860 | 63877614 | 86.9558 | 123.5166 |
| 2026-01-01 | 3 | 148692 | 197675 | 1402 | 72349050 | 54421272 | 75.2204 | 106.0571 |
| 2026-02-01 | 3 | 152324 | 185408 | 1313 | 67859328 | 55750584 | 82.1561 | 116.0122 |
| 2026-03-01 | 3 | 168682 | 223530 | 1600 | 81811980 | 61737612 | 75.4628 | 105.4262 |
| 2026-04-01 | 3 | 157762 | 207340 | 1468 | 75886440 | 57699900 | 76.0345 | 107.4673 |
| 2026-05-01 | 3 | 168366 | 213571 | 1536 | 78166986 | 61621956 | 78.8337 | 109.6133 |
| 2026-06-01 | 3 | 156346 | 199949 | 1437 | 73181334 | 57222636 | 78.1929 | 108.8003 |
| 2026-07-01 | 3 | 155413 | 208788 | 1500 | 76416408 | 56850414 | 74.3956 | 103.6087 |
### `SDU -> CGH`
| ROTA_DIRECIONAL | PRIMEIRO_MES | ULTIMO_MES | MESES_COM_REGISTROS | QTD_COMPANHIAS | COMPANHIAS | PASSAGEIROS_PAGOS | ASSENTOS | DECOLAGENS | ASK | RPK |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SBRJ>SBSP | 2000-01-01 | 2026-07-01 | 319 | 14 | ACN, AZU, BLC, GLO, ONE, PTB, PTN, RSL, TAM, TBA, VRG, VRN, VSP, WEB | 45165266 | 71324119 | 496584 | 26104627554 | 16532788764 |

Ultimos 12 meses disponiveis:
| PERIODO | COMPANHIAS_NO_MES | PASSAGEIROS_PAGOS | ASSENTOS | DECOLAGENS | ASK | RPK | LOAD_FACTOR_PCT | PASSAGEIROS_POR_DECOLAGEM |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2025-08-01 | 3 | 167152 | 227346 | 1576 | 83208636 | 61177632 | 73.5232 | 106.0609 |
| 2025-09-01 | 3 | 164024 | 215964 | 1493 | 79042824 | 60032784 | 75.9497 | 109.8620 |
| 2025-10-01 | 3 | 175843 | 235929 | 1632 | 86350014 | 64358538 | 74.5322 | 107.7469 |
| 2025-11-01 | 3 | 169294 | 213821 | 1478 | 78258486 | 61961604 | 79.1756 | 114.5426 |
| 2025-12-01 | 3 | 153260 | 202465 | 1421 | 74102190 | 56093160 | 75.6970 | 107.8536 |
| 2026-01-01 | 3 | 166271 | 197252 | 1406 | 72194232 | 60855186 | 84.2937 | 118.2582 |
| 2026-02-01 | 3 | 146845 | 186853 | 1314 | 68388198 | 53691102 | 78.5093 | 111.7542 |
| 2026-03-01 | 3 | 165112 | 226757 | 1597 | 82993062 | 60390732 | 72.7660 | 103.3889 |
| 2026-04-01 | 3 | 156925 | 210266 | 1458 | 76957356 | 57377088 | 74.5570 | 107.6303 |
| 2026-05-01 | 3 | 166060 | 217400 | 1532 | 79568400 | 60757830 | 76.3592 | 108.3943 |
| 2026-06-01 | 3 | 156265 | 202378 | 1431 | 74070348 | 57156024 | 77.1645 | 109.1999 |
| 2026-07-01 | 3 | 155703 | 214335 | 1494 | 78446610 | 56987298 | 72.6447 | 104.2189 |
### `GRU -> BSB`
| ROTA_DIRECIONAL | PRIMEIRO_MES | ULTIMO_MES | MESES_COM_REGISTROS | QTD_COMPANHIAS | COMPANHIAS | PASSAGEIROS_PAGOS | ASSENTOS | DECOLAGENS | ASK | RPK |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SBGR>SBBR | 2000-01-01 | 2026-07-01 | 319 | 16 | AZU, BLC, BRB, GLO, IPM, ITB, ONE, PTB, RSL, TAM, TBA, TIB, VRG, VRN, VSP, WEB | 11810314 | 17194757 | 108906 | 14701517235 | 10844407035 |

Ultimos 12 meses disponiveis:
| PERIODO | COMPANHIAS_NO_MES | PASSAGEIROS_PAGOS | ASSENTOS | DECOLAGENS | ASK | RPK | LOAD_FACTOR_PCT | PASSAGEIROS_POR_DECOLAGEM |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2025-08-01 | 2 | 55406 | 69082 | 394 | 59065110 | 47372130 | 80.2032 | 140.6244 |
| 2025-09-01 | 2 | 53840 | 65831 | 374 | 56285505 | 46033200 | 81.7852 | 143.9572 |
| 2025-10-01 | 2 | 57003 | 68241 | 379 | 58346055 | 48555450 | 83.2198 | 150.4037 |
| 2025-11-01 | 2 | 57199 | 66710 | 374 | 57037050 | 49026555 | 85.9556 | 152.9385 |
| 2025-12-01 | 2 | 59027 | 68501 | 379 | 58568355 | 50641650 | 86.4659 | 155.7441 |
| 2026-01-01 | 2 | 56085 | 70097 | 390 | 59932935 | 47818440 | 79.7866 | 143.8077 |
| 2026-02-01 | 2 | 46583 | 59669 | 344 | 51016995 | 39828465 | 78.0690 | 135.4157 |
| 2026-03-01 | 2 | 49545 | 64317 | 366 | 54991035 | 42746580 | 77.7337 | 135.3689 |
| 2026-04-01 | 2 | 48154 | 61997 | 344 | 53007435 | 41171670 | 77.6715 | 139.9826 |
| 2026-05-01 | 2 | 47485 | 58434 | 329 | 49961070 | 40951935 | 81.9677 | 144.3313 |
| 2026-06-01 | 2 | 49184 | 59832 | 334 | 51156360 | 42343875 | 82.7734 | 147.2575 |
| 2026-07-01 | 2 | 47921 | 57398 | 332 | 49075290 | 40972455 | 83.4890 | 144.3404 |
### `BSB -> GRU`
| ROTA_DIRECIONAL | PRIMEIRO_MES | ULTIMO_MES | MESES_COM_REGISTROS | QTD_COMPANHIAS | COMPANHIAS | PASSAGEIROS_PAGOS | ASSENTOS | DECOLAGENS | ASK | RPK |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SBBR>SBGR | 2000-01-01 | 2026-07-01 | 319 | 17 | AZU, BLC, BRB, GLO, IPM, ITB, NES, ONE, PTB, RSL, TAM, TBA, TIB, VRG, VRN, VSP, WEB | 11942600 | 17225476 | 107249 | 14727781980 | 10862918640 |

Ultimos 12 meses disponiveis:
| PERIODO | COMPANHIAS_NO_MES | PASSAGEIROS_PAGOS | ASSENTOS | DECOLAGENS | ASK | RPK | LOAD_FACTOR_PCT | PASSAGEIROS_POR_DECOLAGEM |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2025-08-01 | 2 | 56748 | 68647 | 390 | 58693185 | 48807675 | 83.1573 | 145.5077 |
| 2025-09-01 | 2 | 54557 | 64404 | 372 | 55065420 | 46646235 | 84.7106 | 146.6586 |
| 2025-10-01 | 3 | 57113 | 66082 | 375 | 56500110 | 48713625 | 86.2186 | 152.3013 |
| 2025-11-01 | 2 | 56804 | 67222 | 374 | 57474810 | 48567420 | 84.5021 | 151.8824 |
| 2025-12-01 | 3 | 60488 | 68350 | 373 | 58439250 | 51567615 | 88.2414 | 162.1662 |
| 2026-01-01 | 2 | 54272 | 69185 | 381 | 59153175 | 45992160 | 77.7510 | 142.4462 |
| 2026-02-01 | 2 | 49023 | 60196 | 341 | 51467580 | 41590620 | 80.8094 | 143.7625 |
| 2026-03-01 | 2 | 49755 | 64341 | 364 | 55011555 | 42639705 | 77.5105 | 136.6896 |
| 2026-04-01 | 2 | 49475 | 62260 | 348 | 53232300 | 42301125 | 79.4651 | 142.1695 |
| 2026-05-01 | 3 | 48036 | 59050 | 331 | 50487750 | 41553000 | 82.3031 | 145.1239 |
| 2026-06-01 | 2 | 46558 | 58690 | 325 | 50179950 | 39807090 | 79.3287 | 143.2554 |
| 2026-07-01 | 2 | 49649 | 58225 | 331 | 49782375 | 42449895 | 85.2709 | 149.9970 |
### `BEL -> MAO`
| ROTA_DIRECIONAL | PRIMEIRO_MES | ULTIMO_MES | MESES_COM_REGISTROS | QTD_COMPANHIAS | COMPANHIAS | PASSAGEIROS_PAGOS | ASSENTOS | DECOLAGENS | ASK | RPK |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SBBE>SBEG | 2000-01-01 | 2026-07-01 | 318 | 15 | AZU, BRB, GLO, MSQ, NES, PAM, RLE, TAM, TBA, TIB, TSD, TTL, TVJ, VRG, VSP | 2724296 | 4665340 | 32837 | 6060276660 | 4337940354 |

Ultimos 12 meses disponiveis:
| PERIODO | COMPANHIAS_NO_MES | PASSAGEIROS_PAGOS | ASSENTOS | DECOLAGENS | ASK | RPK | LOAD_FACTOR_PCT | PASSAGEIROS_POR_DECOLAGEM |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2025-08-01 | 3 | 9692 | 11696 | 89 | 15193104 | 12589908 | 82.8659 | 108.8989 |
| 2025-09-01 | 3 | 9672 | 12774 | 96 | 16593426 | 12563928 | 75.7163 | 100.7500 |
| 2025-10-01 | 3 | 9549 | 13599 | 103 | 17665101 | 12404151 | 70.2184 | 92.7087 |
| 2025-11-01 | 3 | 9467 | 12415 | 87 | 16127085 | 12297633 | 76.2545 | 108.8161 |
| 2025-12-01 | 3 | 8901 | 12326 | 83 | 16011474 | 11562399 | 72.2132 | 107.2410 |
| 2026-01-01 | 3 | 11067 | 12578 | 79 | 16338822 | 14376033 | 87.9870 | 140.0886 |
| 2026-02-01 | 3 | 9470 | 11404 | 78 | 14813796 | 12301530 | 83.0410 | 121.4103 |
| 2026-03-01 | 3 | 9087 | 12225 | 88 | 15880275 | 11804013 | 74.3313 | 103.2614 |
| 2026-04-01 | 3 | 7217 | 11314 | 82 | 14696886 | 9374883 | 63.7882 | 88.0122 |
| 2026-05-01 | 3 | 8432 | 12289 | 87 | 15963411 | 10953168 | 68.6142 | 96.9195 |
| 2026-06-01 | 3 | 7822 | 11172 | 82 | 14512428 | 10160778 | 70.0143 | 95.3902 |
| 2026-07-01 | 3 | 9507 | 12243 | 85 | 15903657 | 12349593 | 77.6525 | 111.8471 |
### `MAO -> BEL`
| ROTA_DIRECIONAL | PRIMEIRO_MES | ULTIMO_MES | MESES_COM_REGISTROS | QTD_COMPANHIAS | COMPANHIAS | PASSAGEIROS_PAGOS | ASSENTOS | DECOLAGENS | ASK | RPK |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SBEG>SBBE | 2000-01-01 | 2026-07-01 | 318 | 15 | AZU, BRB, GLO, MSQ, NES, PAM, RLE, TAM, TBA, TIB, TSD, TTL, TVJ, VRG, VSP | 2707095 | 4645884 | 30849 | 6035003316 | 4294939557 |

Ultimos 12 meses disponiveis:
| PERIODO | COMPANHIAS_NO_MES | PASSAGEIROS_PAGOS | ASSENTOS | DECOLAGENS | ASK | RPK | LOAD_FACTOR_PCT | PASSAGEIROS_POR_DECOLAGEM |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2025-08-01 | 2 | 11147 | 12106 | 69 | 15725694 | 14479953 | 92.0783 | 161.5507 |
| 2025-09-01 | 2 | 10325 | 11733 | 67 | 15241167 | 13412175 | 87.9997 | 154.1045 |
| 2025-10-01 | 2 | 10183 | 12180 | 70 | 15821820 | 13227717 | 83.6043 | 145.4714 |
| 2025-11-01 | 2 | 9911 | 12179 | 68 | 15820521 | 12874389 | 81.3778 | 145.7500 |
| 2025-12-01 | 2 | 11504 | 12040 | 68 | 15639960 | 14943696 | 95.5482 | 169.1765 |
| 2026-01-01 | 2 | 11169 | 12684 | 72 | 16476516 | 14508531 | 88.0558 | 155.1250 |
| 2026-02-01 | 2 | 8499 | 11228 | 64 | 14585172 | 11040201 | 75.6947 | 132.7969 |
| 2026-03-01 | 2 | 9559 | 12359 | 71 | 16054341 | 12417141 | 77.3444 | 134.6338 |
| 2026-04-01 | 3 | 7522 | 10810 | 62 | 14042190 | 9771078 | 69.5837 | 121.3226 |
| 2026-05-01 | 2 | 9166 | 12051 | 68 | 15654249 | 11906634 | 76.0601 | 134.7941 |
| 2026-06-01 | 2 | 9415 | 11441 | 65 | 14861859 | 12230085 | 82.2918 | 144.8462 |
| 2026-07-01 | 2 | 9777 | 12011 | 69 | 15602289 | 12700323 | 81.4004 | 141.6957 |


## Ida e volta

As chaves usam origem e destino em ordem. Portanto, `SBBE>SBGR` e `SBGR>SBBE` sao distintas, assim como todas as demais duplas testadas. Os totais dos ultimos 12 meses disponiveis confirmam que as metricas podem divergir por sentido:

| ROTA_IATA | PASSAGEIROS_PAGOS | ASSENTOS | DECOLAGENS | ASK | RPK | LOAD_FACTOR_PCT | PASSAGEIROS_POR_DECOLAGEM |
| --- | --- | --- | --- | --- | --- | --- | --- |
| BEL>GRU | 403788 | 478137 | 2460 | 1176695157 | 991293261 | 84.2438 | 164.1415 |
| GRU>BEL | 392255 | 478798 | 2675 | 1178321878 | 964414219 | 81.8464 | 146.6374 |
| CGH>SDU | 1969474 | 2514569 | 17864 | 920332254 | 720699018 | 78.3086 | 110.2482 |
| SDU>CGH | 1942754 | 2550766 | 17832 | 933580356 | 710838978 | 76.1412 | 108.9476 |
| GRU>BSB | 627432 | 770109 | 4339 | 658443195 | 537462405 | 81.6262 | 144.6029 |
| BSB>GRU | 632478 | 766652 | 4305 | 655487460 | 540636165 | 82.4785 | 146.9171 |
| BEL>MAO | 109883 | 146035 | 1039 | 189699465 | 142738017 | 75.2443 | 105.7584 |
| MAO>BEL | 118177 | 142822 | 813 | 185525778 | 153511923 | 82.7443 | 145.3592 |

Nao foi criada rota nao direcional.

## Calculo de indicadores

- `LOAD_FACTOR_PCT = SUM(RPK) / SUM(ASK) * 100`. O resultado e nulo quando `ASK` e nulo ou menor/igual a zero.
- `PASSAGEIROS_POR_DECOLAGEM = SUM(PASSAGEIROS_PAGOS) / SUM(DECOLAGENS)`. O resultado e nulo quando `DECOLAGENS` e nulo ou menor/igual a zero.
- Nenhuma media simples de percentuais foi usada.

Exemplo mais recente da rota `BEL>GRU` em `2026-07-01`: `RPK = 90665701`, `ASK = 105943589` e `LOAD_FACTOR_PCT = 85.5792%`. Passageiros pagos por decolagem: `160.1783`.

## Market share e HHI

Foi escolhida automaticamente, entre as rotas de teste, a rota com maior volume e mais de uma companhia no ultimo ano completo: `CGH>SDU`, ano `2025`.

| EMPRESA_SIGLA | EMPRESA_NOME | PASSAGEIROS_PAGOS | MARKET_SHARE_PCT |
| --- | --- | --- | --- |
| GLO | GOL LINHAS AÉREAS S.A. (EX- VRG LINHAS AÉREAS S.A.) | 902204 | 45.8359 |
| TAM | TAM LINHAS AÉREAS S.A. | 774426 | 39.3442 |
| AZU | AZUL LINHAS AÉREAS BRASILEIRAS S/A | 291704 | 14.8198 |

- Soma dos market shares: `100.00000000%`.
- HHI em escala 0-100: `3868.5283`.

O HHI foi calculado como a soma dos quadrados dos shares. Nenhuma classificacao concorrencial foi aplicada.

## Anos completos e parciais

| ANO | MESES_DISPONIVEIS | PRIMEIRO_MES_DISPONIVEL | ULTIMO_MES_DISPONIVEL | ANO_COMPLETO | ANO_PARCIAL |
| --- | --- | --- | --- | --- | --- |
| 2000 | 12 | 1 | 12 | True | False |
| 2001 | 12 | 1 | 12 | True | False |
| 2002 | 12 | 1 | 12 | True | False |
| 2003 | 12 | 1 | 12 | True | False |
| 2004 | 12 | 1 | 12 | True | False |
| 2005 | 12 | 1 | 12 | True | False |
| 2006 | 12 | 1 | 12 | True | False |
| 2007 | 12 | 1 | 12 | True | False |
| 2008 | 12 | 1 | 12 | True | False |
| 2009 | 12 | 1 | 12 | True | False |
| 2010 | 12 | 1 | 12 | True | False |
| 2011 | 12 | 1 | 12 | True | False |
| 2012 | 12 | 1 | 12 | True | False |
| 2013 | 12 | 1 | 12 | True | False |
| 2014 | 12 | 1 | 12 | True | False |
| 2015 | 12 | 1 | 12 | True | False |
| 2016 | 12 | 1 | 12 | True | False |
| 2017 | 12 | 1 | 12 | True | False |
| 2018 | 12 | 1 | 12 | True | False |
| 2019 | 12 | 1 | 12 | True | False |
| 2020 | 12 | 1 | 12 | True | False |
| 2021 | 12 | 1 | 12 | True | False |
| 2022 | 12 | 1 | 12 | True | False |
| 2023 | 12 | 1 | 12 | True | False |
| 2024 | 12 | 1 | 12 | True | False |
| 2025 | 12 | 1 | 12 | True | False |
| 2026 | 7 | 1 | 7 | False | True |

Regra: um ano e completo somente quando contem os 12 meses de janeiro a dezembro. O ultimo ano disponivel e `2026`, com dados ate o mes `7`, e deve ser tratado como parcial. Uma comparacao com `2025` deve usar janeiro a mes `7` nos dois anos. Totais anuais completos nunca devem ser comparados diretamente com esse acumulado parcial.

Exemplo YTD do universo recomendado, janeiro a mes `7`: `2025` teve `55664808` passageiros pagos e `2026` teve `58343401`. A variacao calculada sobre periodos equivalentes e `4.8120%`.

## Anomalias no candidato domestico

Os controles abaixo sao calculados antes de retirar origem igual a destino, para que esses casos permaneçam visiveis na validacao:

| ANOMALIA | CASOS | PRIMEIRO_PERIODO | ULTIMO_PERIODO | COMPANHIAS | ROTAS |
| --- | --- | --- | --- | --- | --- |
| RPK_MAIOR_ASK | 1254 | 2000-01-01 | 2018-11-01 | 22 | 356 |
| PASSAGEIROS_MAIOR_ASSENTOS | 15164 | 2000-01-01 | 2026-04-01 | 36 | 1123 |
| ORIGEM_IGUAL_DESTINO | 2229 | 2000-01-01 | 2026-07-01 | 34 | 102 |
| CODIGO_AEROPORTO_AUSENTE | 0 |  |  | 0 | 0 |
| ASK_ZERO_RPK_POSITIVO | 29 | 2004-12-01 | 2018-11-01 | 6 | 28 |
| DECOLAGENS_ZERO_PASSAGEIROS_POSITIVOS | 0 |  |  | 0 | 0 |
| ASSENTOS_ZERO_PASSAGEIROS_POSITIVOS | 526 | 2000-01-01 | 2025-11-01 | 12 | 120 |

Anos com maior concentracao:

| ANOMALIA | ANO | CASOS |
| --- | --- | --- |
| RPK_MAIOR_ASK | 2008 | 332 |
| RPK_MAIOR_ASK | 2009 | 277 |
| RPK_MAIOR_ASK | 2006 | 227 |
| RPK_MAIOR_ASK | 2005 | 133 |
| RPK_MAIOR_ASK | 2007 | 130 |
| PASSAGEIROS_MAIOR_ASSENTOS | 2000 | 1227 |
| PASSAGEIROS_MAIOR_ASSENTOS | 2011 | 1060 |
| PASSAGEIROS_MAIOR_ASSENTOS | 2001 | 1047 |
| PASSAGEIROS_MAIOR_ASSENTOS | 2002 | 1042 |
| PASSAGEIROS_MAIOR_ASSENTOS | 2012 | 1020 |
| ORIGEM_IGUAL_DESTINO | 2007 | 204 |
| ORIGEM_IGUAL_DESTINO | 2010 | 172 |
| ORIGEM_IGUAL_DESTINO | 2008 | 160 |
| ORIGEM_IGUAL_DESTINO | 2000 | 147 |
| ORIGEM_IGUAL_DESTINO | 2006 | 141 |
| ASK_ZERO_RPK_POSITIVO | 2013 | 9 |
| ASK_ZERO_RPK_POSITIVO | 2018 | 6 |
| ASK_ZERO_RPK_POSITIVO | 2017 | 4 |
| ASK_ZERO_RPK_POSITIVO | 2010 | 3 |
| ASK_ZERO_RPK_POSITIVO | 2009 | 2 |
| ASSENTOS_ZERO_PASSAGEIROS_POSITIVOS | 2000 | 118 |
| ASSENTOS_ZERO_PASSAGEIROS_POSITIVOS | 2002 | 115 |
| ASSENTOS_ZERO_PASSAGEIROS_POSITIVOS | 2001 | 96 |
| ASSENTOS_ZERO_PASSAGEIROS_POSITIVOS | 2004 | 64 |
| ASSENTOS_ZERO_PASSAGEIROS_POSITIVOS | 2003 | 60 |

Tratamento recomendado:

- `RPK_MAIOR_ASK`: os casos domesticos vao de 2000 a 2018 e se concentram em 2005-2009, indicando forte componente historico. Sinalizar. O Load Factor pode superar 100%, mas nao deve ser truncado. A ressalva da ANAC sobre desagregacao por rota de empresas estrangeiras explica parte do problema no universo internacional, mas nao explica sozinha os casos domesticos.
- `PASSAGEIROS_MAIOR_ASSENTOS`: ocorre desde 2000 e ainda aparece em 2026, portanto nao e apenas legado historico. Sinalizar e impedir qualquer indicador que use passageiros/assentos como taxa de ocupacao. Nao excluir automaticamente passageiros de market share sem validacao adicional.
- `ORIGEM_IGUAL_DESTINO`: persiste ate 2026. Pode refletir etapas especiais ou registros operacionais, mas nao representa um mercado origem-destino. Preservar na base principal e excluir do universo de mercado pela `FLAG_ROTA_OD_VALIDA`.
- `CODIGO_AEROPORTO_AUSENTE`: preservar e sinalizar; nao construir chave de rota nem usar em metricas por mercado.
- `ASK_ZERO_RPK_POSITIVO`: os casos terminam em 2018 e parecem uma inconsistencia historica. Manter o registro, sinalizar e retornar Load Factor nulo.
- `DECOLAGENS_ZERO_PASSAGEIROS_POSITIVOS`: manter e retornar passageiros por decolagem nulo.
- `ASSENTOS_ZERO_PASSAGEIROS_POSITIVOS`: ainda ocorre em 2025, portanto nao deve ser tratado apenas como problema historico. Sinalizar e nao usar em indicadores baseados em assentos.

## Artefato de validacao

`data/processed/avscope_mvp_validation.parquet` contem apenas as oito rotas de teste, agregadas por mes no universo recomendado. Ele inclui as somas, indicadores com divisao segura e flags de ano completo/parcial. Nao substitui a base principal.

## Recomendacoes antes do app

1. Substituir, na proxima versao metodologica, o uso direto de `FLAG_UNIVERSO_MVP` pela regra historica e geografica validada nesta etapa.
2. Manter `NATUREZA` e a classificacao geografica separadas, pois medem conceitos diferentes.
3. Criar uma dimensao aeroportuaria oficial OACI-IATA antes da interface; nao derivar IATA por manipulacao de texto.
4. Aplicar `FLAG_ROTA_OD_VALIDA` nas telas de mercado e manter as anomalias disponiveis para auditoria.
5. Centralizar Load Factor, passageiros por decolagem, market share, HHI e comparacao YTD no modulo oficial de metricas da Etapa 4.

