# Vivo SMS Relay

Automação para roteadores 4G da Vivo com interface web ZTE.

O projeto faz login na UI interna do modem, envia SMS, lê a inbox, consulta estatísticas de tráfego e pode encaminhar mensagens novas para um webhook HTTP. A implementação foi construída a partir de engenharia reversa dos endpoints usados pela própria interface web do equipamento.

## O que o projeto faz

- Envia SMS por CLI ou por HTTP.
- Lê SMS recebidos por CLI ou por HTTP.
- Marca mensagens como lidas quando solicitado.
- Encaminha apenas SMS novos para um webhook, com estado local para evitar reprocessar backlog.
- Consulta e limpa estatísticas de uso de rede.
- Instala serviços `systemd` para a API HTTP e para o poller contínuo.

## Estrutura

- `config.py`: leitura de configuração via ambiente e `.env`
- `modem_client.py`: cliente principal para login, envio e leitura de SMS
- `modem_crypto.py`: implementação do hash de senha usado pelo modem
- `sms_server.py`: API HTTP para envio e leitura da inbox
- `read_sms.py`: leitura da inbox via terminal
- `sms_poller.py`: poller de inbox com webhook e estado local
- `modem_stats.py`: consulta e limpeza de estatísticas de tráfego
- `setup_env.py`: assistente para gerar `.env`
- `install_sms_server_service.sh`: instala a API como serviço `systemd`
- `install_sms_poller_service.sh`: instala o poller como serviço `systemd`

## Requisitos

- Python 3.x
- `requests`
- `python-dotenv`
- `Flask` apenas para a API HTTP (`sms_server.py`)

Instalação:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

## Configuração

### `.env`

Você pode gerar o arquivo com:

```bash
python3 setup_env.py
```

Ou criar manualmente:

```ini
MODEM_URL=http://192.168.1.1
MODEM_USER=admin

# Use MODEM_PASS ou MODEM_HASH
MODEM_PASS=vivo
# MODEM_HASH=<hash_precalculado>

SMS_SERVER_PORT=5001

# Poller / webhook
SMS_WEBHOOK_URL=http://127.0.0.1:9000/sms
SMS_POLL_INTERVAL=30
SMS_POLL_REQUEST_TIMEOUT=15
SMS_POLL_STATE_FILE=/caminho/para/sms_poller_state.json
```

### Variáveis de ambiente

- `MODEM_URL`: URL base da interface do modem
- `MODEM_USER`: usuário da interface web
- `MODEM_PASS`: senha em texto plano
- `MODEM_HASH`: hash pré-calculado da senha; tem prioridade sobre `MODEM_PASS`
- `SMS_SERVER_PORT`: porta da API HTTP
- `SMS_WEBHOOK_URL`: destino do poller
- `SMS_POLL_INTERVAL`: intervalo em segundos entre leituras da inbox
- `SMS_POLL_REQUEST_TIMEOUT`: timeout do POST do webhook
- `SMS_POLL_STATE_FILE`: arquivo local onde o poller guarda o último `idx` processado

## Uso rápido

### 1. Enviar SMS

```bash
python3 modem_client.py 11999999999 "Mensagem de teste"
```

Com credenciais explícitas:

```bash
python3 modem_client.py 11999999999 "Mensagem de teste" --user admin --password vivo
```

Com hash explícito:

```bash
python3 modem_client.py 11999999999 "Mensagem de teste" --user admin --hash <hash>
```

### 2. Ler SMS recebidos

Últimos 10:

```bash
python3 read_sms.py --limit 10
```

Apenas não lidos:

```bash
python3 read_sms.py --limit 10 --unread-only
```

Saída JSON:

```bash
python3 read_sms.py --limit 10 --json
```

Marcar como lidos os SMS retornados:

```bash
python3 read_sms.py --limit 5 --mark-read
```

### 3. Encaminhar SMS novos para webhook

Executar um único ciclo:

```bash
python3 sms_poller.py --once --webhook-url http://127.0.0.1:9000/sms
```

Executar continuamente:

```bash
python3 sms_poller.py --webhook-url http://127.0.0.1:9000/sms
```

Na primeira execução, o comportamento padrão é inicializar o estado com o maior `idx` atual da inbox e não reenviar mensagens antigas. Para reenviar também o backlog existente:

```bash
python3 sms_poller.py --once --replay-existing --webhook-url http://127.0.0.1:9000/sms
```

Para marcar como lidas as mensagens encaminhadas:

```bash
python3 sms_poller.py --mark-read --webhook-url http://127.0.0.1:9000/sms
```

### 4. Consultar estatísticas de tráfego

```bash
python3 modem_stats.py
```

Limpar histórico:

```bash
python3 modem_stats.py --clear
```

Saída JSON:

```bash
python3 modem_stats.py --json
```

## API HTTP

Suba a API:

```bash
python3 sms_server.py
```

### Enviar SMS

```bash
curl -X POST http://localhost:5001/send_sms \
     -H "Content-Type: application/json" \
     -d '{"number": "11999999999", "message": "Olá via API"}'
```

### Ler inbox

Via `GET`:

```bash
curl "http://localhost:5001/inbox_sms?limit=10&unread_only=1"
```

Via `POST` JSON:

```bash
curl -X POST http://localhost:5001/inbox_sms \
     -H "Content-Type: application/json" \
     -d '{"limit": 5, "unread_only": true, "mark_read": false}'
```

### Resposta da inbox

Exemplo:

```json
{
  "status": "success",
  "total_inbox_messages": 31,
  "returned_messages": 2,
  "messages": [
    {
      "idx": 31,
      "number": "Vivo",
      "time": "2026/04/13,18:19:43",
      "content": "Mensagem...",
      "unread": true
    }
  ]
}
```

## Webhook do poller

O `sms_poller.py` envia um `POST` JSON com este formato:

```json
{
  "event": "sms_received",
  "source": "vivosmsrelay",
  "message": {
    "idx": 31,
    "number": "Vivo",
    "time": "2026/04/13,18:19:43",
    "content": "Mensagem...",
    "unread": true
  },
  "forwarded_at": "2026-04-14T21:46:10.452625+00:00"
}
```

## Serviços systemd

### API HTTP

Instala e sobe o serviço:

```bash
sudo ./install_sms_server_service.sh
```

Serviço criado:

- `vivosmsrelay.service`

Função:

- sobe `sms_server.py`
- expõe `/send_sms` e `/inbox_sms`
- reinicia automaticamente em caso de falha

### Poller contínuo

Instala e sobe o serviço:

```bash
sudo ./install_sms_poller_service.sh
```

Serviço criado:

- `vivosmsrelay-poller.service`

Antes de instalar, configure ao menos:

```ini
SMS_WEBHOOK_URL=http://127.0.0.1:9000/sms
SMS_POLL_INTERVAL=30
```

Função:

- roda `sms_poller.py` em loop
- consulta a inbox periodicamente
- encaminha apenas mensagens novas para o webhook

## Limitações e comportamento do modem

- A API do modem aceita no máximo 30 registros por chamada em `get_sms_inbox_records`.
- Quando `full_content=true`, o modem aceita apenas um único SMS por vez.
- O cliente deste projeto pagina e expande esses registros automaticamente.
- Os scripts assumem execução a partir da raiz do repositório.
- O servidor Flask é simples e voltado a uso controlado em rede confiável.

## Desenvolvimento

Validação rápida de sintaxe:

```bash
python3 -m py_compile modem_client.py read_sms.py sms_poller.py sms_server.py modem_stats.py config.py
```

## Aviso legal

Projeto para fins educacionais. Use com responsabilidade.
