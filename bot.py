import json
import logging

from telegram import Update
from telegram.ext import (
    Application,
    ContextTypes,
    MessageHandler,
    CommandHandler,
    filters,
)

from core.config import TELEGRAM_TOKEN
from core.security import is_authorized
from core.classifier import classify_text


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Responde ao /start."""
    user_id = update.effective_user.id if update.effective_user else None
    if not user_id:
        return

    if is_authorized(user_id):
        await update.message.reply_text("👷 GessoBot Online.")
    else:
        await update.message.reply_text("⛔ Acesso não autorizado.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Processa mensagens de texto normais."""
    user_id = update.effective_user.id if update.effective_user else None
    if not user_id or not is_authorized(user_id):
        return

    if not update.message or not update.message.text:
        return

    user_text = update.message.text
    eventos = classify_text(user_text)

    if not eventos:
        await update.message.reply_text("⚠ Nenhuma informação reconhecida.")
        return

    for i, evento in enumerate(eventos, start=1):
        resposta = (
            f"📌 Evento {i} - {evento['tipo']}\n"
            f"{json.dumps(evento['dados'], indent=2, ensure_ascii=False)}"
        )
        await update.message.reply_text(resposta)


def main() -> None:
    """Inicializa o bot de forma simples."""
    if not TELEGRAM_TOKEN:
        raise ValueError("❌ TELEGRAM_TOKEN não definido no .env")

    print("🚀 Iniciando GessoBot...")

    app: Application = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("✅ Bot rodando.")
    app.run_polling()


if __name__ == "__main__":
    main()
