# Descobrir mercados

Implementado em 22/09/2026 sobre o Parquet oficial existente, sem alterar os dados brutos ou tratados.

## Período e comparação

O usuário escolhe um ano e o último mês do acumulado. Cada rota soma janeiro até esse mês; o período anterior usa exatamente os mesmos meses do ano anterior. O limite do mês vem da cobertura do ano na base inteira.

O crescimento é `(passageiros atuais / passageiros anteriores - 1) * 100`. Ele só é calculado quando ambos os períodos têm todos os meses esperados, nenhum registro com passageiros nulos e base anterior positiva. Caso contrário, é nulo e tem uma justificativa: sem base anterior, meses sem registro, passageiros ausentes ou base anterior zerada. Ausência não é interpretada como zero e não caracteriza automaticamente uma nova rota.

Essa verificação mede completude dos registros presentes. Ela não prova que todas as companhias enviaram todos os dados à ANAC. Totais, participações e HHI dependem dos valores informados na fonte.

## Agregação e concorrência

Uma linha por rota direcional. As métricas aditivas usam os valores informados; se todos forem nulos, a soma é nula. Load Factor é soma de RPK dividida pela soma de ASK, vezes 100. Não é a média dos percentuais mensais.

Companhias no ranking contam identificadores com passageiros pagos positivos no período. Na tela da rota, a contagem original inclui companhias com registros, inclusive zerados. HHI e participação máxima usam passageiros da companhia sobre o total da rota, sem filtros de uma companhia individual e sem classificação concorrencial automática.

## Filtros e sinalizações

UF de origem e destino vêm da dimensão aeroportuária. Filtros por volume mínimo, número máximo de companhias e comparabilidade não alteram os denominadores dos indicadores. A ordenação usa a rota como critério de desempate e coloca indicadores ausentes por último.

Registros sinalizados contam linhas com pelo menos uma das cinco flags operacionais. São contagens de linhas únicas; a tela de detalhe também mostra ocorrências por tipo, que podem se sobrepor. Nenhum dado anômalo é corrigido, truncado ou eliminado.

## Exportação e navegação

O CSV inclui todo o resultado filtrado, não apenas os 12 mercados do gráfico: códigos ICAO/IATA, localização, janelas atual e anterior, métricas, cobertura, nulos e sinalizações. Usa UTF-8 com BOM, ponto e vírgula e vírgula decimal.

O botão de exploração transfere origem, destino e janela selecionados à tela da rota. Links do modo Descobrir preservam ano e mês; filtros adicionais ficam na sessão. Links da rota preservam aeroportos, datas e companhia. Sem hospedagem, um link localhost funciona apenas no computador que executa o app.

## Limite de interpretação

O ranking descreve rotas existentes no histórico, não estima demanda de uma rota inédita ou rentabilidade. Não há tarifas, custos, preços, margens nem previsão. Rotas com pouca concorrência ou ocupação alta são pontos de partida para investigação.

