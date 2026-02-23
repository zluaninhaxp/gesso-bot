"""
bot.py — GessoBot: controle financeiro via Telegram.
"""

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
from core.sheets import registrar_eventos, inicializar_planilha

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ============================================================
# FORMATAÇÃO DA RESPOSTA DO BOT
# ============================================================

EMOJI_TIPO = {
    "receita":          "💰",
    "despesa_servico":  "🔧",
    "despesa_pessoal":  "🏠",
    "despesa":          "❓",
    "nao_classificado": "⚠️",
}

NOME_TIPO = {
    "receita":          "Receita",
    "despesa_servico":  "Despesa de Serviço",
    "despesa_pessoal":  "Despesa Pessoal",
    "despesa":          "Despesa (sem categoria)",
    "nao_classificado": "Não classificado",
}

def formatar_evento(evento: dict, idx: int) -> str:
    """Monta a mensagem de confirmação de um evento para o usuário."""
    tipo  = evento.get("tipo", "")
    dados = evento.get("dados", {})

    emoji = EMOJI_TIPO.get(tipo, "📌")
    nome  = NOME_TIPO.get(tipo, tipo)

    linhas = [f"{emoji} *Evento {idx} — {nome}*"]

    if dados.get("valor"):
        linhas.append(f"  💵 Valor: R$ {dados['valor']}")

    if dados.get("cliente"):
        linhas.append(f"  👤 Cliente: {dados['cliente']}")

    if dados.get("tags"):
        tags_fmt = " · ".join(f"`{t}`" for t in dados["tags"])
        linhas.append(f"  🏷 Tags: {tags_fmt}")

    if dados.get("dias"):
        linhas.append(f"  📅 Dia(s): {', '.join(dados['dias'])}")

    if dados.get("descricao"):
        linhas.append(f"  📝 Desc: _{dados['descricao']}_")

    if dados.get("aviso"):
        linhas.append(f"  ⚠️ Aviso: {dados['aviso']}")

    return "\n".join(linhas)


# ============================================================
# HANDLERS
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id if update.effective_user else None
    if not user_id:
        return

    if is_authorized(user_id):
        await update.message.reply_text(
            "👷 *GessoBot Online.*\n\n"
            "Me manda o que aconteceu financeiramente e eu registro na planilha.\n\n"
            "Exemplos:\n"
            "• _Recebi 2500 do João pelo serviço_\n"
            "• _Comprei tinta por 300 e paguei o ajudante 200_\n"
            "• _Fui no mercado, gastei 180_",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("⛔ Acesso não autorizado.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id if update.effective_user else None
    if not user_id or not is_authorized(user_id):
        return
    if not update.message or not update.message.text:
        return

    frase = update.message.text
    eventos = classify_text(frase)

    if not eventos:
        await update.message.reply_text("⚠️ Nenhuma informação financeira reconhecida.")
        return

    # Monta resposta de confirmação
    linhas_resposta = []
    for i, evento in enumerate(eventos, 1):
        linhas_resposta.append(formatar_evento(evento, i))

    # Registra no Sheets
    resultado = registrar_eventos(eventos, frase)

    # Feedback de registro
    if resultado["erros"]:
        linhas_resposta.append(
            f"\n❌ Erro ao salvar na planilha:\n" + "\n".join(resultado["erros"])
        )
    else:
        n = len(resultado["sucesso"])
        linhas_resposta.append(f"\n✅ {n} registro(s) salvo(s) na planilha.")

    await update.message.reply_text(
        "\n\n".join(linhas_resposta),
        parse_mode="Markdown"
    )


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    if not TELEGRAM_TOKEN:
        raise ValueError("❌ TELEGRAM_TOKEN não definido no .env")

    print("🚀 Iniciando GessoBot...")

    # Garante que as abas existem antes de começar
    try:
        inicializar_planilha()
        print("✅ Planilha inicializada.")
    except Exception as e:
        print(f"⚠️  Aviso: não foi possível inicializar planilha: {e}")

    app: Application = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("✅ Bot rodando.")
    app.run_polling()


if __name__ == "__main__":
    main()
