# Auditoria exploratoria do dataset ANAC

Gerado em: `2026-09-14T10:37:38`

Arquivo auditado: `data\raw\Dados_Estatisticos.csv`

## Sumario executivo

- O arquivo original nao foi alterado durante a auditoria: `True`.
- Tamanho: `358893852` bytes (342,27 MB).
- Encoding detectado: `utf-8-sig` (BOM UTF-8 detectado no inicio do arquivo, confianca `1.0`).
- Separador detectado: `;`.
- Linha de cabecalho real: `2`; existem `1` linha(s) de metadados antes do cabecalho.
- Quantidade de colunas: `38`.
- Quantidade exata de linhas de dados via Polars: `1096554`.
- Estimativa por contagem de quebras de linha: `1096554`.
- Duplicidades estimadas por hash da linha completa: `0`.
- Linhas com pelo menos um campo ausente/vazio: `482115`.
- Caracter de substituicao Unicode (`�`) encontrado: `0` ocorrencia(s).

## Deteccao automatica

```json
{
  "arquivo": "data\\raw\\Dados_Estatisticos.csv",
  "tamanho_bytes": 358893852,
  "linhas_dados": 1096554,
  "colunas": 38,
  "encoding": {
    "encoding": "utf-8-sig",
    "source": "BOM UTF-8 detectado no inicio do arquivo",
    "confidence": 1.0
  },
  "separador": ";",
  "hash_sha256_inicial": "270b815c5ded4a254aea3a2f8ebd731e53a2cb8eeb9f1689d013ddb6eda4ec92",
  "hash_sha256_final": "270b815c5ded4a254aea3a2f8ebd731e53a2cb8eeb9f1689d013ddb6eda4ec92",
  "hash_preservado": true
}
```

Contagem de separadores na linha de cabecalho candidata:

```json
{
  ";": 37,
  ",": 0,
  "\t": 0,
  "|": 0
}
```

## Colunas reais

| ordem | coluna |
| --- | --- |
| 1 | EMPRESA_SIGLA |
| 2 | EMPRESA_NOME |
| 3 | EMPRESA_NACIONALIDADE |
| 4 | ANO |
| 5 | MES |
| 6 | AEROPORTO_DE_ORIGEM_SIGLA |
| 7 | AEROPORTO_DE_ORIGEM_NOME |
| 8 | AEROPORTO_DE_ORIGEM_UF |
| 9 | AEROPORTO_DE_ORIGEM_REGIAO |
| 10 | AEROPORTO_DE_ORIGEM_PAIS |
| 11 | AEROPORTO_DE_ORIGEM_CONTINENTE |
| 12 | AEROPORTO_DE_DESTINO_SIGLA |
| 13 | AEROPORTO_DE_DESTINO_NOME |
| 14 | AEROPORTO_DE_DESTINO_UF |
| 15 | AEROPORTO_DE_DESTINO_REGIAO |
| 16 | AEROPORTO_DE_DESTINO_PAIS |
| 17 | AEROPORTO_DE_DESTINO_CONTINENTE |
| 18 | NATUREZA |
| 19 | GRUPO_DE_VOO |
| 20 | PASSAGEIROS_PAGOS |
| 21 | PASSAGEIROS_GRATIS |
| 22 | CARGA_PAGA_KG |
| 23 | CARGA_GRATIS_KG |
| 24 | CORREIO_KG |
| 25 | ASK |
| 26 | RPK |
| 27 | ATK |
| 28 | RTK |
| 29 | COMBUSTIVEL_LITROS |
| 30 | DISTANCIA_VOADA_KM |
| 31 | DECOLAGENS |
| 32 | CARGA_PAGA_KM |
| 33 | CARGA_GRATIS_KM |
| 34 | CORREIO_KM |
| 35 | ASSENTOS |
| 36 | PAYLOAD |
| 37 | HORAS_VOADAS |
| 38 | BAGAGEM_KG |

## Tipos inferidos pelo Polars

