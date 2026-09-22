# Fontes da dimensao de aeroportos

Gerado em: `2026-09-14T11:25:22`.

## Fontes

1. **SIROS/ANAC**, arquivo estruturado `https://siros.anac.gov.br/siros/registros/aerodromo/aerodromos.csv`. E a fonte prioritaria para ICAO, IATA, nome oficial, municipio, UF, pais, latitude e longitude. Snapshot local: `data/external/anac_siros_aerodromos.csv`, SHA-256 `2fc678c89b76216d319bfe57ae3c2ad9e45e1258035e724743105a7e415b1c2c`.
2. **Dados Estatisticos do Transporte Aereo da ANAC**, por meio do Parquet da Etapa 2. Fornecem nome, UF, regiao e pais para codigos historicos ausentes do cadastro SIROS atual.
3. **OurAirports**, arquivo aberto `https://raw.githubusercontent.com/davidmegginson/ourairports-data/main/airports.csv` e dicionario em `https://ourairports.com/help/data-dictionary.html`. E usado somente como complemento para IATA, municipio ou coordenadas ausentes na ANAC. Snapshot local: `data/external/ourairports_airports.csv`, SHA-256 `47880571c7f3129667cc22e5a3fd0ec10f12883b405ca2b3ce40994847610529`.

ICAO e a chave interna. Nenhum IATA foi inferido por manipulacao de texto. A precedencia e ANAC SIROS, dados estatisticos ANAC quando aplicavel e, por ultimo, OurAirports.

## Cobertura do universo

- Aeroportos do MVP: `334`.
- Encontrados no cadastro SIROS atual: `306`.
- Com IATA: `272` (`267` pela ANAC e `5` complementares).
- Sem IATA: `62`.
- Com nome: `334`.
- Com municipio: `310`.
- Com coordenadas completas: `310`.
- Conflitos de IATA valido entre ANAC e OurAirports: `0`.
- Codigos IATA associados a mais de um ICAO no universo: `0`.

Os codigos sem correspondencia no SIROS atual sao principalmente aerodromos historicos, militares, encerrados ou codigos legados. Nesses casos, o nome/UF/regiao/pais da propria serie estatistica foi preservado. Ausencia de IATA continua nula.

## Validacoes explicitas

- `SBBE` -> `BEL`: INTERNACIONAL DE BELÉM/VAL DE CANS/JÚLIO CEZAR RIBEIRO (BELÉM).
- `SBBR` -> `BSB`: PRESIDENTE JUSCELINO KUBITSCHEK (BRASÍLIA).
- `SBEG` -> `MAO`: EDUARDO GOMES (MANAUS).
- `SBGR` -> `GRU`: GUARULHOS - GOVERNADOR ANDRÉ FRANCO MONTORO (GUARULHOS).
- `SBRJ` -> `SDU`: SANTOS DUMONT (RIO DE JANEIRO).
- `SBSP` -> `CGH`: CONGONHAS (SÃO PAULO).

## Observacoes de ingestao

O CSV do SIROS usa ponto e virgula e virgula decimal. Alguns nomes internacionais possuem aspas literais sem escape CSV; por isso a leitura desabilita semantica de aspas e valida exatamente nove campos por linha. O OurAirports e UTF-8 separado por virgula. Os snapshots locais tornam a execucao repetivel; use `--refresh-airports` somente para atualizar conscientemente as fontes externas.

