"""
core/classifier.py
==================
Classificador financeiro em duas camadas:

  Camada 1 — Regex (rápido, gratuito)
    Tenta identificar eventos por vocabulário expandido e split por contexto.
    Cobre linguagem formal, informal e coloquial.

  Camada 2 — Gemini (fallback inteligente)
    Acionado quando o regex retorna nao_classificado ou despesa genérica.
    Interpreta linguagem livre, sem pontuação, gírias e expressões informais.

Fluxo:
  texto → split_intencoes() → regex classifier → se inconclusivo → Gemini
        → normalizar_evento_gemini() → lista de eventos padronizados
"""

import re
import json
import logging

logger = logging.getLogger(__name__)

# ================================================================
# VOCABULÁRIO — RECEITA
# Formal + informal + coloquial + erros ortográficos comuns
# ================================================================

PALAVRAS_RECEITA = [
    # Formal
    "recebi", "recebemos", "recebeu",
    "me pagou", "nos pagou", "pagou",
    "transferiu", "fez transferência", "fez transferencia",
    "depositou", "fez depósito", "fez deposito",
    "pagamento recebido", "pagamento efetuado",
    "faturei", "faturamos",
    "cobrei", "cobramos",
    # Informal/coloquial
    "caiu na conta", "caiu no pix", "caiu",
    "entrou na conta", "entrou no pix", "entrou",
    "me mandou", "me mandaram", "mandou",
    "me passou", "me passaram",
    "me enviou", "enviou",
    "pagaram", "me pagaram", "nos pagaram",
    "quitou", "quitaram",
    "acertou", "acertaram", "me acertou", "me acertaram",
    "liquidou", "liquidaram",
    "depositaram",
    "recebi pix", "pix caiu", "pix entrou",
    "me pagaram", "pagaram",
    "virou", "caiu grana", "veio dinheiro",
    "recebi grana", "recebi dinheiro",
    "recebi o valor", "recebi os valores",
    "fechei serviço", "fechei trabalho",
    "ganhei", "ganhamos",
    "liquidaram", "liquidou",
    "quitaram", "quitou",
    "acertamos", "acertou",
    "me acertou", "me acertaram",
]

# ================================================================
# VOCABULÁRIO — DESPESA (gatilhos de que é um gasto)
# ================================================================

PALAVRAS_DESPESA = [
    # Formal
    "paguei", "pagamos", "pagou",
    "comprei", "compramos", "comprou",
    "gastei", "gastamos", "gastou", "gasto",
    "despesa", "despesas",
    "custou", "custo",
    "desembolsei", "desembolsamos",
    "adquiri", "adquirimos",
    "investi", "investimos",
    "contratei", "contratamos",
    # Informal/coloquial
    "coloquei", "coloquei dinheiro",
    "tirei da conta", "tirei do bolso", "tirei",
    "aluguei", "alugamos",
    "transferi", "mandei dinheiro", "mandei",
    "debitou", "debitaram",
    "pedi", "pedi comida", "fiz um pedido", "pedi no",
    "fui no mercado", "fui no supermercado", "fui na farmácia",
    "fui na farmacia", "fui no restaurante", "fui na padaria",
    "fui no açougue", "fui na feira", "fui na loja",
    "passei no mercado", "passei na farmácia",
    "passei no supermercado", "passei na padaria",
    "saiu", "saiu dinheiro", "foi embora", "foi",
    "botei", "botamos",
    "abasteci", "abastecemos",
    "enchi o tanque", "enchemos o tanque",
    "repus", "reposição",
    "consertei", "consertamos",
    "arrumei",
    "tô devendo", "to devendo", "devo",  # passivo mas financeiro
]

# ================================================================
# TAGS — DESPESA DE SERVIÇO
# (palavra, usa_word_boundary)
# ================================================================

