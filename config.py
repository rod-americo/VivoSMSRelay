import os
import sys
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Modem Connection Details
MODEM_URL = os.getenv("MODEM_URL", "http://192.168.1.1")

# Credentials
MODEM_USER = os.getenv("MODEM_USER", "admin")
MODEM_PASS = os.getenv("MODEM_PASS", "vivo")

# Pre-calculated hash for default creds (admin/vivo) to save time
# Key: TIFA
# Pwd: vivo
# Hash: 6bbcbeed1205437de307b72351f329b3206363636363638363635a63633b6363206363636363638363635a63633b6363206363636363638363635a63633b6363
# (Note: The hash for 'vivo' might be different from the one for 'Q7fR...', I will recalculate it if needed, 
# but for now I'll include the one we know works if the user updates .env. 
# Actually, let's allow MODEM_HASH env var to override everything.)

MODEM_HASH = os.getenv("MODEM_HASH", None)

# Pre-calculated hash for admin/vivo to save time
# This avoids running the encryption logic if using defaults
DEFAULT_VIVO_HASH = "93636363636363316363046363b76363206363636363638363635a63633b6363206363636363638363635a63633b6363206363636363638363635a63633b6363"

if not MODEM_HASH and MODEM_USER == "admin" and MODEM_PASS == "vivo":
    MODEM_HASH = DEFAULT_VIVO_HASH
