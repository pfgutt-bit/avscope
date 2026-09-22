# Performance da interface

Medição local em 14/09/2026, com Python 3.12, Polars 1.44.2, Streamlit 1.63.0 e Plotly 7.0.0.

- Leitura inicial do Parquet oficial: aproximadamente `0,04–0,11 s`.
- Memória estimada do `DataFrame` Polars em cache: `139,54 MB`.
- Atualização analítica média nas cinco rotas de validação: `0,023 s`.
- Intervalo observado por troca de rota: `0,019–0,034 s`.

O app carrega os dois Parquets uma única vez com `st.cache_data`. Os filtros e agregações trabalham em Polars, e apenas os resultados pequenos são enviados ao Plotly. Não há leitura do CSV bruto nem conversão repetida do conjunto completo para Pandas.

O principal custo perceptível restante é a renderização dos quatro componentes Plotly no navegador, não o cálculo das métricas. O volume em memória é adequado para execução local; em hospedagem com limite de memória baixo, esse será o primeiro ponto a monitorar.