TAGS_SERVICO_RAW = {
    "funcionario": [
        # Formal
        ("funcionário", False), ("funcionario", False),
        ("funcionária", False), ("funcionaria", False),
        ("colaborador", True), ("colaboradora", True),
        ("empregado", True), ("empregada", True),
        ("contratado", True), ("contratada", True),
        ("empreiteiro", True), ("empreiteira", True),
        ("subcontratado", True), ("terceirizado", True),
        ("prestador", True), ("prestadora", True),
        ("mestre de obra", False), ("mestre", True),
        ("servente", True),
        # Informal
        ("ajudante", True), ("ajudante de obra", False),
        ("peão", True), ("piao", True), ("peão de obra", False),
        ("diarista", True),
        ("diária", True), ("diaria", True),
        ("mão de obra", False), ("mao de obra", False),
        ("mão", True),  # "paguei a mão"
        ("rapaziada", True), ("rapazes", True),  # "paguei a rapaziada"
        ("galera", True),  # "paguei a galera"
        ("pessoal da obra", False), ("pessoal do serviço", False),
        ("equipe", True),
    ],
    "material": [
        # Materiais de construção/pintura
        ("tinta", True), ("tintão", True),
        ("gesso", True), ("cimento", True),
        ("areia", True), ("brita", True),
        ("argamassa", True), ("rejunte", True),
        ("parafuso", True), ("prego", True),
        ("madeira", True), ("madeiramento", True),
        ("massa corrida", False), ("massa", True),
        ("fio", True), ("cabo", True),
        ("tubo", True), ("cano", True),
        ("lixa", True), ("rolo", True), ("rolo de pintura", False),
        ("pincel", True), ("brocha", True),
        ("primer", True), ("selador", True),
        ("impermeabilizante", True), ("impermeabilização", True),
        ("cola", True), ("vedante", True),
        ("placa", True), ("placa de drywall", False), ("drywall", True),
        ("tijolo", True), ("bloco", True),
        ("cal", True),
        ("piso", True), ("porcelanato", True), ("cerâmica", True), ("ceramica", True),
        ("telha", True), ("cumeeira", True),
        ("insumo", True),
        # Gatilhos genéricos (apenas quando é objeto direto)
        ("materiais", True),
        ("comprei material", False), ("gastei com material", False),
        ("compra de material", False), ("material de obra", False),
        ("material para obra", False), ("material para o serviço", False),
    ],
    "ferramenta": [
        ("ferramenta", True), ("ferramentas", True),
        ("equipamento", True), ("equipamentos", True),
        ("furadeira", True), ("martelete", True),
        ("esmerilhadeira", True), ("esmeril", True),
        ("betoneira", True), ("misturador", True),
        ("andaime", True), ("andaimes", True),
        ("escada", True),
        ("mangueira", True), ("compressor", True),
        ("gerador", True), ("motosserra", True),
        ("aluguel de equipamento", False), ("locação de equipamento", False),
        ("aluguel de ferramenta", False), ("locação de ferramenta", False),
    ],
    "transporte": [
        # Combustível
        ("gasolina", True), ("combustível", True), ("combustivel", True),
        ("diesel", True), ("etanol", True), ("álcool", True), ("alcool", True),
        ("abasteci", True), ("abastecemos", True), ("enchi o tanque", False),
        # Serviços de transporte
        ("frete", True), ("fretes", True),
        ("pedágio", True), ("pedagio", True),
        ("estacionamento", True),
        ("uber", True), ("99", True), ("táxi", True), ("taxi", True),
        ("passagem", True),
        # Manutenção do veículo de trabalho
        ("aluguel da van", False), ("aluguel do carro", False),
        ("aluguel da caminhonete", False),
        ("manutenção do carro", False), ("manutenção da van", False),
        ("conserto do carro", False), ("revisão do carro", False),
        ("troca de óleo", False), ("troca de pneu", False),
        ("deslocamento", True), ("translado", True),
    ],
    "imposto": [
        ("imposto", True), ("impostos", True),
        ("nota fiscal", False), ("nf", True),
        ("simples nacional", False), ("simples", True),
        ("das", True), ("iss", True),
        ("inss", True), ("fgts", True),
        ("contador", True), ("contadora", True), ("contabilidade", True),
        ("taxa", True), ("taxas", True),
        ("alvará", True), ("alvara", True),
        ("licença", True), ("licenca", True),
    ],
}

# ================================================================
# TAGS — DESPESA PESSOAL
# ================================================================

