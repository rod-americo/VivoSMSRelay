# Vivo SMS Relay

This project allows programmatic control of Vivo Modems (likely **ZTE** models such as MF79U/MF833) to send SMS messages via their web interface/API.

It was developed through reverse engineering of the modem's web interface authentication (custom AES-like encryption) and internal API endpoints.

## Features

-   **Dynamic Authentication**: Supports any username/password combination by replicating the modem's custom hashing algorithm (TIFA key).
-   **Performance Optimization**: Pre-calculated hash support for default credentials (`admin`/`vivo`) to avoid re-encryption overhead.
-   **Configurable**: Easy setup via `.env` file.

## Requirements

-   Python 3.x
-   `requests`
-   `python-dotenv`

Install dependencies:
```bash
pip install requests python-dotenv
```

## Setup

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/rod-americo/VivoSMSRelay.git
    cd VivoSMSRelay
    ```

2.  **Configuration**:
    Create a `.env` file in the project root (optional, defaults are `admin`/`vivo` @ `192.168.1.1`):
    ```ini
    MODEM_URL=http://192.168.1.1
    MODEM_USER=admin
    MODEM_PASS=vivo
    # Optional: Pre-calculated hash to override dynamic calculation
    # MODEM_HASH=...
    ```

## Usage

### As a Library
```python
from sms.modem_client import ModemClient

client = ModemClient() # Uses credentials from .env or defaults
if client.login():
    client.send_sms("11999999999", "Hello from Python!")
```

### CLI
Send an SMS directly from the terminal:
```bash
# Uses defaults or .env
python3 sms/modem_client.py 11999999999 "Test Message"

# Override credentials
python3 sms/modem_client.py 11999999999 "Test Message" --user myuser --password mypass
```

## Disclaimer

This project is for educational purposes. Use responsibly.
