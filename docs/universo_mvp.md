# Universo oficial do MVP

Gerado em: `2026-09-14T11:25:22`.

## Definicao

O produto usa exclusivamente registros com `GRUPO_DE_VOO = REGULAR`, `NATUREZA = DOMÉSTICA`, pais de origem e destino iguais a `BRASIL`, codigos aeroportuarios presentes, origem diferente de destino e evidencia historica de transporte de passageiros na mesma combinacao `ROTA_DIRECIONAL + EMPRESA_ID`.

A evidencia historica e verdadeira quando ao menos um mes regular da rota-companhia possui `FLAG_EVIDENCIA_TRANSPORTE_PASSAGEIROS`. Ela preserva meses zerados pertencentes a uma operacao historicamente caracterizada como transporte de passageiros, sem admitir automaticamente toda operacao cargueira regular.

## Flags e rastreabilidade

- `FLAG_UNIVERSO_MVP`: regra original da Etapa 2, avaliada linha a linha: voo regular e evidencia positiva na propria linha.
- `FLAG_UNIVERSO_MVP_V2`: regra oficial validada na Etapa 3, com evidencia historica, recorte domestico brasileiro e rota OD valida.
- `FLAG_REGISTRO_RECUPERADO_MVP_V2`: linha aceita pela V2 que seria perdida pela flag original.

No arquivo oficial, `504033` linhas tambem satisfazem a flag antiga e `11416` foram recuperadas pela V2. Total: `515449` registros.

Na base processada completa, a matriz e: `504033` registros aceitos por ambas, `11416` somente pela V2, `120650` somente pela antiga e `460455` por nenhuma. Os registros aceitos apenas pela regra antiga ficam fora do produto porque a flag original nao exigia simultaneamente o recorte domestico brasileiro, a validade OD e a evidencia historica usada pela V2.

## Cobertura

- Rotas direcionais: `5187`.
- Aeroportos: `334`.
- Companhias por `EMPRESA_ID`: `43`.
- Periodo: `2000-01-01` a `2026-07-01`.
- `GRUPO_DE_VOO`: `REGULAR`.
- `NATUREZA`: `DOMÉSTICA`.

## Grao

O Parquet preserva o grao da base processada: `PERIODO + ROTA_DIRECIONAL + EMPRESA_ID + categorias operacionais e atributos de origem/destino`. Nao houve nova agregacao nem mistura de categorias. Embora `GRUPO_DE_VOO` e `NATUREZA` sejam constantes neste recorte, elas foram mantidas para rastreabilidade. Duplicidades no conjunto completo de dimensoes da Etapa 2: `0`.

## Anomalias

Registros com `RPK > ASK`, passageiros acima de assentos ou denominadores zerados nao foram excluidos. O arquivo inclui flags especificas para que as metricas e a futura interface possam sinaliza-los. Valores nulos permanecem nulos; zero observado nao e usado como substituto de ausencia de informacao.