TAGS_PESSOAL_RAW = {
    "alimentacao": [
        # Lugares
        ("mercado", True), ("supermercado", True), ("hipermercado", True),
        ("feira", True), ("quitanda", True),
        ("açougue", True), ("acougue", True), ("peixaria", True),
        ("padaria", True), ("confeitaria", True),
        ("restaurante", True), ("lanchonete", True),
        ("pizzaria", True), ("hamburgueria", True),
        # Refeições e itens
        ("lanche", True), ("refeição", True), ("refeicao", True),
        ("almoço", True), ("almoco", True),
        ("janta", True), ("jantar", True), ("ceia", True),
        ("café", True), ("cafezinho", True),
        ("café da manhã", False), ("cafe da manha", False),
        ("marmita", True),
        # Apps/delivery
        ("ifood", True), ("delivery", True), ("rappi", True),
        ("uber eats", False),
        # Itens
        ("pizza", True), ("hamburguer", True), ("hamburger", True),
        ("comida", True), ("alimento", True), ("alimentação", True), ("alimentacao", True),
        ("rancho", True),  # compra do mês no nordeste
        ("feira do mês", False), ("compras do mês", False),
    ],
    "moradia": [
        ("aluguel da casa", False), ("aluguel do apartamento", False),
        ("aluguel do apto", False), ("aluguel", True),
        ("condomínio", True), ("condominio", True),
        ("conta de luz", False), ("conta de água", False), ("conta de agua", False),
        ("conta de gás", False), ("conta de gas", False),
        ("energia elétrica", False), ("energia eletrica", False),
        ("água da casa", False), ("água encanada", False),
        ("internet da casa", False), ("wi-fi", True), ("wifi", True),
        ("iptu", True),
        ("financiamento da casa", False), ("prestação da casa", False),
        ("prestação do apê", False), ("prestação do apto", False),
        ("reforma da casa", False),
    ],
    "transporte_pessoal": [
        ("financiamento do carro", False), ("prestação do carro", False),
        ("seguro do carro", False), ("seguro do veículo", False),
        ("ipva", True), ("licenciamento", True),
        ("ônibus", True), ("onibus", True),
        ("metrô", True), ("metro", True), ("trem", True),
        ("passagem de ônibus", False), ("cartão de transporte", False),
        ("bilhete único", False),
        ("manutenção do carro pessoal", False), ("conserto do carro pessoal", False),
    ],
    "saude": [
        ("médico", True), ("medico", True),
        ("hospital", True), ("pronto-socorro", True), ("pronto socorro", False),
        ("clínica", True), ("clinica", True), ("upa", True),
        ("farmácia", True), ("farmacia", True), ("drogaria", True),
        ("remédio", True), ("remedio", True), ("medicamento", True),
        ("plano de saúde", False), ("plano de saude", False),
        ("plano", True),
        ("exame", True), ("exames", True),
        ("consulta", True), ("consultas", True),
        ("dentista", True), ("ortodontista", True),
        ("fisioterapeuta", True), ("fisioterapia", True),
        ("psicólogo", True), ("psicologo", True), ("psiquiatra", True),
        ("academia de saúde", False), ("nutricionista", True),
        ("vacina", True), ("vacinação", True),
        ("cirurgia", True), ("internação", True),
    ],
    "educacao": [
        ("escola", True), ("colégio", True), ("colegio", True),
        ("faculdade", True), ("universidade", True), ("facul", True),
        ("curso", True), ("cursos", True),
        ("mensalidade", True), ("anuidade", True),
        ("material escolar", False), ("material do curso", False),
        ("livro", True), ("apostila", True),
        ("aula", True), ("aulas", True),
        ("treinamento", True),
    ],
    "lazer": [
        ("lazer", True), ("diversão", True), ("diversao", True),
        ("cinema", True), ("teatro", True), ("show", True),
        ("viagem", True), ("passeio", True), ("excursão", True),
        ("hotel", True), ("pousada", True), ("hospedagem", True),
        ("parque", True), ("clube", True),
        ("academia", True), ("personal", True),
        ("streaming", True), ("netflix", True), ("spotify", True),
        ("amazon prime", False), ("disney", True),
        ("assinatura", True), ("jogo", True), ("games", True),
        ("bar", True), ("balada", True), ("festa", True),
        ("churrasco", True),
    ],
    "vestuario": [
        ("roupa", True), ("roupas", True),
        ("calçado", True), ("calçados", True),
        ("sapato", True), ("tênis", True), ("tenis", True),
        ("sandália", True), ("sandalia", True),
        ("vestuário", True), ("vestuario", True),
        ("camisa", True), ("camiseta", True), ("blusa", True),
        ("calça", True), ("calca", True), ("bermuda", True),
        ("vestido", True), ("saia", True),
        ("cueca", True), ("meia", True), ("meias", True),
        ("roupa íntima", False),
        ("loja de roupa", False), ("shopping", True),
    ],
    "internet_telefone": [
        ("internet", True), ("plano de internet", False),
        ("telefone", True), ("celular", True),
        ("plano do celular", False), ("plano celular", False),
        ("recarga", True), ("recarga de celular", False),
        ("tim", True), ("vivo", True), ("claro", True), ("oi", True),
        ("net", True), ("claro net", False),
    ],
}

