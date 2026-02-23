import os
from dotenv import load_dotenv

load_dotenv()

# ── Telegram ───────────────────────────────────────────────
TELEGRAM_TOKEN     = os.getenv("TELEGRAM_TOKEN")
AUTHORIZED_USER_ID = os.getenv("AUTHORIZED_USER_ID")

# ── Google Sheets ──────────────────────────────────────────
SHEETS_CREDENTIALS_PATH = os.getenv("SHEETS_CREDENTIALS_PATH", "credentials.json")
SPREADSHEET_ID          = os.getenv("SPREADSHEET_ID")

# ── Gemini ─────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# ── Validações ─────────────────────────────────────────────
if not TELEGRAM_TOKEN:
    raise ValueError("❌ TELEGRAM_TOKEN não definido no .env")
if not SPREADSHEET_ID:
    raise ValueError("❌ SPREADSHEET_ID não definido no .env")
# GEMINI_API_KEY é opcional — fallback simplesmente não será acionado sem ela
