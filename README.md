# AVScope

Explorador independente do mercado aéreo doméstico brasileiro, baseado nos dados da ANAC.

## O que está disponível

- **Explorar rota:** séries mensais, passageiros, assentos, decolagens, ocupação, participação das companhias e concentração (HHI).
- **Descobrir mercados:** ranking por volume, crescimento, ocupação e concentração; filtros por UFs, mínimo de passageiros e quantidade de companhias; abertura da rota selecionada.
- **Sobre os dados:** cobertura, conceitos, fontes e limitações.
- **Exportação:** séries, companhias e mercados em CSV compatível com Excel.

A edição acompanha 515.449 registros, 5.187 rotas direcionais, 334 aeroportos e 43 identificações de companhias, de janeiro/2000 a julho/2026. Essas contagens referem-se ao histórico completo, não a empresas ou rotas atualmente ativas. A fonte é uma fotografia histórica; não há atualização automática.

## Dados

A fonte principal são os Dados Estatísticos do Transporte Aéreo da ANAC. O app lê somente:

- `data/processed/avscope_mvp_domestic.parquet`
- `data/processed/dim_airports.parquet`

O CSV bruto nunca é lido pela interface. A metodologia está documentada em `docs/universo_mvp.md`, `docs/metricas.md`, `docs/descobrir_mercados.md` e `docs/fontes_dimensao_aeroportos.md`.

O pacote `AVScope_publicacao.zip` inclui os dois Parquets e tudo que é necessário para executar a aplicação. Ele não inclui o CSV original, a base intermediária ou os snapshots dos cadastros. Esses arquivos permanecem na pasta completa do projeto e no ZIP original recebido.

## Instalação

Requer Python 3.12 e internet na primeira instalação.

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m streamlit run app.py --server.address=127.0.0.1
```

No Windows, `iniciar.ps1` também prepara o ambiente e inicia o app. O endereço normalmente é http://localhost:8501. Ele só permanece acessível enquanto o processo estiver em execução.

## Verificação

```powershell
python -m unittest discover -s tests -v
```

Os testes conferem fórmulas, referências reais, qualidade, descoberta, filtros e navegação do aplicativo. O primeiro carregamento de bibliotecas pode ser mais lento numa instalação nova.

## Publicar

Veja `docs/publicacao.md`. Incluímos uma opção para Streamlit Community Cloud e um Dockerfile para serviços que executam containers. Preparar esses arquivos não cria uma publicação: é necessário conectar a conta de hospedagem e o repositório ou enviar a imagem.

Para gerar novamente o pacote de publicação:

```powershell
python scripts/package_release.py
```

## Atualização e reprodução

Para reconstruir esta edição, use a pasta completa e o CSV original preservado:

```powershell
python scripts/auditar_dataset.py
python -m src.process_data
python scripts/validar_mvp.py
python scripts/build_stage4.py
python -m unittest discover -s tests -v
```

Uma nova edição da ANAC deve ser auditada em uma cópia separada do projeto, preservando a edição anterior. Testes de referência vinculados a esta edição precisam ser revistos se a ANAC revisar os valores históricos. Reinicie o servidor após atualizar os Parquets para invalidar os caches.

As medições históricas estão em `docs/performance_app.md`; a validação desta entrega está em `docs/entrega_final.md`.