CONTEXTO_SERVICO = [
    "obra", "do serviço", "para o serviço", "para a obra",
    "do trabalho", "para o trabalho", "da obra", "do cliente",
    "para o cliente", "no serviço", "no trabalho",
]

CONTEXTO_PESSOAL = [
    "minha casa", "meu carro", "para mim", "pessoal",
    "vida pessoal", "pra mim", "pra minha família", "minha família",
]


# ================================================================
# HELPERS DE MATCH
# ================================================================

def _match_tag(frase_lower, entries):
    for palavra, wb in entries:
        if wb:
            if re.search(r'\b' + re.escape(palavra) + r'\b', frase_lower):
                return True
        else:
            if palavra in frase_lower:
                return True
    return False


def _contem_alguma(frase_lower, palavras):
    return any(p in frase_lower for p in palavras)


def extract_tags(frase_lower, mapa_tags_raw):
    return [tag for tag, entries in mapa_tags_raw.items()
            if _match_tag(frase_lower, entries)]


# ================================================================
# SPLIT INTELIGENTE — sem depender de pontuação
#
# Estratégia:
#   1. Marca separadores explícitos (vírgula+mas, ponto, traço)
#   2. Detecta transição de verbo financeiro mesmo sem pontuação:
#      "recebi 500 comprei tinta" → dois eventos
#   3. Aplica merge de blocos órfãos (sem verbo próprio)
# ================================================================

# Verbos que iniciam um novo evento financeiro
_VERBOS_EVENTO = (
    # 1ª pessoa singular (eu)
    "paguei", "comprei", "gastei", "recebi", "transferi",
    "depositei", "aluguei", "coloquei", "botei", "abasteci",
    "faturei", "cobrei", "desembolsei", "contratei", "pedi",
    "fui", "mandei", "enviei", "passei",
    # 1ª pessoa plural (nós)
    "pagamos", "compramos", "gastamos", "recebemos", "transferimos",
    "depositamos", "alugamos", "colocamos", "botamos", "abastecemos",
    "faturamos", "cobramos", "contratamos", "fomos",
    # 3ª pessoa singular (ele/ela/você/cliente)
    "pagou", "comprou", "gastou", "recebeu", "transferiu",
    "depositou", "alugou", "colocou", "botou", "abasteceu",
    "cobrou", "contratou", "pediu", "mandou", "enviou", "passou",
    # 3ª pessoa plural (eles/clientes)
    "pagaram", "compraram", "gastaram", "receberam", "transferiram",
    "depositaram", "alugaram", "pediram", "mandaram", "enviaram",
    "passaram", "colocaram",
    # Verbos especiais (impessoais ou de estado)
    "caiu",    # "caiu 1800 no pix"
    "entrou",  # "entrou 500 na conta"
    "saiu",    # "saiu 300 da conta"
)

_RE_VERBOS = r'\b(' + '|'.join(_VERBOS_EVENTO) + r')\b'