| coluna | tipo_inferido_polars |
| --- | --- |
| EMPRESA_SIGLA | String |
| EMPRESA_NOME | String |
| EMPRESA_NACIONALIDADE | String |
| ANO | Int64 |
| MES | Int64 |
| AEROPORTO_DE_ORIGEM_SIGLA | String |
| AEROPORTO_DE_ORIGEM_NOME | String |
| AEROPORTO_DE_ORIGEM_UF | String |
| AEROPORTO_DE_ORIGEM_REGIAO | String |
| AEROPORTO_DE_ORIGEM_PAIS | String |
| AEROPORTO_DE_ORIGEM_CONTINENTE | String |
| AEROPORTO_DE_DESTINO_SIGLA | String |
| AEROPORTO_DE_DESTINO_NOME | String |
| AEROPORTO_DE_DESTINO_UF | String |
| AEROPORTO_DE_DESTINO_REGIAO | String |
| AEROPORTO_DE_DESTINO_PAIS | String |
| AEROPORTO_DE_DESTINO_CONTINENTE | String |
| NATUREZA | String |
| GRUPO_DE_VOO | String |
| PASSAGEIROS_PAGOS | Int64 |
| PASSAGEIROS_GRATIS | Int64 |
| CARGA_PAGA_KG | Int64 |
| CARGA_GRATIS_KG | Int64 |
| CORREIO_KG | Int64 |
| ASK | Int64 |
| RPK | Int64 |
| ATK | Int64 |
| RTK | Int64 |
| COMBUSTIVEL_LITROS | Int64 |
| DISTANCIA_VOADA_KM | Int64 |
| DECOLAGENS | Int64 |
| CARGA_PAGA_KM | Int64 |
| CARGA_GRATIS_KM | Int64 |
| CORREIO_KM | Int64 |
| ASSENTOS | Int64 |
| PAYLOAD | Int64 |
| HORAS_VOADAS | String |
| BAGAGEM_KG | Int64 |

## Primeiras 5 linhas

| EMPRESA_SIGLA | EMPRESA_NOME | EMPRESA_NACIONALIDADE | ANO | MES | AEROPORTO_DE_ORIGEM_SIGLA | AEROPORTO_DE_ORIGEM_NOME | AEROPORTO_DE_ORIGEM_UF | AEROPORTO_DE_ORIGEM_REGIAO | AEROPORTO_DE_ORIGEM_PAIS | AEROPORTO_DE_ORIGEM_CONTINENTE | AEROPORTO_DE_DESTINO_SIGLA | AEROPORTO_DE_DESTINO_NOME | AEROPORTO_DE_DESTINO_UF | AEROPORTO_DE_DESTINO_REGIAO | AEROPORTO_DE_DESTINO_PAIS | AEROPORTO_DE_DESTINO_CONTINENTE | NATUREZA | GRUPO_DE_VOO | PASSAGEIROS_PAGOS | PASSAGEIROS_GRATIS | CARGA_PAGA_KG | CARGA_GRATIS_KG | CORREIO_KG | ASK | RPK | ATK | RTK | COMBUSTIVEL_LITROS | DISTANCIA_VOADA_KM | DECOLAGENS | CARGA_PAGA_KM | CARGA_GRATIS_KM | CORREIO_KM | ASSENTOS | PAYLOAD | HORAS_VOADAS | BAGAGEM_KG |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AAL | AMERICAN AIRLINES, INC. | ESTRANGEIRA | 2000 | 1 |  |  |  |  |  |  | KMIA | MIAMI, FLORIDA |  |  | ESTADOS UNIDOS DA AMÉRICA | AMÉRICA DO NORTE | INTERNACIONAL | REGULAR | 152 | 9 | 2285 | 0 | 0 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| AAL | AMERICAN AIRLINES, INC. | ESTRANGEIRA | 2000 | 1 | KDFW | DALLAS & FORT WORTH, TEXAS |  |  | ESTADOS UNIDOS DA AMÉRICA | AMÉRICA DO NORTE | SBGR | GUARULHOS | SP | SUDESTE | BRASIL | AMÉRICA DO SUL | INTERNACIONAL | REGULAR | 3932 | 142 | 97876 | 0 | 73 | 52184520 | 32415408 | 8656200 | 3724861 |  | 247320 | 30 | 806889736 | 0 | 601812 | 6330 | 1050000 | 409,08 |  |
| AAL | AMERICAN AIRLINES, INC. | ESTRANGEIRA | 2000 | 1 | KJFK | NEW YORK, NEW YORK |  |  | ESTADOS UNIDOS DA AMÉRICA | AMÉRICA DO NORTE | SBGL | RIO DE JANEIRO | RJ | SUDESTE | BRASIL | AMÉRICA DO SUL | INTERNACIONAL | REGULAR | 2338 | 131 | 48066 | 0 | 8034 | 47293751 | 18070402 | 3586256 | 2059920 |  | 224141 | 29 | 371502116 | 0 | 62094786 | 6119 | 464000 | 418,1 |  |
| AAL | AMERICAN AIRLINES, INC. | ESTRANGEIRA | 2000 | 1 | KJFK | NEW YORK, NEW YORK |  |  | ESTADOS UNIDOS DA AMÉRICA | AMÉRICA DO NORTE | SBGR | GUARULHOS | SP | SUDESTE | BRASIL | AMÉRICA DO SUL | INTERNACIONAL | REGULAR | 2892 | 127 | 194997 | 0 | 1980 | 46896016 | 22164288 | 7778960 | 3504404 |  | 222256 | 29 | 1494457008 | 0 | 15174720 | 6119 | 1015000 | 411,5 |  |
| AAL | AMERICAN AIRLINES, INC. | ESTRANGEIRA | 2000 | 1 | KMIA | MIAMI, FLORIDA |  |  | ESTADOS UNIDOS DA AMÉRICA | AMÉRICA DO NORTE | SBCF | CONFINS | MG | SUDESTE | BRASIL | AMÉRICA DO SUL | INTERNACIONAL | REGULAR | 997 | 20 | 91022 | 493 | 0 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |

