import re

# ============================================================
# PALAVRAS-CHAVE
# ============================================================

PALAVRAS_RECEITA = [
    "recebi", "me pagou", "transferiu", "depositou",
    "entrou", "pagamento recebido", "faturei", "cobrei",
    "me mandou", "caiu na conta"
]

PALAVRAS_DESPESA = [
    "paguei", "comprei", "gastei", "gasto", "compra",
    "despesa", "custou", "coloquei", "tirei da conta",
    "aluguei", "transferi", "debitou", "pedi", "fiz um pedido",
    "fui no mercado", "fui no supermercado", "fui na farmácia",
    "fui na farmacia", "fui no restaurante", "fui na padaria",
    "fui no açougue", "fui na feira"
]

# ============================================================
# TAGS — DESPESA DE SERVIÇO
# Cada entrada é (palavra, usa_word_boundary)
# word_boundary=True evita falsos positivos como "gas" em "gastei"
# ============================================================

TAGS_SERVICO_RAW = {
    "funcionario": [
        ("funcionário", False), ("funcionario", False),
        ("funcionária", False), ("funcionaria", False),
        ("ajudante", True), ("peão", True), ("piao", True),
        ("colaborador", True), ("diarista", True),
        ("diária", True), ("diaria", True),
        ("mão de obra", False), ("mao de obra", False),
        ("empreiteiro", True), ("subcontratado", True),
        ("terceirizado", True), ("prestador", True),
        ("mestre de obra", False), ("servente", True),
    ],
    "material": [
        ("tinta", True), ("gesso", True), ("cimento", True),
        ("areia", True), ("argamassa", True), ("rejunte", True),
        ("parafuso", True), ("prego", True), ("madeira", True),
        ("massa corrida", False), ("massa", True), ("fio", True),
        ("cabo", True), ("tubo", True), ("cano", True),
        ("lixa", True), ("rolo", True), ("pincel", True),
        ("primer", True), ("selador", True), ("impermeabilizante", True),
        ("cola", True), ("vedante", True), ("placa", True),
        ("tijolo", True), ("materiais", True),
        # "material" só bate quando é o objeto direto (comprei/gastei material)
        # não bate em "entrega do material", "para o material"
        ("comprei material", False), ("gastei com material", False),
        ("compra de material", False), ("material de obra", False),
        ("material para", False),
        ("insumo", True),
    ],
    "ferramenta": [
        ("ferramenta", True), ("ferramentas", True),
        ("equipamento", True), ("equipamentos", True),
        ("furadeira", True), ("martelete", True),
        ("esmerilhadeira", True), ("betoneira", True),
        ("andaime", True), ("escada", True),
        ("mangueira", True), ("compressor", True),
        ("aluguel de equipamento", False), ("locação de equipamento", False),
    ],
    "transporte": [
        ("gasolina", True), ("combustível", True), ("combustivel", True),
        ("diesel", True), ("etanol", True),
        ("frete", True), ("pedágio", True), ("pedagio", True),
        ("estacionamento", True), ("aluguel da van", False),
        ("aluguel do carro", False), ("manutenção do carro", False),
        ("manutenção da van", False), ("conserto do carro", False),
        ("revisão do carro", False), ("deslocamento", True),
        ("uber", True), ("passagem", True),
    ],
    "imposto": [
        ("imposto", True), ("nota fiscal", False),
        ("simples nacional", False), (" das ", True),
        (" iss ", True), ("inss", True), ("fgts", True),
        ("contador", True), ("contabilidade", True), ("taxa", True),
    ],
}