_VERBOS_FIN = re.compile(_RE_VERBOS, re.IGNORECASE)


def split_intencoes(texto: str) -> list:
    """
    Divide o texto em blocos de eventos independentes.
    Funciona COM e SEM pontuação.

    Estratégia de corte (em ordem):
      1. Separadores explícitos: ponto, vírgula+mas, traço
      2. vírgula + verbo financeiro
      3. Conectivos (aí, então, e, também) + verbo + número
      4. Transição numérica: número [unidade] → verbo
      5. Merge de blocos sem verbo com o seguinte que tem
    """
    t = texto.strip()
    VERBOS_RE = '|'.join(_VERBOS_EVENTO)

    # 1. Separadores explícitos
    t = re.sub(r',\s*(mas|porém|porem)\s+', ' |||SEP||| ', t, flags=re.IGNORECASE)
    t = re.sub(r',?\s*e\s+ainda\s+', ' |||SEP||| ', t, flags=re.IGNORECASE)
    t = re.sub(r'\s*[.!?]\s+', ' |||SEP||| ', t)
    t = re.sub(r'\s*[—–]{1,}\s*', ' |||SEP||| ', t)

    # 2. vírgula + verbo financeiro
    t = re.sub(
        r',\s*(' + VERBOS_RE + r')\s+',
        r' |||SEP||| \1 ', t, flags=re.IGNORECASE
    )

    # 3. Conectivos + verbo + conteúdo (até o primeiro número ou fim)
    # Captura: "aí botei gasolina 130", "e comprei tinta 200", "então paguei 300"
    # Para no primeiro número para não engolir múltiplos eventos
    t = re.sub(
        r'\s+(?:aí|ai|então|entao|também|tambem)\s+(' + VERBOS_RE + r')\s+([^,]+?\d+)',
        lambda m: ' |||SEP||| ' + m.group(1) + ' ' + m.group(2),
        t, flags=re.IGNORECASE
    )
    # "e" + verbo só separa se houver número logo após (evita false positives)
    t = re.sub(
        r'\s+e\s+(' + VERBOS_RE + r')\s+(\w[^,]{0,30}?\d+)',
        lambda m: ' |||SEP||| ' + m.group(1) + ' ' + m.group(2),
        t, flags=re.IGNORECASE
    )

    # 4. Transição numérica: [uns/umas] número [unidade/palavras] → verbo
    # Cobre: "gastei uns 200", "caiu uns 300 no pix comprei", "recebi 1500 do João comprei"
    UNIDADES = r'(?:\s*(?:reais|conto|contos|pila|pilas|real|r\$))?'
    # Normaliza "uns/umas X" → "X" para facilitar a detecção
    t = re.sub(r'\b(?:uns|umas|cerca de|mais de|menos de)\s+(\d)', r'\1', t, flags=re.IGNORECASE)
    # Roda em loop porque cada substituição pode ativar a próxima
    _num_pat = re.compile(
        r'(\d[\d.,]*)' + UNIDADES + r'(?:\s+\w+){0,4}?\s+(' + VERBOS_RE + r')\s+',
        re.IGNORECASE
    )
    for _ in range(10):  # máx 10 eventos por mensagem
        new_t = _num_pat.sub(lambda m: m.group(1) + ' |||SEP||| ' + m.group(2) + ' ', t)
        if new_t == t:
            break
        t = new_t

    # 5. Quebra pelos marcadores
    partes = re.split(r'\s*\|\|\|SEP\|\|\|\s*', t)

    blocos = []
    for parte in partes:
        sub = parte.strip().rstrip('.,!?')
        if not sub:
            continue
        # Bloco órfão: só "verbo + número [unidade]" → mescla com anterior
        if blocos and re.fullmatch(
            r'(' + VERBOS_RE + r')\s+[\d.,]+(\s*(?:reais|conto|real|pila))?',
            sub, re.IGNORECASE
        ):
            blocos[-1] = blocos[-1].rstrip() + ' ' + sub
        else:
            blocos.append(sub)

    # 6. Merge: bloco sem verbo financeiro + próximo que tem
    merged = []
    i = 0
    while i < len(blocos):
        atual = blocos[i]
        if (
            not _VERBOS_FIN.search(atual)
            and i + 1 < len(blocos)
            and _VERBOS_FIN.search(blocos[i + 1])
        ):
            merged.append(atual.rstrip() + ' ' + blocos[i + 1].lstrip())
            i += 2
        else:
            merged.append(atual)
            i += 1

    return [b for b in merged if b.strip()]


