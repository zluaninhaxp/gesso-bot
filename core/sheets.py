"""
core/sheets.py — Integração com Google Sheets para o GessoBot.

Estrutura da planilha:
  Aba "Receitas"          → toda entrada de dinheiro
  Aba "Despesas Serviço"  → gastos ligados ao negócio
  Aba "Despesas Pessoal"  → gastos da vida pessoal
  Aba "Não Classificado"  → eventos que precisam revisão manual

Cada aba tem colunas:
  Data/Hora | Dia Semana | Tipo | Tags | Valor (R$) | Cliente |
  Descrição | Frase Original | Aviso

Autenticação: Service Account (JSON key definido em .env).
"""

import re
import logging
from datetime import datetime

import gspread
from google.oauth2.service_account import Credentials

from core.config import SHEETS_CREDENTIALS_PATH, SPREADSHEET_ID

logger = logging.getLogger(__name__)

# ============================================================
# ESCOPOS DO GOOGLE
# ============================================================

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# ============================================================
# MAPEAMENTO EVENTO → ABA
# ============================================================

ABA_POR_TIPO = {
    "receita":           "Receitas",
    "despesa_servico":   "Despesas Serviço",
    "despesa_pessoal":   "Despesas Pessoal",
    "despesa":           "Não Classificado",
    "nao_classificado":  "Não Classificado",
}

# ============================================================
# CABEÇALHOS (mesma ordem em todas as abas)
# ============================================================

CABECALHO = [
    "Data/Hora",
    "Dia Semana",
    "Tipo",
    "Tags",
    "Valor (R$)",
    "Cliente",
    "Descrição",  # descrição limpa se disponível; senão, frase original completa
    "Aviso",
]

# ============================================================
# CLIENTE GSPREAD (singleton simples)
# ============================================================

_gc = None

def _get_client() -> gspread.Client:
    global _gc
    if _gc is None:
        creds = Credentials.from_service_account_file(
            SHEETS_CREDENTIALS_PATH, scopes=SCOPES
        )
        _gc = gspread.authorize(creds)
    return _gc


def _get_sheet(nome_aba: str) -> gspread.Worksheet:
    """Retorna a aba pelo nome, criando-a se não existir."""
    gc = _get_client()
    spreadsheet = gc.open_by_key(SPREADSHEET_ID)

    try:
        ws = spreadsheet.worksheet(nome_aba)
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=nome_aba, rows=1000, cols=len(CABECALHO))
        ws.append_row(CABECALHO, value_input_option="RAW")
        # Formata cabeçalho: negrito + fundo cinza
        _formatar_cabecalho(spreadsheet, ws)
        logger.info(f"Aba '{nome_aba}' criada.")

    return ws


def _formatar_cabecalho(spreadsheet: gspread.Spreadsheet, ws: gspread.Worksheet):
    """Aplica formatação básica ao cabeçalho da aba."""
    try:
        sheet_id = ws.id
        n_cols = len(CABECALHO)
        requests = [
            {
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 0,
                        "endRowIndex": 1,
                        "startColumnIndex": 0,
                        "endColumnIndex": n_cols,
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": {"red": 0.2, "green": 0.2, "blue": 0.2},
                            "textFormat": {
                                "bold": True,
                                "foregroundColor": {"red": 1, "green": 1, "blue": 1},
                            },
                            "horizontalAlignment": "CENTER",
                        }
                    },
                    "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)",
                }
            },
            # Congela a primeira linha
            {
                "updateSheetProperties": {
                    "properties": {
                        "sheetId": sheet_id,
                        "gridProperties": {"frozenRowCount": 1},
                    },
                    "fields": "gridProperties.frozenRowCount",
                }
            },
        ]
        spreadsheet.batch_update({"requests": requests})
    except Exception as e:
        logger.warning(f"Não foi possível formatar cabeçalho: {e}")


# ============================================================
# NORMALIZAÇÃO DE VALOR
# ============================================================

