import logging
import os
import re
import json
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters, CommandHandler

# =============================
# CONFIGURAÇÕES
# =============================

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
AUTHORIZED_USER_ID = os.getenv("AUTHORIZED_USER_ID")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =============================
# SEGURANÇA
# =============================

def is_authorized(user_id: int) -> bool:
    return str(user_id) == str(AUTHORIZED_USER_ID)

# =============================
# EXTRAÇÕES
# =============================

def extract_valor(frase):
    match = re.search(r'(\d+[.,]?\d*)', frase)
    return match.group(1) if match else ""

def extract_nome(frase):
    match = re.search(
        r'\b([A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-záéíóúâêôãõç]+)\b',
        frase
    )
    return match.group(1) if match else ""

def extract_dias(frase):
    return re.findall(
        r"(segunda|terça|quarta|quinta|sexta|sábado|domingo)",
        frase.lower()
    )

# =============================
# CLASSIFICAÇÃO INTELIGENTE
# =============================

def classify_text(texto):

    eventos = []

    # Divide frases por ponto
    frases = re.split(r'\.\s*', texto)

    for frase in frases:
        frase = frase.strip()
        if not frase:
            continue

        frase_lower = frase.lower()

        # =============================
        # ORÇAMENTO (separa múltiplos clientes)
        # =============================

        if "orçamento" in frase_lower:

             # Encontra todos os clientes após "com"
            clientes = re.findall(
                r'com\s+(?:a\s+|o\s+)?([A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-záéíóúâêôãõç]+)',
                frase
            )

            # Encontra todos os dias na frase
            dias = extract_dias(frase)

            # Se quantidade bater, associa por ordem
            if len(clientes) == len(dias):
                for cliente, dia in zip(clientes, dias):
                    eventos.append({
                        "tipo": "orcamento_agendado",
                        "dados": {
                            "cliente": cliente,
                            "dias": [dia]
                        }
                    })
            else:
                # fallback simples: associa todos dias ao primeiro cliente
                for cliente in clientes:
                    eventos.append({
                        "tipo": "orcamento_agendado",
                        "dados": {
                            "cliente": cliente,
                            "dias": dias
                        }
                    })

            continue

        # =============================
        # RECEITA
        # =============================

        if any(p in frase_lower for p in ["recebi", "me pagou", "transferiu"]):

            nome_match = re.search(r'\b([A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-záéíóúâêôãõç]+)\b', frase)
            cliente = nome_match.group(1) if nome_match else ""

            eventos.append({
                "tipo": "receita",
                "dados": {
                    "cliente": cliente,
                    "valor": extract_valor(frase)
                }
            })
            continue

        # =============================
        # TAREFA (obra, casa, ir, terminar, revisar)
        # =============================

        if any(p in frase_lower for p in [
            "tenho que", "preciso", "ir", "terminar", "revisar"
        ]):

            cliente_match = re.search(
                r'(?:do|da|na|no|de)\s+([A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-záéíóúâêôãõç]+)',
                frase
            )

            cliente = cliente_match.group(1) if cliente_match else ""

            eventos.append({
                "tipo": "tarefa",
                "dados": {
                    "cliente": cliente,
                    "descricao": frase,
                    "dias": extract_dias(frase)
                }
            })
            continue

        # =============================
        # DESPESA
        # =============================

        if any(p in frase_lower for p in ["paguei", "comprei", "gastei"]):
            eventos.append({
                "tipo": "despesa",
                "dados": {
                    "descricao": frase,
                    "valor": extract_valor(frase)
                }
            })
            continue

        # =============================
        # NÃO CLASSIFICADO
        # =============================

        eventos.append({
            "tipo": "nao_classificado",
            "dados": {
                "descricao": frase
            }
        })

    return eventos

# =============================
# PROCESSAMENTO PRINCIPAL
# =============================

async def process_content(update, content_type):

    user_text = update.message.text

    eventos = classify_text(user_text)

    if not eventos:
        await update.message.reply_text("⚠ Nenhuma informação reconhecida.")
        return

    for i, evento in enumerate(eventos, start=1):
        await update.message.reply_text(
            f"📌 Evento {i} - {evento['tipo']}\n"
            f"{json.dumps(evento['dados'], indent=2, ensure_ascii=False)}"
        )

# =============================
# HANDLERS
# =============================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_authorized(update.effective_user.id):
        await update.message.reply_text("👷 GessoBot Online.")
    else:
        await update.message.reply_text("⛔ Acesso não autorizado.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_authorized(update.effective_user.id):
        await process_content(update, "text")

# =============================
# MAIN
# =============================

def main():

    if not TELEGRAM_TOKEN:
        print("❌ TELEGRAM_TOKEN não encontrado no .env")
        return

    print("🚀 Iniciando GessoBot...")

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("✅ Bot rodando.")
    app.run_polling()

if __name__ == "__main__":
    main()