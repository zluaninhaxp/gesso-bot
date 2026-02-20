import asyncio
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
# CONFIGURAÇÕES
# =============================

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
AUTHORIZED_USER_ID = os.getenv("AUTHORIZED_USER_ID")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Gemini (usado apenas como fallback)
genai.configure(api_key=GEMINI_API_KEY)
MODEL_NAME = "models/gemini-2.5-flash"
model = genai.GenerativeModel(model_name=MODEL_NAME)

# =============================
# SEGURANÇA
# =============================

def is_authorized(user_id: int) -> bool:
    return str(user_id) == str(AUTHORIZED_USER_ID)

# =============================
# CLASSIFICAÇÃO LOCAL (SEM IA)
# =============================

def extract_valor(frase):
    match = re.search(r'(\d+[.,]?\d*)', frase)
    return match.group(1) if match else ""

def extract_nome_depois_de(frase, palavra):
    match = re.search(rf'{palavra}\s+([A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-záéíóúâêôãõç]+)', frase, re.IGNORECASE)
    return match.group(1) if match else ""

def classify_locally(text):
    eventos = []
    frases = re.split(r'[.]\s*', text)

    for frase in frases:
        frase_lower = frase.lower().strip()
        if not frase_lower:
            continue

        # RECEITA
        if any(p in frase_lower for p in ["recebi", "me pagou", "pagamento"]):
            eventos.append({
                "tipo": "receita",
                "dados": {
                    "cliente": extract_nome_depois_de(frase, "de") or extract_nome_depois_de(frase, "do"),
                    "valor": extract_valor(frase),
                    "status": "pago"
                }
            })
            continue

        # DESPESA
        if any(p in frase_lower for p in ["paguei", "comprei", "gastei"]):
            eventos.append({
                "tipo": "despesa",
                "dados": {
                    "descricao": frase.strip(),
                    "valor": extract_valor(frase)
                }
            })
            continue

        # ORÇAMENTO
        if "orçamento" in frase_lower:
            eventos.append({
                "tipo": "orcamento_agendado",
                "dados": {
                    "cliente": extract_nome_depois_de(frase, "com"),
                    "data": ""
                }
            })
            continue

        # TAREFA
        if any(p in frase_lower for p in ["vou", "preciso", "devo"]):
            eventos.append({
                "tipo": "tarefa",
                "dados": {
                    "descricao": frase.strip()
                }
            })
            continue

        # NÃO IDENTIFICADO → fallback IA
        eventos.append({
            "tipo": "complexo",
            "dados": {
                "texto_original": frase.strip()
            }
        })

    return eventos

# =============================
# FALLBACK IA (SÓ SE PRECISAR)
# =============================

def extract_with_ai(texto):
    prompt = f"""
    Extraia evento estruturado da seguinte frase:

    "{texto}"

    Retorne JSON no formato:
    {{
        "tipo": "",
        "dados": {{}}
    }}
    """

    response = model.generate_content(prompt)
    response_text = response.text

    match = re.search(r"\{.*\}", response_text, re.DOTALL)
    if not match:
        return None

    return json.loads(match.group(0))

# =============================
# PROCESSAMENTO PRINCIPAL
# =============================

async def process_content(update, content_type, file_path=None):
    try:
        # 1️⃣ Transcrição se for áudio
        if content_type == "voice":
            audio_file = genai.upload_file(path=str(file_path), mime_type="audio/ogg")
            response = model.generate_content(["Transcreva em português:", audio_file])
            user_text = response.text
        else:
            user_text = update.message.text

        # 2️⃣ Classificação local
        eventos = classify_locally(user_text)

        # 3️⃣ Processa fallback IA
        eventos_finais = []
        for evento in eventos:
            if evento["tipo"] == "complexo":
                resultado_ai = extract_with_ai(evento["dados"]["texto_original"])
                if resultado_ai:
                    eventos_finais.append(resultado_ai)
            else:
                eventos_finais.append(evento)

        # 4️⃣ Enviar resposta
        for i, evento in enumerate(eventos_finais, start=1):
            await update.message.reply_text(
                "Evento {} - Tipo: {}\n{}".format(
                    i,
                    evento["tipo"],
                    json.dumps(evento["dados"], indent=2, ensure_ascii=False)
                )
            )

    except Exception as e:
        logger.error(str(e))
        await update.message.reply_text(f"Erro: {str(e)}")

# =============================
# HANDLERS
# =============================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_authorized(update.effective_user.id):
        await update.message.reply_text("👷 GessoBot Inteligente Online.")
    else:
        await update.message.reply_text("⛔ Acesso não autorizado.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_authorized(update.effective_user.id):
        await process_content(update, "text")

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        return

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
# INICIALIZAÇÃO
# =============================

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))

    logger.info("Bot iniciado com arquitetura híbrida.")
    app.run_polling()

if __name__ == "__main__":
    main()