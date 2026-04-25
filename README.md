# CPE SMS Relay

Automacao para envio, leitura e encaminhamento de SMS em modems/roteadores CPE usados como uplink movel.

O projeto nasceu para o modem Vivo/ZTE legado, mas agora usa drivers para suportar mais de um equipamento com a mesma interface de CLI, API HTTP, poller e estatisticas.

## Drivers suportados

- `zte`: modem Vivo/ZTE legado, com API JSON em `/cgi-bin/login.cgi` e `/cgi-bin/gui.cgi`.
- `huawei`: roteadores Huawei/ZOWEE HiLink, incluindo `H153-381 / 5G CPE 5s`, com API XML em `/api/...` e login SCRAM.

Aliases aceitos:

- `vivo` e `mf79u` apontam para `zte`.
- `zowee`, `hilink`, `h153` e `h153-381` apontam para `huawei`.

## O que o projeto faz

- Envia SMS por CLI ou HTTP.
- Le SMS recebidos por CLI ou HTTP.
- Marca mensagens como lidas quando solicitado.
- Encaminha apenas SMS novos para um webhook HTTP, com estado local para evitar reprocessar backlog.
- Consulta e limpa estatisticas de trafego quando o driver/equipamento suporta.
- Pode instalar servicos `systemd` opcionais para API HTTP e poller continuo.

## Estrutura

- `config.py`: leitura de configuracao via ambiente e `.env`.
- `modem_client.py`: fabrica `ModemClient` e implementacoes dos drivers `zte` e `huawei`.
- `modem_crypto.py`: hash de senha usado pelo modem ZTE legado.
- `sms_server.py`: API HTTP para envio e leitura da inbox.
- `read_sms.py`: leitura da inbox via terminal.
- `sms_poller.py`: poller de inbox com webhook e estado local.
- `modem_stats.py`: consulta e limpeza de estatisticas de trafego.
- `setup_env.py`: assistente para gerar `.env`.
- `install_sms_server_service.sh`: instala a API como servico `systemd` opcional.
- `install_sms_poller_service.sh`: instala o poller como servico `systemd` opcional.

## Requisitos

- Python 3.x
- `requests`
- `python-dotenv`
- `Flask` apenas para a API HTTP (`sms_server.py`)

Instalacao:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

## Configuracao

Gere o `.env` interativamente:

```bash
python3 setup_env.py
```

Ou crie manualmente.

### ZTE legado

```ini
MODEM_DRIVER=zte
MODEM_URL=http://192.168.1.1
MODEM_USER=admin

# Use MODEM_PASS ou MODEM_HASH. MODEM_HASH evita guardar a senha em texto.
MODEM_PASS=vivo
# MODEM_HASH=<hash_precalculado>

SMS_SERVER_PORT=5001
```

### Huawei/ZOWEE H153-381

```ini
MODEM_DRIVER=huawei
MODEM_URL=http://192.168.8.1
MODEM_USER=admin
MODEM_PASS=<senha_do_painel>

SMS_SERVER_PORT=5001
```

`MODEM_HASH` nao se aplica ao driver `huawei`, porque esse firmware usa login SCRAM com nonce/salt/iteracoes.
O driver replica a variante SCRAM implementada pela biblioteca `emui-crypto.js`
do firmware, incluindo a ordem dos argumentos HMAC usada pelo roteador.

### Poller / webhook

```ini
SMS_WEBHOOK_URL=http://127.0.0.1:9000/sms
SMS_POLL_INTERVAL=30
SMS_POLL_REQUEST_TIMEOUT=15
SMS_POLL_STATE_FILE=/caminho/para/sms_poller_state.json
```

## Uso rapido

### Enviar SMS

```bash
python3 modem_client.py 11999999999 "Mensagem de teste"
```

Com driver e credenciais explicitas:

```bash
python3 modem_client.py 11999999999 "Mensagem de teste" \
  --driver huawei \
  --user admin \
  --password '<senha_do_painel>'
```

### Ler SMS recebidos

Ultimos 10:

```bash
python3 read_sms.py --limit 10
```

Apenas nao lidos:

```bash
python3 read_sms.py --limit 10 --unread-only
```

Saida JSON:

```bash
python3 read_sms.py --limit 10 --json
```

Marcar como lidos os SMS retornados:

```bash
python3 read_sms.py --limit 5 --mark-read
```

### Encaminhar SMS novos para webhook

Executar um unico ciclo:

```bash
python3 sms_poller.py --once --webhook-url http://127.0.0.1:9000/sms
```

Executar continuamente:

```bash
python3 sms_poller.py --webhook-url http://127.0.0.1:9000/sms
```

Na primeira execucao, o comportamento padrao e inicializar o estado com o maior `idx` atual da inbox e nao reenviar mensagens antigas. Para reenviar tambem o backlog existente:

```bash
python3 sms_poller.py --once --replay-existing --webhook-url http://127.0.0.1:9000/sms
```

Para marcar como lidas as mensagens encaminhadas:

```bash
python3 sms_poller.py --mark-read --webhook-url http://127.0.0.1:9000/sms
```

### Consultar estatisticas de trafego

```bash
python3 modem_stats.py
```

Limpar historico:

```bash
python3 modem_stats.py --clear
```

Saida JSON:

```bash
python3 modem_stats.py --json
```

## API HTTP

Suba a API:

```bash
python3 sms_server.py
```

Enviar SMS:

```bash
curl -X POST http://localhost:5001/send_sms \
  -H "Content-Type: application/json" \
  -d '{"number": "11999999999", "message": "Ola via API"}'
```

Ler inbox:

```bash
curl "http://localhost:5001/inbox_sms?limit=10&unread_only=1"
```

Via `POST` JSON:

```bash
curl -X POST http://localhost:5001/inbox_sms \
  -H "Content-Type: application/json" \
  -d '{"limit": 5, "unread_only": true, "mark_read": false}'
```

Resposta da inbox:

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
  "forwarded_at": "2026-04-13T21:20:00+00:00"
}
```

## Servicos systemd

Os instaladores agora usam nomes genericos por padrao:

- API HTTP: `cpe-sms-relay.service`
- Poller: `cpe-sms-relay-poller.service`

Instalar API:

```bash
sudo ./install_sms_server_service.sh
```

Instalar poller:

```bash
sudo ./install_sms_poller_service.sh
```

Para manter nomes legados em outro host, use variaveis de ambiente:

```bash
sudo SMS_SERVICE_NAME=vivosmsrelay ./install_sms_server_service.sh
sudo SMS_POLLER_SERVICE_NAME=vivosmsrelay-poller ./install_sms_poller_service.sh
```

## Notas operacionais

- `.env`, estados locais e `.venv/` nao devem ser versionados.
- O driver `huawei` consome a metade final do token retornado por `/api/webserver/token`, seguindo o comportamento observado na UI oficial do firmware `H153-381`.
- Estatisticas do driver `huawei` sao normalizadas para `tx` e `rx` em KiB, preservando o contrato usado pelo script `info` do host.