def extract_valor(frase: str) -> str:
    """Extrai o primeiro valor monetário encontrado."""
    for pattern in [
        r'\b(\d{1,3}(?:\.\d{3})+(?:,\d+)?)\b',   # 2.500 ou 2.500,50
        r'\b(\d{1,3}(?:,\d{3})+(?:\.\d+)?)\b',   # 2,500
        r'\b(\d{4,})\b',                          # 2500
        r'\b(\d{2,})\b',                          # 75
    ]:
        m = re.search(pattern, frase)
        if m:
            return m.group(1)
    return ""


def extract_todos_valores(frase: str) -> list:
    """Extrai todos os valores monetários (para blocos com múltiplos valores)."""
    return re.findall(r'\b\d[\d.,]*\b', frase)


def extract_descricao(frase: str) -> str:
    d = re.sub(r'\b\d[\d.,]*\b', '', frase)
    d = re.sub(r'\b(reais|real|conto|contos|pila|r\$|\$)\b', '', d, flags=re.IGNORECASE)
    return re.sub(r'\s+', ' ', d).strip()


def extract_cliente(frase: str) -> str:
    """Extrai o nome de quem pagou/enviou dinheiro."""
    padroes = [
        # "recebi X da/do Nome" ou "da empresa Nome"
        r'(?:recebi|recebemos|recebeu).*?(?:da|do)\s+(?:empresa\s+)?'
        r'([A-ZÁÉÍÓÚÂÊÔÃÕÇ][A-Za-záéíóúâêôãõç]{2,})',
        # "Nome me pagou", "Nome transferiu", "Nome enviou"
        r'\b([A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-záéíóúâêôãõç]{2,})\s+'
        r'(?:me\s+)?(?:pagou|transferiu|depositou|mandou|enviou|passou|acertou)',
        # "da/do Nome" como último recurso
        r'(?:da|do)\s+(?:empresa\s+)?([A-ZÁÉÍÓÚÂÊÔÃÕÇ][A-Za-záéíóúâêôãõç]{2,})',
    ]
    for padrao in padroes:
        m = re.search(padrao, frase, re.IGNORECASE)
        if m:
            return m.group(1)
    return ""


def inferir_contexto(frase_lower: str) -> str | None:
    if _contem_alguma(frase_lower, CONTEXTO_SERVICO):
        return "servico"
    if _contem_alguma(frase_lower, CONTEXTO_PESSOAL):
        return "pessoal"
    return None


# ================================================================
# SUBCLASSIFICADORES REGEX
# ================================================================

def classificar_receita(bloco: str, bloco_lower: str, valor: str, dias: list) -> dict:
    return {
        "tipo": "receita",
        "dados": {
            "cliente": extract_cliente(bloco),
            "valor": valor,
            "dias": dias,
        }
    }


def classificar_despesa(bloco: str, bloco_lower: str, valor: str, dias: list) -> dict:
    descricao = extract_descricao(bloco)
    tags_s = extract_tags(bloco_lower, TAGS_SERVICO_RAW)
    tags_p = extract_tags(bloco_lower, TAGS_PESSOAL_RAW)

    if tags_s:
        return {"tipo": "despesa_servico",
                "dados": {"descricao": descricao, "valor": valor, "tags": tags_s, "dias": dias}}
    if tags_p:
        return {"tipo": "despesa_pessoal",
                "dados": {"descricao": descricao, "valor": valor, "tags": tags_p, "dias": dias}}

    ctx = inferir_contexto(bloco_lower)
    if ctx == "servico":
        return {"tipo": "despesa_servico",
                "dados": {"descricao": descricao, "valor": valor, "tags": [], "dias": dias,
                          "aviso": "Tag não identificada — revise manualmente"}}
    if ctx == "pessoal":
        return {"tipo": "despesa_pessoal",
                "dados": {"descricao": descricao, "valor": valor, "tags": [], "dias": dias,
                          "aviso": "Tag não identificada — revise manualmente"}}

    return {"tipo": "despesa",
            "dados": {"descricao": descricao, "valor": valor, "tags": [], "dias": dias,
                      "aviso": "Tipo e tag não identificados — revise manualmente"}}