def _normalizar_valor(valor_str: str) -> str:
    """
    Converte string de valor para float e formata como moeda brasileira.
    Aceita: '2.500', '2500', '1.200,50', '1200.50'
    Retorna: '2500.00' (float string para o Sheets calcular)
    """
    if not valor_str:
        return ""
    v = valor_str.strip()
    # Remove pontos de milhar e converte vírgula decimal
    if "." in v and "," in v:
        # 1.200,50 → 1200.50
        v = v.replace(".", "").replace(",", ".")
    elif "." in v and v.count(".") == 1 and len(v.split(".")[-1]) != 3:
        # 1200.50 → já é decimal
        pass
    elif "." in v:
        # 2.500 → 2500 (ponto de milhar)
        v = v.replace(".", "")
    elif "," in v:
        # 2500,50 → 2500.50
        v = v.replace(",", ".")
    try:
        return str(float(v))
    except ValueError:
        return valor_str


# ============================================================
# MONTAR LINHA
# ============================================================

def _montar_linha(evento: dict, frase_original: str, timestamp: datetime) -> list:
    """
    Monta a lista de valores que vai para uma linha do Sheets.
    Ordem: CABECALHO
    """
    dados = evento.get("dados", {})
    tipo  = evento.get("tipo", "")

    data_hora = timestamp.strftime("%d/%m/%Y %H:%M")
    dias      = ", ".join(dados.get("dias", [])) if dados.get("dias") else ""
    tags      = ", ".join(dados.get("tags", [])) if dados.get("tags") else ""
    valor     = _normalizar_valor(dados.get("valor", ""))
    cliente   = dados.get("cliente", "")
    aviso     = dados.get("aviso", "")

    # Descrição: usa a descrição limpa se existir e for informativa;
    # caso contrário, usa a frase original como fallback
    descricao_limpa = (dados.get("descricao") or "").strip()
    descricao = descricao_limpa if descricao_limpa else frase_original

    return [
        data_hora,  # Data/Hora
        dias,       # Dia Semana
        tipo,       # Tipo
        tags,       # Tags
        valor,      # Valor (R$)
        cliente,    # Cliente
        descricao,  # Descrição (limpa ou frase original como fallback)
        aviso,      # Aviso
    ]


# ============================================================
# FUNÇÃO PRINCIPAL
# ============================================================

def registrar_eventos(eventos: list, frase_original: str) -> dict:
    """
    Recebe a lista de eventos do classifier e registra cada um
    na aba correta do Google Sheets.

    Retorna um dict com o resumo do que foi registrado:
    {
        "sucesso": [...nomes das abas onde registrou...],
        "erros":   [...mensagens de erro...]
    }
    """
    timestamp = datetime.now()
    resultado = {"sucesso": [], "erros": []}

    for evento in eventos:
        tipo     = evento.get("tipo", "nao_classificado")
        nome_aba = ABA_POR_TIPO.get(tipo, "Não Classificado")

        try:
            ws   = _get_sheet(nome_aba)
            linha = _montar_linha(evento, frase_original, timestamp)
            ws.append_row(linha, value_input_option="USER_ENTERED")
            resultado["sucesso"].append(nome_aba)
            logger.info(f"Evento '{tipo}' registrado em '{nome_aba}'.")
        except Exception as e:
            msg = f"Erro ao registrar em '{nome_aba}': {e}"
            logger.error(msg)
            resultado["erros"].append(msg)

    return resultado


# ============================================================
# INICIALIZAÇÃO: garante que todas as abas existem
# ============================================================

def inicializar_planilha():
    """
    Garante que todas as abas necessárias existem com cabeçalho correto.
    Chamar uma vez no startup do bot.
    """
    abas = list(dict.fromkeys(ABA_POR_TIPO.values()))  # mantém ordem, sem duplicatas
    for nome_aba in abas:
        try:
            _get_sheet(nome_aba)
        except Exception as e:
            logger.error(f"Erro ao inicializar aba '{nome_aba}': {e}")
    logger.info("Planilha inicializada.")