## Valores ausentes por coluna

| coluna | ausentes | nao_ausentes | pct_ausente |
| --- | --- | --- | --- |
| EMPRESA_SIGLA | 0 | 1096554 | 0.0 |
| EMPRESA_NOME | 0 | 1096554 | 0.0 |
| EMPRESA_NACIONALIDADE | 0 | 1096554 | 0.0 |
| ANO | 0 | 1096554 | 0.0 |
| MES | 0 | 1096554 | 0.0 |
| AEROPORTO_DE_ORIGEM_SIGLA | 5212 | 1091342 | 0.4753 |
| AEROPORTO_DE_ORIGEM_NOME | 5212 | 1091342 | 0.4753 |
| AEROPORTO_DE_ORIGEM_UF | 166370 | 930184 | 15.1721 |
| AEROPORTO_DE_ORIGEM_REGIAO | 166370 | 930184 | 15.1721 |
| AEROPORTO_DE_ORIGEM_PAIS | 5212 | 1091342 | 0.4753 |
| AEROPORTO_DE_ORIGEM_CONTINENTE | 5212 | 1091342 | 0.4753 |
| AEROPORTO_DE_DESTINO_SIGLA | 0 | 1096554 | 0.0 |
| AEROPORTO_DE_DESTINO_NOME | 0 | 1096554 | 0.0 |
| AEROPORTO_DE_DESTINO_UF | 169917 | 926637 | 15.4955 |
| AEROPORTO_DE_DESTINO_REGIAO | 169917 | 926637 | 15.4955 |
| AEROPORTO_DE_DESTINO_PAIS | 0 | 1096554 | 0.0 |
| AEROPORTO_DE_DESTINO_CONTINENTE | 0 | 1096554 | 0.0 |
| NATUREZA | 0 | 1096554 | 0.0 |
| GRUPO_DE_VOO | 2 | 1096552 | 0.0002 |
| PASSAGEIROS_PAGOS | 40353 | 1056201 | 3.68 |
| PASSAGEIROS_GRATIS | 40353 | 1056201 | 3.68 |
| CARGA_PAGA_KG | 40353 | 1056201 | 3.68 |
| CARGA_GRATIS_KG | 40353 | 1056201 | 3.68 |
| CORREIO_KG | 40353 | 1056201 | 3.68 |
| ASK | 238521 | 858033 | 21.7519 |
| RPK | 238008 | 858546 | 21.7051 |
| ATK | 238521 | 858033 | 21.7519 |
| RTK | 238533 | 858021 | 21.753 |
| COMBUSTIVEL_LITROS | 331625 | 764929 | 30.2425 |
| DISTANCIA_VOADA_KM | 238520 | 858034 | 21.7518 |
| DECOLAGENS | 237940 | 858614 | 21.6989 |
| CARGA_PAGA_KM | 238008 | 858546 | 21.7051 |
| CARGA_GRATIS_KM | 238533 | 858021 | 21.753 |
| CORREIO_KM | 238008 | 858546 | 21.7051 |
| ASSENTOS | 237941 | 858613 | 21.699 |
| PAYLOAD | 237941 | 858613 | 21.699 |
| HORAS_VOADAS | 238458 | 858096 | 21.7461 |
| BAGAGEM_KG | 172644 | 923910 | 15.7442 |

