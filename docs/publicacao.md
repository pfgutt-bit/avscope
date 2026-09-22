# Publicação do AVScope

## Situação desta entrega

O aplicativo e o pacote de publicação estão preparados. Nenhuma conta de hospedagem foi conectada nesta entrega e nenhuma URL pública foi criada. O endereço local não equivale a uma publicação na internet.

## Streamlit Community Cloud

O serviço publica a aplicação a partir de um repositório GitHub. São necessários acesso à conta GitHub e à conta Streamlit Community Cloud.

1. Extraia `AVScope_publicacao.zip` para uma pasta vazia e envie seu conteúdo a um repositório sob sua conta. Não envie o CSV bruto de 358,9 MB.
2. Em https://share.streamlit.io escolha **Create app** e **Yup, I have an app**.
3. Selecione o repositório, a branch e `app.py` como arquivo de entrada.
4. Nas opções avançadas, selecione Python 3.12. Esta versão não requer chaves ou segredos.
5. Defina a visibilidade desejada, publique e confirme no endereço gerado: tela de rota, Descobrir mercados, exportação e dados até julho/2026.

Instruções oficiais consultadas em 22/09/2026: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy

## Container

Um serviço que execute containers pode usar o Dockerfile incluído. Ele instala as dependências fixadas, copia somente o código necessário e os dois Parquets, executa sem usuário root e aceita a variável `PORT` (padrão 8501).

```sh
docker build -t avscope .
docker run --rm -p 8501:8501 avscope
```

O health check usa `/_stcore/health`. O provedor precisa aceitar WebSockets e manter o processo Python ativo. TLS, domínio, recursos e acesso são configurados no provedor. O Dockerfile não foi executado nesta máquina, pois Docker não está instalado; a aplicação Python foi testada localmente.

## Atualizações e reversão

Mantenha a edição anterior do código e dos Parquets. Audite uma nova base em separado, execute o pipeline e os testes adequados, substitua os dois Parquets juntos e reinicie a aplicação. Uma reversão deve restaurar código e dados da mesma edição.

A aplicação usa cache em memória compartilhado no processo. Após mudar os arquivos, reinicie o servidor. O ranking acumula até 24 resultados por período no cache. Uso real com vários usuários deve ser acompanhado nos recursos e logs do provedor.

