# Vivo SMS Relay

Este projeto permite o controle programático de roteadores 4G (Modems) da Vivo (modelo WLD71-T5A) para envio de SMS através de sua interface web/API.

Foi desenvolvido através de engenharia reversa da autenticação da interface web do modem (que utiliza uma criptografia AES customizada) e dos endpoints internos da API.

## Funcionalidades

-   **Autenticação Dinâmica**: Suporta qualquer combinação de usuário/senha replicando o algoritmo de hash customizado do modem (chave TIFA).
-   **Otimização de Performance**: Suporte a hash pré-calculado para as credenciais padrão (`admin`/`vivo`) para evitar overhead de re-encriptação.
-   **Configurável**: Configuração fácil via arquivo `.env`.

## Requisitos

-   Python 3.x
-   `requests`
-   `python-dotenv`

Instale as dependências:
```bash
pip install requests python-dotenv
```

## Configuração

1.  **Clone o repositório**:
    ```bash
    git clone https://github.com/rod-americo/VivoSMSRelay.git
    cd VivoSMSRelay
    ```

2.  **Configuração Automática (Recomendado)**:
    Execute o script auxiliar para gerar o arquivo `.env` com suas credenciais e hash otimizado:
    ```bash
    python3 sms/setup_env.py
    ```

3.  **Configuração Manual (Alternativa)**:
    Crie um arquivo `.env` na raiz do projeto:
    ```ini
    MODEM_URL=http://192.168.1.1
    MODEM_USER=admin
    # Use MODEM_PASS (cálculo dinâmico) OU MODEM_HASH (pré-calculado)
    MODEM_PASS=vivo
    ```

## Uso

### Como Biblioteca
```python
from sms.modem_client import ModemClient

client = ModemClient() # Usa credenciais do .env ou padrões
if client.login():
    client.send_sms("11999999999", "Olá do Python!")
```

### Linha de Comando (CLI)
Envie um SMS diretamente pelo terminal:
```bash
# Usa padrões ou .env
python3 sms/modem_client.py 11999999999 "Mensagem de Teste"

# Sobrescrever credenciais
python3 sms/modem_client.py 11999999999 "Mensagem de Teste" --user outro_usuario --password nova_senha
```

### Servidor HTTP (API)
Para enviar SMS via requisições HTTP (útil para integrar com outros sistemas):
1. Inicie o servidor:
    ```bash
    python3 sms/sms_server.py
    ```
2. Envie uma requisição POST:
    ```bash
    curl -X POST http://localhost:5001/send_sms \
         -H "Content-Type: application/json" \
         -d '{"number": "11999999999", "message": "Olá via API!"}'
    ```

## Aviso Legal

Este projeto é para fins educacionais. Use com responsabilidade.