TAGS_PESSOAL_RAW = {
    "alimentacao": [
        ("mercado", True), ("supermercado", True), ("feira", True),
        ("açougue", True), ("padaria", True), ("restaurante", True),
        ("lanche", True), ("refeição", True), ("refeicao", True),
        ("almoço", True), ("almoco", True), ("janta", True),
        ("jantar", True), ("café", True), ("cafe", True),
        ("ifood", True), ("delivery", True), ("pizza", True),
        ("hamburguer", True), ("comida", True),
    ],
    "moradia": [
        ("aluguel da casa", False), ("aluguel do apartamento", False),
        ("condomínio", True), ("condominio", True),
        ("conta de luz", False), ("conta de água", False),
        ("conta de agua", False),
        ("conta de gás", False), ("conta de gas", False),
        ("energia elétrica", False), ("água da casa", False),
        ("iptu", True), ("financiamento da casa", False),
        ("prestação da casa", False),
    ],
    "transporte_pessoal": [
        ("financiamento do carro", False), ("seguro do carro", False),
        ("ipva", True), ("licenciamento", True),
        ("ônibus", True), ("onibus", True),
        ("metrô", True), ("metro", True), ("trem", True),
    ],
    "saude": [
        ("médico", True), ("medico", True), ("hospital", True),
        ("clínica", True), ("clinica", True),
        ("farmácia", True), ("farmacia", True),
        ("remédio", True), ("remedio", True), ("medicamento", True),
        ("plano de saúde", False), ("plano de saude", False),
        ("exame", True), ("consulta", True),
        ("dentista", True), ("fisioterapeuta", True),
        ("psicólogo", True), ("psicologo", True),
    ],
    "educacao": [
        ("escola", True), ("faculdade", True), ("curso", True),
        ("mensalidade", True), ("material escolar", False),
        ("livro", True), ("universidade", True),
    ],
    "lazer": [
        ("lazer", True), ("cinema", True), ("teatro", True),
        ("show", True), ("viagem", True), ("hotel", True),
        ("hospedagem", True), ("passeio", True), ("parque", True),
        ("academia", True), ("streaming", True),
        ("netflix", True), ("spotify", True), ("assinatura", True),
    ],
    "vestuario": [
        ("roupa", True), ("roupas", True), ("calçado", True),
        ("calçados", True), ("sapato", True), ("tenis", True),
        ("vestuário", True), ("vestuario", True),
        ("camisa", True), ("calça", True),
    ],
    "internet_telefone": [
        ("internet", True), ("telefone", True), ("celular", True),
        ("plano do celular", False), ("recarga", True),
    ],
}

CONTEXTO_SERVICO = [
    "obra", "do serviço", "para o serviço", "para a obra",
    "do trabalho", "para o trabalho", "da obra"
]

CONTEXTO_PESSOAL = [
    "minha casa", "meu carro", "para mim", "pessoal", "vida pessoal"
]


# ============================================================
# HELPERS DE MATCH (com suporte a word boundary opcional)
# ============================================================

def _match_tag(frase_lower, entries):
    """
    Verifica se alguma das entradas da tag está na frase.
    entries: lista de (palavra, usa_word_boundary)
    """
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
    tags = []
    for tag, entries in mapa_tags_raw.items():
        if _match_tag(frase_lower, entries):
            tags.append(tag)
    return tags


# ============================================================
# SPLIT INTELIGENTE
# ============================================================