def _evento_inconclusivo(evento: dict) -> bool:
    """Retorna True se o evento precisa do fallback Gemini."""
    tipo = evento.get("tipo", "")
    if tipo in ("nao_classificado", "despesa"):
        return True
    # despesa_servico/pessoal sem tags e sem valor também é inconclusivo
    if tipo in ("despesa_servico", "despesa_pessoal"):
        dados = evento.get("dados", {})
        if not dados.get("tags") and not dados.get("valor"):
            return True
    return False


# ================================================================
# CAMADA 2 — FALLBACK GEMINI
# ================================================================

def _chamar_gemini(texto_original: str, blocos_inconclusivos: list) -> list:
    """
    Envia os blocos inconclusivos para o Gemini e retorna eventos normalizados.
    Retorna lista vazia em caso de erro (silencia falha graciosamente).
    """
    try:
        import google.generativeai as genai
        from core.config import GEMINI_API_KEY

        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-2.5-flash-lite")

        prompt = f"""Você é um assistente de classificação financeira para um microempresário brasileiro.
Analise o texto abaixo e extraia TODOS os eventos financeiros, mesmo em linguagem informal, gíria ou sem pontuação.

TEXTO ORIGINAL COMPLETO:
"{texto_original}"

TRECHOS NÃO CLASSIFICADOS (que precisam de análise):
{chr(10).join(f'- "{b}"' for b in blocos_inconclusivos)}

Retorne APENAS um JSON válido, sem markdown, sem explicações, no formato:
{{
  "eventos": [
    {{
      "tipo": "receita" | "despesa_servico" | "despesa_pessoal" | "despesa" | "nao_classificado",
      "dados": {{
        "valor": "número como string ou vazio",
        "cliente": "nome se for receita ou vazio",
        "descricao": "descrição curta do evento",
        "tags": ["tag1", "tag2"],
        "dias": ["segunda", "terça", etc. ou lista vazia],
        "aviso": "se não tiver certeza, explique aqui; senão deixe vazio"
      }}
    }}
  ]
}}

REGRAS:
- tipo "despesa_servico": gastos do negócio (funcionário, material, ferramenta, transporte da obra, imposto)
  tags possíveis: funcionario, material, ferramenta, transporte, imposto
- tipo "despesa_pessoal": gastos da vida pessoal
  tags possíveis: alimentacao, moradia, saude, educacao, lazer, vestuario, internet_telefone, transporte_pessoal
- tipo "receita": qualquer entrada de dinheiro
- Expressões informais como "caiu grana", "me pagaram", "desembolsei", "botei", "abasteci" são válidas
- Se o mesmo trecho tiver múltiplos eventos, retorne múltiplos objetos no array
- Se genuinamente não for financeiro, use "nao_classificado"
"""

        response = model.generate_content(prompt)
        raw = response.text.strip()

        # Remove markdown se vier com ```json
        raw = re.sub(r'^```(?:json)?\s*', '', raw, flags=re.MULTILINE)
        raw = re.sub(r'\s*```$', '', raw, flags=re.MULTILINE)

        parsed = json.loads(raw)
        eventos = parsed.get("eventos", [])

        # Normaliza e valida cada evento
        resultado = []
        for ev in eventos:
            tipo = ev.get("tipo", "nao_classificado")
            dados = ev.get("dados", {})
            resultado.append({
                "tipo": tipo,
                "dados": {
                    "valor":     str(dados.get("valor", "") or ""),
                    "cliente":   str(dados.get("cliente", "") or ""),
                    "descricao": str(dados.get("descricao", "") or ""),
                    "tags":      list(dados.get("tags", []) or []),
                    "dias":      list(dados.get("dias", []) or []),
                    "aviso":     str(dados.get("aviso", "") or ""),
                    "fonte":     "gemini",  # marca para rastreabilidade
                }
            })
        return resultado

    except Exception as e:
        logger.warning(f"Fallback Gemini falhou: {e}")
        return []


