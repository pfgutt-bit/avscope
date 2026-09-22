# Entrega do AVScope — 22/09/2026

## Concluído nesta continuação

- Descobrir mercados, com comparação janeiro–mês contra os mesmos meses do ano anterior.
- Ranking por passageiros, crescimento, ocupação e concentração.
- Filtros por UF de origem/destino, volume, quantidade de companhias e completude da comparação.
- Abertura da rota selecionada com o período preservado.
- CSVs de mercados, série mensal e companhias, incluindo contexto de período e códigos internos.
- Página Sobre os dados com conceitos, cobertura, valores ausentes e fontes.
- Avisos de lacunas e anomalias sem correções silenciosas.
- Correção da consulta de companhias históricas sem operação no ano final selecionado.
- Calendário mensal contínuo para que meses ausentes interrompam as linhas dos gráficos, em vez de parecer continuidade.
- Manutenção da identidade escura com azul e navegação em três áreas.
- Pacote enxuto de publicação, instruções de operação e Dockerfile.

## Verificação executada

`python -m unittest discover -s tests -v`: **41 testes passaram** (27 existentes e 14 novos). Inclui testes de interface com Streamlit AppTest: link inválido, filtros, descoberta, abertura de rota, seleção de companhia, estado vazio e página de fontes.

`python -m pip check`: sem dependências quebradas. Ambiente: Python 3.12, versões das quatro dependências principais mantidas conforme o projeto recebido.

Conferência em navegador local: telas de rota e descoberta; layout padrão e viewport de 390 × 844. Na tela pequena, largura do documento = 390 px, sem controles escapando da largura. Tabelas largas usam rolagem interna. Não foi realizada auditoria formal de acessibilidade ou teste de carga multiusuário.

Servidor local: health check `/_stcore/health` retornou `ok`. O endereço local só funciona enquanto o processo estiver ativo.

Medição desta máquina: carregamento dos dados em 0,037 s, agregação de descoberta de jan–jul/2026 em 0,021 s e DataFrame principal de 139,5 MiB. Esses tempos medem dados/cálculos, não o carregamento total da página no navegador nem latência de uma hospedagem.

## Integridade

Comparação SHA-256 com os arquivos extraídos do ZIP recebido: CSV bruto, Parquet intermediário completo, Parquet oficial do MVP e dimensão de aeroportos permaneceram idênticos.

SHA-256 do CSV bruto: `270B815C5DED4A254AEA3A2F8EBD731E53A2CB8EEB9F1689D013DDB6EDA4EC92`.

A base oficial continua com 515.449 registros e cobertura até julho/2026. Nenhuma nova carga da ANAC foi feita. Os cálculos originais de `src/metrics.py` foram preservados; a interface adiciona critérios de completude antes de exibir variações.

## Publicação — pendente de conta

Nenhuma conta ou destino de hospedagem foi informado/conectado. Portanto, esta entrega não tem URL pública. O pacote acompanha instruções para Streamlit Community Cloud e container. O Dockerfile foi preparado, mas não executado porque Docker não está instalado nesta máquina. A publicação só estará concluída após o envio ao serviço e a confirmação da URL funcionando.

## Limites preservados

O produto descreve operações históricas, não prevê demanda nem rentabilidade. Anomalias permanecem sinalizadas; dados ausentes não são substituídos por zero. Alguns aeroportos históricos não têm IATA ou coordenadas. A atualização da base é manual e exige reauditoria, reconstrução dos dados e revisão dos testes vinculados à edição.