def split_intencoes(texto: str):
    """
    Divide o texto em blocos de eventos independentes.
    Pontos de corte:
      - vírgula + 'mas'
      - vírgula ou 'e' + verbo de ação + número  (novo evento claro)
      - ponto final
      - traço (—)
    NÃO quebra quando o verbo+número é complemento da frase anterior
    (ex: 'comprei remédio na farmácia, gastei 75' → 1 bloco só).
    """
    t = texto

    # vírgula + mas
    t = re.sub(r',\s+mas\s+', ' |||SEP||| ', t, flags=re.IGNORECASE)
    # e ainda
    t = re.sub(r',?\s+e\s+ainda\s+', ' |||SEP||| ', t, flags=re.IGNORECASE)

    VERBOS = r'(paguei|comprei|gastei|gastou|coloquei|aluguei|recebi|faturei|cobrei|transferi|debitou|pedi|fiz|fui)'

    # vírgula + verbo  →  novo evento (separação de eventos em lista)
    # Ex: "paguei ajudante 250, comprei tinta por 180" → 2 eventos
    t = re.sub(
        r',\s+' + VERBOS + r'\s+',
        r' |||SEP||| \1 ',
        t,
        flags=re.IGNORECASE
    )

    # ' e ' + verbo + (palavra(s)) + número  →  novo evento
    # ex: "e coloquei gasolina por 90"  ou  "e comprei tinta por 180"
    t = re.sub(
        r'\s+e\s+' + VERBOS + r'\s+([^,]+?\d)',
        lambda m: ' |||SEP||| ' + m.group(1) + ' ' + m.group(2),
        t,
        flags=re.IGNORECASE
    )

    partes = re.split(r'\|\|\|SEP\|\|\|', t)

    # Verbos financeiros — usados para detectar blocos sem ação própria
    _VERBOS_FIN = re.compile(
        r'\b(paguei|comprei|gastei|gastou|coloquei|aluguei|recebi|faturei|'
        r'cobrei|transferi|debitou|pedi|fiz|fui|custou|saiu|entrou|caiu)\b',
        re.IGNORECASE
    )

    blocos = []
    for parte in partes:
        for sub in re.split(r'\.\s+|—\s*', parte.strip()):
            sub = sub.strip().rstrip('.')
            if not sub:
                continue
            # Bloco órfão 1: só "verbo + número" sem contexto → mescla com anterior
            if blocos and re.fullmatch(
                r'(paguei|comprei|gastei|gastou|coloquei|aluguei|transferi|pedi)\s+[\d.,]+',
                sub, re.IGNORECASE
            ):
                blocos[-1] = blocos[-1].rstrip() + ', ' + sub
            # Bloco órfão 2: não tem verbo financeiro → mescla com o próximo
            # (ex: "Fui no mercado" quando separado de "gastei 700")
            # — na prática, adiciona normalmente e depois fazemos merge abaixo
            else:
                blocos.append(sub)

    # Merge: bloco sem verbo financeiro absorve o próximo (que tem o verbo/valor)
    # Ex: ["Fui no mercado", "gastei 700"] → ["Fui no mercado gastei 700"]
    merged = []
    i = 0
    while i < len(blocos):
        bloco_atual = blocos[i]
        # Se este bloco não tem verbo financeiro, tenta absorver o(s) próximo(s)
        if not _VERBOS_FIN.search(bloco_atual):
            # Absorve enquanto o próximo também não tiver verbo OU for o complemento direto
            while i + 1 < len(blocos):
                proximo = blocos[i + 1]
                # Só absorve se o próximo tiver verbo financeiro (é o complemento)
                if _VERBOS_FIN.search(proximo):
                    bloco_atual = bloco_atual.rstrip() + ' ' + proximo.lstrip()
                    i += 1
                    break  # absorveu um, para (o resto são eventos independentes)
                else:
                    break
        merged.append(bloco_atual)
        i += 1

    return merged


# ============================================================
# HELPERS DE EXTRAÇÃO
# ============================================================

def extract_valor(frase):
    for pattern in [
        r'\b(\d{1,3}(?:\.\d{3})+(?:,\d+)?)\b',
        r'\b(\d{1,3}(?:,\d{3})+(?:\.\d+)?)\b',
        r'\b(\d{4,})\b',
        r'\b(\d{2,})\b',
    ]:
        m = re.search(pattern, frase)
        if m:
            return m.group(1)
    return ""


def extract_descricao(frase):
    d = re.sub(r'\b\d[\d.,]*\b', '', frase)
    d = re.sub(r'\b(reais|real|r\$|\$)\b', '', d, flags=re.IGNORECASE)
    return re.sub(r'\s+', ' ', d).strip()


def extract_cliente(frase):
    m = re.search(
        r'(?:recebi|recebido).*?(?:da|do)\s+(?:empresa\s+)?([A-ZÁÉÍÓÚÂÊÔÃÕÇ][A-Za-záéíóúâêôãõç]+)',
        frase, re.IGNORECASE
    )
    if m:
        return m.group(1)
    m = re.search(
        r'\b([A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-záéíóúâêôãõç]+)\s+(?:me\s+)?(?:pagou|transferiu|depositou|mandou)',
        frase
    )
    if m:
        return m.group(1)
    m = re.search(
        r'(?:da|do)\s+(?:empresa\s+)?([A-ZÁÉÍÓÚÂÊÔÃÕÇ][A-Za-záéíóúâêôãõç]+)',
        frase
    )
    if m:
        return m.group(1)
    return ""


def inferir_contexto(frase_lower):
    if _contem_alguma(frase_lower, CONTEXTO_SERVICO):
        return "servico"
    if _contem_alguma(frase_lower, CONTEXTO_PESSOAL):
        return "pessoal"
    return None