# ================================================================
# CLASSIFICADOR PRINCIPAL
# ================================================================

def classify_text(texto: str) -> list:
    """
    Classifica texto em eventos financeiros do dono da empresa.

    Fluxo:
      1. Split inteligente (com e sem pontuação)
      2. Regex classifier para cada bloco
      3. Blocos inconclusivos → fallback Gemini
      4. Pós-processamento: merge de blocos com tag mas sem valor

    Tipos de evento:
        receita          — qualquer entrada de dinheiro
        despesa_servico  — gasto do negócio
                           tags: funcionario | material | ferramenta | transporte | imposto
        despesa_pessoal  — gasto pessoal
                           tags: alimentacao | moradia | transporte_pessoal | saude |
                                 educacao | lazer | vestuario | internet_telefone
        despesa          — genérica, não classificada (requer revisão)
        nao_classificado — frase não reconhecida como financeira
    """
    eventos = []
    blocos_inconclusivos = []

    for bloco in split_intencoes(texto):
        bloco = bloco.strip()
        if not bloco:
            continue

        bloco_lower = bloco.lower()
        valor = extract_valor(bloco)
        dias = re.findall(
            r'\b(segunda|terça|quarta|quinta|sexta|sábado|domingo)\b',
            bloco_lower
        )

        if _contem_alguma(bloco_lower, PALAVRAS_RECEITA):
            ev = classificar_receita(bloco, bloco_lower, valor, dias)
        elif _contem_alguma(bloco_lower, PALAVRAS_DESPESA):
            ev = classificar_despesa(bloco, bloco_lower, valor, dias)
        else:
            ev = {"tipo": "nao_classificado", "dados": {"descricao": bloco}}

        # Marca inconclusivos para o Gemini
        if _evento_inconclusivo(ev):
            blocos_inconclusivos.append(bloco)

        eventos.append(ev)

    # ── Fallback Gemini para inconclusivos ───────────────────────
    if blocos_inconclusivos:
        logger.info(f"Gemini fallback acionado para {len(blocos_inconclusivos)} bloco(s).")
        eventos_gemini = _chamar_gemini(texto, blocos_inconclusivos)

        if eventos_gemini:
            # Substitui os eventos inconclusivos pelos do Gemini
            eventos_finais = []
            gemini_idx = 0
            for ev in eventos:
                if _evento_inconclusivo(ev) and gemini_idx < len(eventos_gemini):
                    eventos_finais.append(eventos_gemini[gemini_idx])
                    gemini_idx += 1
                else:
                    eventos_finais.append(ev)
            # Se o Gemini retornou mais eventos do que inconclusivos (subdividiu), adiciona o resto
            while gemini_idx < len(eventos_gemini):
                eventos_finais.append(eventos_gemini[gemini_idx])
                gemini_idx += 1
            eventos = eventos_finais

    # ── Pós-processamento: mescla tag-sem-valor com valor-sem-tag ─
    eventos_merged = []
    i = 0
    while i < len(eventos):
        ev = eventos[i]
        dados = ev.get("dados", {})

        if (
            i + 1 < len(eventos)
            and not dados.get("valor")
            and dados.get("tags")
            and ev["tipo"] in ("despesa_pessoal", "despesa_servico")
        ):
            prox = eventos[i + 1]
            pd = prox.get("dados", {})
            if (
                pd.get("valor")
                and not pd.get("tags")
                and prox["tipo"] in ("despesa", "despesa_pessoal", "despesa_servico")
            ):
                ev_merged = {
                    "tipo": ev["tipo"],
                    "dados": {
                        **dados,
                        "valor": pd["valor"],
                        "descricao": (dados.get("descricao", "") + " " + pd.get("descricao", "")).strip(),
                    }
                }
                ev_merged["dados"].pop("aviso", None)
                eventos_merged.append(ev_merged)
                i += 2
                continue

        eventos_merged.append(ev)
        i += 1

    return eventos_merged
