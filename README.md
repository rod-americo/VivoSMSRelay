# Vivo SMS Relay

Este projeto permite o controle programático de roteadores 4G da Vivo para envio de SMS por meio da interface web interna do modem.

O fluxo foi construído a partir de engenharia reversa da autenticação da interface web e dos endpoints usados pelo equipamento.

## Funcionalidades

- **Autenticação dinâmica**: calcula o hash esperado pelo modem a partir de usuário e senha.
- **Hash otimizado para credenciais padrão**: evita recálculo quando o modem está com `admin` / `vivo`.
- **CLI para envio de SMS**: uso direto via terminal.
- **Servidor HTTP opcional**: expõe uma API simples para integração local.
- **Consulta e reset de estatísticas**: lê consumo de rede e registra o último reset localmente.

## Estrutura do projeto

- `config.py`: leitura de configuração via ambiente e `.env`
- `modem_client.py`: cliente principal para login e envio de SMS
- `modem_crypto.py`: implementação do algoritmo de hash usado pelo modem
- `modem_stats.py`: leitura e limpeza de estatísticas de rede
- `setup_env.py`: assistente interativo para gerar `.env`
- `sms_server.py`: API HTTP simples para envio de SMS

## Requisitos

- Python 3.x
- `requests`
- `python-dotenv`
- `Flask` apenas se você for usar a API HTTP (`sms_server.py`)

Instalação das dependências básicas:

```bash
pip install requests python-dotenv
```

Se também for usar o servidor HTTP:

```bash
pip install Flask
```

## Configuração

1. Clone o repositório:

```bash
git clone https://github.com/rod-americo/VivoSMSRelay.git
cd VivoSMSRelay
```

2. Gere o `.env` automaticamente:

```bash
python3 setup_env.py
```

3. Ou crie o `.env` manualmente na raiz do projeto:

```ini
MODEM_URL=http://192.168.1.1
MODEM_USER=admin
# Use MODEM_PASS (cálculo dinâmico) OU MODEM_HASH (pré-calculado)
MODEM_PASS=vivo
SMS_SERVER_PORT=5001
```

Também é possível usar:

```ini
MODEM_HASH=<hash_precalculado>
```

## Uso

### Como biblioteca

```python
from modem_client import ModemClient

client = ModemClient()
if client.login():
    client.send_sms("11999999999", "Olá do Python!")
```

### Linha de comando

Envie um SMS diretamente pelo terminal:

```bash
# Usa credenciais do .env ou os padrões
python3 modem_client.py 11999999999 "Mensagem de teste"
```

Sobrescrevendo as credenciais:

```bash
python3 modem_client.py 11999999999 "Mensagem de teste" --user outro_usuario --password nova_senha
```

Usando hash pré-calculado diretamente:

```bash
python3 modem_client.py 11999999999 "Mensagem de teste" --user admin --hash <hash>
```

### Servidor HTTP

Para enviar SMS via requisições HTTP:

1. Inicie o servidor:

```bash
python3 sms_server.py
```

2. Envie uma requisição `POST`:

```bash
curl -X POST http://localhost:5001/send_sms \
     -H "Content-Type: application/json" \
     -d '{"number": "11999999999", "message": "Olá via API"}'
```

Para mudar a porta do servidor, defina no `.env`:

```ini
SMS_SERVER_PORT=5001
```

### Estatísticas de uso

O script `modem_stats.py` permite consultar consumo de dados e limpar o histórico. Ele também salva localmente a data e hora do último reset em `modem_stats_state.json`.

Visualizar consumo:

```bash
python3 modem_stats.py
```

Limpar histórico:

```bash
python3 modem_stats.py --clear
```

Saída em JSON:

```bash
python3 modem_stats.py --json
```

Sobrescrevendo credenciais no script de estatísticas:

```bash
python3 modem_stats.py --user admin --password vivo
```

## Observações

- Os scripts assumem execução a partir da raiz do repositório.
- O arquivo `.env` é opcional, mas recomendado para não depender dos valores padrão.
- O servidor HTTP atual é simples e voltado a uso controlado em rede confiável.

## Aviso legal

Projeto para fins educacionais. Use com responsabilidade.