# ============================================================
# SUBCLASSIFICADORES
# ============================================================

def classificar_receita(bloco, bloco_lower, valor, dias):
    return {
        "tipo": "receita",
        "dados": {
            "cliente": extract_cliente(bloco),
            "valor": valor,
            "dias": dias
        }
    }


def classificar_despesa(bloco, bloco_lower, valor, dias):
    descricao = extract_descricao(bloco)
    tags_s = extract_tags(bloco_lower, TAGS_SERVICO_RAW)
    tags_p = extract_tags(bloco_lower, TAGS_PESSOAL_RAW)

    if tags_s:
        return {
            "tipo": "despesa_servico",
            "dados": {"descricao": descricao, "valor": valor, "tags": tags_s, "dias": dias}
        }

    if tags_p:
        return {
            "tipo": "despesa_pessoal",
            "dados": {"descricao": descricao, "valor": valor, "tags": tags_p, "dias": dias}
        }

    contexto = inferir_contexto(bloco_lower)
    if contexto == "servico":
        return {
            "tipo": "despesa_servico",
            "dados": {"descricao": descricao, "valor": valor, "tags": [], "dias": dias,
                      "aviso": "Tag não identificada — revise manualmente"}
        }
    if contexto == "pessoal":
        return {
            "tipo": "despesa_pessoal",
            "dados": {"descricao": descricao, "valor": valor, "tags": [], "dias": dias,
                      "aviso": "Tag não identificada — revise manualmente"}
        }

    return {
        "tipo": "despesa",
        "dados": {"descricao": descricao, "valor": valor, "tags": [], "dias": dias,
                  "aviso": "Tipo e tag não identificados — revise manualmente"}
    }


# ============================================================
# CLASSIFICADOR PRINCIPAL
# ============================================================

def classify_text(texto: str):
    """
    Classifica texto em eventos financeiros do dono da empresa.

    Tipos:
        receita          — qualquer entrada de dinheiro
        despesa_servico  — gasto do negócio
                           tags: funcionario | material | ferramenta | transporte | imposto
        despesa_pessoal  — gasto pessoal
                           tags: alimentacao | moradia | transporte_pessoal | saude |
                                 educacao | lazer | vestuario | internet_telefone
        despesa          — não classificado (requer revisão)
        nao_classificado — frase não reconhecida como financeira
    """
    eventos = []
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
            eventos.append(classificar_receita(bloco, bloco_lower, valor, dias))
        elif _contem_alguma(bloco_lower, PALAVRAS_DESPESA):
            eventos.append(classificar_despesa(bloco, bloco_lower, valor, dias))
        else:
            eventos.append({"tipo": "nao_classificado", "dados": {"descricao": bloco}})

    # ── Pós-processamento: mescla evento sem valor com o seguinte sem tags ──
    # Caso: "Fui no mercado" (tag ok, sem valor) + "gastei 700" (valor, sem tags)
    # → une em um evento só com tag + valor
    eventos_merged = []
    i = 0
    while i < len(eventos):
        ev = eventos[i]
        dados = ev.get("dados", {})
        proximo_existe = i + 1 < len(eventos)

        if (
            proximo_existe
            and not dados.get("valor")         # este não tem valor
            and dados.get("tags")              # mas tem tags (já classificado)
            and ev["tipo"] in ("despesa_pessoal", "despesa_servico")
        ):
            prox = eventos[i + 1]
            pd = prox.get("dados", {})
            if (
                pd.get("valor")                # o próximo tem valor
                and not pd.get("tags")         # mas não tem tags
                and prox["tipo"] in ("despesa", "despesa_pessoal", "despesa_servico")
            ):
                # Mescla: mantém tipo e tags do atual, valor do próximo
                ev_merged = {
                    "tipo": ev["tipo"],
                    "dados": {
                        **dados,
                        "valor": pd["valor"],
                        "descricao": (dados.get("descricao", "") + " " + pd.get("descricao", "")).strip(),
                    }
                }
                # Remove aviso se existia no próximo mas não no atual
                if "aviso" in ev_merged["dados"] and not dados.get("aviso"):
                    ev_merged["dados"].pop("aviso", None)
                eventos_merged.append(ev_merged)
                i += 2
                continue

        eventos_merged.append(ev)
        i += 1

    return eventos_merged