## Periodo, empresas e aeroportos

- Ano: coluna `ANO`, menor `2000`, maior `2026`.
- Meses disponiveis pela coluna `MES`: `1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12`.
- Empresas: `325` valores distintos em `EMPRESA_SIGLA`.
- Aeroportos de origem: `1107` valores distintos em `AEROPORTO_DE_ORIGEM_SIGLA`.
- Aeroportos de destino: `1129` valores distintos em `AEROPORTO_DE_DESTINO_SIGLA`.

## Variaveis localizadas para metricas e dimensoes solicitadas

| variavel | colunas_reais_localizadas |
| --- | --- |
| passageiros_pagos | PASSAGEIROS_PAGOS |
| assentos | ASSENTOS |
| decolagens | DECOLAGENS |
| ask | ASK |
| rpk | RPK |
| empresa_aerea | EMPRESA_SIGLA, EMPRESA_NOME, EMPRESA_NACIONALIDADE |
| aeroporto_origem | AEROPORTO_DE_ORIGEM_SIGLA, AEROPORTO_DE_ORIGEM_NOME, AEROPORTO_DE_ORIGEM_UF, AEROPORTO_DE_ORIGEM_REGIAO, AEROPORTO_DE_ORIGEM_PAIS, AEROPORTO_DE_ORIGEM_CONTINENTE |
| aeroporto_destino | AEROPORTO_DE_DESTINO_SIGLA, AEROPORTO_DE_DESTINO_NOME, AEROPORTO_DE_DESTINO_UF, AEROPORTO_DE_DESTINO_REGIAO, AEROPORTO_DE_DESTINO_PAIS, AEROPORTO_DE_DESTINO_CONTINENTE |
| ano | ANO |
| mes | MES |

## Natureza da operacao e grupo/tipo de voo

Colunas candidatas identificadas sem presumir nomes: `NATUREZA, GRUPO_DE_VOO`.

### `NATUREZA`

- `DOMÉSTICA`
- `INTERNACIONAL`

### `GRUPO_DE_VOO`

- `IMPRODUTIVO`
- `NÃO IDENTIFICADO`
- `NÃO REGULAR`
- `REGULAR`

## Perfil numerico e problemas potenciais

Colunas com valores parseaveis como numero (normalizando virgula decimal quando presente):

