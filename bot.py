import asyncio
import html
import logging
import os
import tempfile
from pathlib import Path
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters, CommandHandler
import google.generativeai as genai

# 1. Configurações Iniciais
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
AUTHORIZED_USER_ID = os.getenv("AUTHORIZED_USER_ID")

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# 2. Configurar Gemini (Versão 2026 - Gemini 2.5 Flash)
genai.configure(api_key=GEMINI_API_KEY)

# Definimos o modelo que sua conta validou como ativo
MODEL_NAME = "models/gemini-2.5-flash"
model = genai.GenerativeModel(model_name=MODEL_NAME)

def is_authorized(user_id: int) -> bool:
    """Trava de segurança para o seu ID do Telegram."""
    return str(user_id) == str(AUTHORIZED_USER_ID)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando inicial do bot."""
    if is_authorized(update.effective_user.id):
        await update.message.reply_text("👷 GessoBot Online! Pode mandar os dados da obra.")
    else:
        await update.message.reply_text("⛔ Acesso não autorizado.")

async def process_content(update: Update, content_type: str, file_path: Path = None):
    """Envia o conteúdo (texto ou áudio) para a IA e retorna o resumo."""
    # Este prompt prepara o terreno para a futura integração com planilhas
    prompt = (
        "Você é um assistente de gestão para gesseiros. "
        "Extraia os dados da mensagem e responda EXATAMENTE neste formato:\n"
        "Cliente: [Nome]\n"
        "Serviço: [O que foi feito]\n"
        "Valor: [R$]\n"
        "Status: [Pago/Pendente/Orçamento]"
    )
    
    try:
        if content_type == "voice":
            # O Gemini 2.5 'ouve' o arquivo diretamente
            audio_file = genai.upload_file(path=str(file_path), mime_type="audio/ogg")
            response = model.generate_content([prompt, audio_file])
        else:
            response = model.generate_content(f"{prompt}\n\nMensagem: {update.message.text}")
        
        await update.message.reply_text(f"<b>Resumo da Obra:</b>\n\n{html.escape(response.text)}", parse_mode="HTML")
    except Exception as e:
        logger.error(f"Erro na IA: {e}")
        await update.message.reply_text(f"❌ Erro ao processar: {str(e)}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lida com mensagens de texto."""
    if is_authorized(update.effective_user.id):
        await update.message.reply_text("⏳ Analisando texto...")
        await process_content(update, "text")

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lida com áudios (Voice Notes)."""
    if not is_authorized(update.effective_user.id): return
    
    await update.message.reply_text("⏳ Ouvindo áudio...")
    voice = update.message.voice
    tg_file = await context.bot.get_file(voice.file_id)
    
    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
        tmp_path = Path(tmp.name)
        await tg_file.download_to_drive(custom_path=tmp_path)
        try:
            await process_content(update, "voice", tmp_path)
        finally:
            if tmp_path.exists(): tmp_path.unlink()

def main():
    """Inicia o bot."""
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    
    logger.info(f"Bot iniciado com o modelo {MODEL_NAME}")
    app.run_polling()

if __name__ == "__main__":
    main()