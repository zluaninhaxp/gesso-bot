import asyncio
import html
import logging
import os
import tempfile
import json
import re
from pathlib import Path
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters, CommandHandler
import google.generativeai as genai

# =============================
# 1. Configurações Iniciais
# =============================

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
AUTHORIZED_USER_ID = os.getenv("AUTHORIZED_USER_ID")

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# =============================
# 2. Configurar Gemini
# =============================

genai.configure(api_key=GEMINI_API_KEY)

MODEL_NAME = "models/gemini-2.5-flash"
model = genai.GenerativeModel(model_name=MODEL_NAME)

# =============================
# 3. Segurança
# =============================

def is_authorized(user_id: int) -> bool:
    return str(user_id) == str(AUTHORIZED_USER_ID)

# =============================
# 4. Comando /start
# =============================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_authorized(update.effective_user.id):
        await update.message.reply_text("👷 GessoBot Online! Pode mandar os dados.")
    else:
        await update.message.reply_text("⛔ Acesso não autorizado.")

# =============================
# 5. Prompt Inteligente
# =============================

def build_prompt(user_message: str) -> str:
    return f"""
Você é um assistente de gestão para um gesseiro.

Classifique a mensagem abaixo em UM dos seguintes tipos: orcamento_agendado, receita, despesa.

Responda APENAS em JSON válido. Não escreva nada fora do JSON. Não adicione comentários ou prefixos.

FORMATOS:

Se for orcamento_agendado:
{{
  "tipo": "orcamento_agendado",
  "dados": {{
    "cliente": "",
    "data": "",
    "local": ""
  }}
}}

Se for receita:
{{
  "tipo": "receita",
  "dados": {{
    "cliente": "",
    "servico": "",
    "valor": "",
    "status": "pago ou pendente"
  }}
}}

Se for despesa:
{{
  "tipo": "despesa",
  "dados": {{
    "descricao": "",
    "valor": "",
    "pago_para": ""
  }}
}}

Mensagem: "{user_message}"
"""

# =============================
# 6. Processamento IA
# =============================

async def process_content(update: Update, content_type: str, file_path: Path = None):
    try:
        # ---------------------------
        # 1️⃣ Pegar texto do usuário
        # ---------------------------
        if content_type == "voice":
            # Upload do áudio
            audio_file = genai.upload_file(path=str(file_path), mime_type="audio/ogg")
            # Transcrição
            transcription_response = model.generate_content([
                "Transcreva este áudio em português.",
                audio_file
            ])
            user_text = getattr(transcription_response, "text", None)
            if not user_text:
                user_text = transcription_response.candidates[0].content
        else:
            user_text = update.message.text

        # ---------------------------
        # 2️⃣ Criar prompt e gerar JSON
        # ---------------------------
        prompt = build_prompt(user_text)
        response = model.generate_content(prompt)

        # Captura do texto da resposta corretamente
        response_text = getattr(response, "text", None)
        if not response_text:
            response_text = response.candidates[0].content

        # ---------------------------
        # 3️⃣ Extrair JSON mesmo com lixo extra
        # ---------------------------
        match = re.search(r"\{.*\}", response_text, re.DOTALL)
        if not match:
            raise ValueError("Não foi possível extrair JSON da resposta da IA.")

        json_text = match.group(0)
        data = json.loads(json_text)

        tipo = data.get("tipo")
        dados = data.get("dados")

        # ---------------------------
        # 4️⃣ Enviar confirmação pro usuário
        # ---------------------------
        mensagem_confirmacao = (
            f"✅ Tipo identificado: {tipo}\n\n"
            f"{json.dumps(dados, indent=2, ensure_ascii=False)}"
        )
        await update.message.reply_text(mensagem_confirmacao)

        # ---------------------------
        # 5️⃣ Aqui você pode salvar no Google Sheets
        # salvar_no_sheets(tipo, dados)
        # ---------------------------

    except json.JSONDecodeError:
        logger.error("Erro ao converter JSON da IA.")
        await update.message.reply_text("⚠️ A IA não retornou JSON válido. Tente novamente.")

    except Exception as e:
        logger.error(f"Erro geral: {e}")
        await update.message.reply_text(f"❌ Erro ao processar: {str(e)}")

# =============================
# 7. Handlers
# =============================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_authorized(update.effective_user.id):
        await update.message.reply_text("⏳ Analisando texto...")
        await process_content(update, "text")

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        return

    await update.message.reply_text("⏳ Ouvindo áudio...")
    voice = update.message.voice
    tg_file = await context.bot.get_file(voice.file_id)

    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
        tmp_path = Path(tmp.name)
        await tg_file.download_to_drive(custom_path=tmp_path)
        try:
            await process_content(update, "voice", tmp_path)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

# =============================
# 8. Inicialização
# =============================

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))

    logger.info(f"Bot iniciado com o modelo {MODEL_NAME}")
    app.run_polling()

if __name__ == "__main__":
    main()