| coluna | tipo_inferido | nao_ausentes | parseaveis_como_numero | pct_parseavel | negativos | min_parseado | max_parseado |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ANO | Int64 | 1096554 | 1096554 | 100.0 | 0 | 2000.0 | 2026.0 |
| MES | Int64 | 1096554 | 1096554 | 100.0 | 0 | 1.0 | 12.0 |
| PASSAGEIROS_PAGOS | Int64 | 1056201 | 1056201 | 100.0 | 0 | 0.0 | 92357.0 |
| PASSAGEIROS_GRATIS | Int64 | 1056201 | 1056201 | 100.0 | 0 | 0.0 | 7452.0 |
| CARGA_PAGA_KG | Int64 | 1056201 | 1056201 | 100.0 | 0 | 0.0 | 4339325.0 |
| CARGA_GRATIS_KG | Int64 | 1056201 | 1056201 | 100.0 | 0 | 0.0 | 198228.0 |
| CORREIO_KG | Int64 | 1056201 | 1056201 | 100.0 | 0 | 0.0 | 825678.0 |
| ASK | Int64 | 858033 | 858033 | 100.0 | 0 | 0.0 | 340016292.0 |
| RPK | Int64 | 858546 | 858546 | 100.0 | 0 | 0.0 | 293260198.0 |
| ATK | Int64 | 858033 | 858033 | 100.0 | 0 | 0.0 | 66562456.0 |
| RTK | Int64 | 858021 | 858021 | 100.0 | 0 | 0.0 | 35016679.0 |
| COMBUSTIVEL_LITROS | Int64 | 764929 | 764929 | 100.0 | 27 | -197121.0 | 6704640.0 |
| DISTANCIA_VOADA_KM | Int64 | 858034 | 858034 | 100.0 | 0 | 0.0 | 1043504.0 |
| DECOLAGENS | Int64 | 858614 | 858614 | 100.0 | 0 | 0.0 | 918.0 |
| CARGA_PAGA_KM | Int64 | 858546 | 858546 | 100.0 | 0 | 0.0 | 28526722432.0 |
| CARGA_GRATIS_KM | Int64 | 858021 | 858021 | 100.0 | 0 | 0.0 | 1475411008.0 |
| CORREIO_KM | Int64 | 858546 | 858546 | 100.0 | 0 | 0.0 | 2750414320.0 |
| ASSENTOS | Int64 | 858613 | 858613 | 100.0 | 0 | 0.0 | 154845.0 |
| PAYLOAD | Int64 | 858613 | 858613 | 100.0 | 0 | 0.0 | 23196480.0 |
| HORAS_VOADAS | String | 858096 | 858096 | 100.0 | 0 | 0.0 | 8765.0 |
| BAGAGEM_KG | Int64 | 923910 | 923910 | 100.0 | 0 | 0.0 | 919417.0 |

Colunas possivelmente numericas armazenadas como texto:

| coluna | tipo_inferido | nao_ausentes | parseaveis_como_numero | pct_parseavel |
| --- | --- | --- | --- | --- |
| HORAS_VOADAS | String | 858096 | 858096 | 100.0 |

Sinais de separador decimal/milhar nas colunas numericas:

| coluna | com_virgula | com_ponto |
| --- | --- | --- |
| HORAS_VOADAS | 837037 | 0 |

## Inconsistencias de nomenclatura

### Aeroportos de origem: mesma sigla com mais de um nome

_Nenhum registro._

### Aeroportos de destino: mesma sigla com mais de um nome

_Nenhum registro._

### Empresas: mesma sigla com mais de um nome

| EMPRESA_SIGLA | nomes_distintos | exemplos |
| --- | --- | --- |
| ARU | 2 | AIR ARUBA; ARUBA AIRLINES |
| ABJ | 2 | ABAETÉ LINHAS AÉREAS S.A.; ATA - AEROTÁXI ABAETÉ LTDA. |
| TSC | 2 | AIR TRANSAT A.T. INC; AIR TRANSAT A.T. INC DO BRASIL |

## Observacoes de qualidade

- Numeros armazenados como texto: ver secao "Colunas possivelmente numericas armazenadas como texto".
- Separador decimal: a auditoria contou ocorrencias de virgula e ponto nas colunas numericas. Campos sem ocorrencias aparentam inteiros; campos com virgula devem ser tratados com normalizacao explicita.
- Caracteres especiais: o arquivo foi lido como UTF-8 com BOM; nao foram detectados caracteres de substituicao se o total acima for zero.
- Duplicidades: `0` linha(s) potencialmente duplicada(s), estimadas por hash da linha completa.
- Valores negativos: ver coluna `negativos` no perfil numerico.
- Linhas incompletas: `482115` linha(s) com pelo menos um campo ausente ou vazio.
- Valores nulos/vazios: detalhados por coluna na tabela de ausentes.
- Nomenclatura de aeroportos e companhias: inconsistencias potenciais listadas nas tabelas acima.

## Reprodutibilidade

Comando usado:

```powershell
python scripts/auditar_dataset.py
```

Verificacoes executadas automaticamente:

- SHA-256 antes da auditoria: `270b815c5ded4a254aea3a2f8ebd731e53a2cb8eeb9f1689d013ddb6eda4ec92`
- SHA-256 depois da auditoria: `270b815c5ded4a254aea3a2f8ebd731e53a2cb8eeb9f1689d013ddb6eda4ec92`
- Arquivo preservado: `True`
- Contagem exata via Polars comparada com estimativa por quebras de linha.

