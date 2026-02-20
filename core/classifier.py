import re

DIAS = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]

# =============================
# SPLIT INTELIGENTE
# =============================

def split_intencoes(texto: str):
    """
    Divide o texto em blocos lógicos, respeitando contexto.
    Divide por: vírgula + "mas", vírgula + "e" + dia, ponto final, traço (—).
    """
    # Padrões de divisão (em ordem de prioridade)
    # 1. Vírgula + "mas" (mudança de contexto)
    # 2. Vírgula + "e" + dia da semana (novo evento temporal)
    # 3. Vírgula + "e" + "ainda" (novo evento)
    # 4. Ponto final
    # 5. Traço (—)
    
    # Primeiro, marca os pontos de divisão preservando o contexto
    # Substitui padrões de divisão por marcadores temporários
    texto_marcado = texto
    
    # Marca vírgula + "mas"
    texto_marcado = re.sub(
        r',\s+mas\s+',
        ' |||MAS||| ',
        texto_marcado,
        flags=re.IGNORECASE
    )
    
    # Marca vírgula + "e" + dia
    texto_marcado = re.sub(
        r',\s+e\s+(segunda|terça|quarta|quinta|sexta|sábado|domingo)',
        r' |||E_DIA||| \1',
        texto_marcado,
        flags=re.IGNORECASE
    )
    
    # Marca vírgula + "e" + "ainda"
    texto_marcado = re.sub(
        r',\s+e\s+ainda',
        ' |||E_AINDA||| ainda',
        texto_marcado,
        flags=re.IGNORECASE
    )
    
    # Divide pelos marcadores
    partes = re.split(r'\|\|\|(?:MAS|E_DIA|E_AINDA)\|\|\|', texto_marcado)
    
    blocos = []
    for i, parte in enumerate(partes):
        parte = parte.strip()
        if not parte:
            continue
        
        # Divide por ponto final e traço
        subpartes = re.split(r'\.\s+|—\s*', parte)
        for subparte in subpartes:
            subparte = subparte.strip()
            if subparte:
                blocos.append(subparte)
    
    return blocos


# =============================
# HELPERS DE EXTRAÇÃO
# =============================

def extract_valor(frase):
    """Extrai valores monetários: 2.500, 780, etc."""
    patterns = [
        r'\b(\d{1,3}(?:\.\d{3})+(?:,\d+)?)\b',  # 2.500 ou 2.500,50
        r'\b(\d{1,3}(?:,\d{3})+(?:\.\d+)?)\b',  # 2,500 ou 2,500.50
        r'\b(\d{4,})\b',                         # 2500 (4+ dígitos)
        r'\b(\d{3,})\b',                         # 780 (3+ dígitos)
    ]
    
    for pattern in patterns:
        match = re.search(pattern, frase)
        if match:
            return match.group(1)
    
    return ""


def extract_dias(frase):
    """Extrai todos os dias da semana mencionados."""
    return re.findall(
        r"(segunda|terça|quarta|quinta|sexta|sábado|domingo)",
        frase.lower()
    )


def extract_cliente_receita(frase):
    """Extrai cliente de receitas: recebi X da Ana"""
    match = re.search(
        r'recebi.*?(?:da|do)\s+([A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-záéíóúâêôãõç]+)',
        frase,
        re.IGNORECASE
    )
    if match:
        return match.group(1)
    
    match = re.search(
        r'\b([A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-záéíóúâêôãõç]+)\s+(?:me\s+)?(?:pagou|transferiu|depositou)',
        frase
    )
    if match:
        return match.group(1)
    
    match = re.search(
        r'(?:da|do)\s+([A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-záéíóúâêôãõç]+)',
        frase
    )
    if match:
        return match.group(1)
    
    return ""


def extract_clientes_orcamento(frase):
    """Extrai clientes de orçamentos: marquei orçamento com a Joana e com o Carlos"""
    clientes = []
    
    # Padrão: "com a Joana", "com o Carlos"
    matches = re.findall(
        r'com\s+(?:a\s+|o\s+)?([A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-záéíóúâêôãõç]+)',
        frase
    )
    clientes.extend(matches)
    
    # Remove duplicatas mantendo ordem
    seen = set()
    return [c for c in clientes if c not in seen and not seen.add(c)]


def extract_cliente_tarefa(frase):
    """Extrai cliente de tarefas: revisar o orçamento da casa da Maria"""
    # Padrão específico: "da casa da Maria" ou "do orçamento da Maria"
    match = re.search(
        r'(?:da|do)\s+(?:casa\s+da\s+|orçamento\s+(?:do\s+|da\s+))?([A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-záéíóúâêôãõç]+)',
        frase
    )
    if match:
        return match.group(1)
    
    # Fallback: "da Maria" ou "do João"
    match = re.search(
        r'(?:da|do)\s+([A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-záéíóúâêôãõç]+)',
        frase
    )
    if match:
        return match.group(1)
    
    return ""


def extract_confirmacao_orcamento(frase):
    """Detecta confirmações: Carlos só confirmou para terça"""
    if any(p in frase.lower() for p in ['confirmou', 'confirmou para', 'confirmado']):
        match = re.search(
            r'\b([A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-záéíóúâêôãõç]+)\s+(?:só\s+)?confirmou',
            frase
        )
        cliente = match.group(1) if match else ""
        
        dias = extract_dias(frase)
        dia = dias[0] if dias else ""
        
        return {"cliente": cliente, "dia": dia}
    
    return None


# =============================
# CLASSIFICADOR PRINCIPAL
# =============================

def classify_text(texto):
    """
    Classifica texto em eventos financeiros e de tarefas.
    Implementa lógica para evitar duplicações e confusões.
    """
    eventos = []
    blocos = split_intencoes(texto)
    
    # Primeira passagem: classifica todos os eventos
    for bloco in blocos:
        bloco = bloco.strip()
        if not bloco:
            continue
        
        bloco_lower = bloco.lower()
        
        # =============================
        # RECEITA (prioridade alta)
        # =============================
        if any(p in bloco_lower for p in [
            "recebi", "me pagou", "transferiu", "depositou", 
            "entrou", "pagamento recebido"
        ]):
            cliente = extract_cliente_receita(bloco)
            valor = extract_valor(bloco)
            dias = extract_dias(bloco)
            
            eventos.append({
                "tipo": "receita",
                "dados": {
                    "cliente": cliente,
                    "valor": valor,
                    "dias": dias if dias else []
                }
            })
            continue
        
        # =============================
        # DESPESA (prioridade alta)
        # =============================
        if any(p in bloco_lower for p in [
            "paguei", "comprei", "gastei", "gasto", 
            "compra", "despesa", "paguei por"
        ]):
            valor = extract_valor(bloco)
            dias = extract_dias(bloco)
            
            eventos.append({
                "tipo": "despesa",
                "dados": {
                    "descricao": bloco,
                    "valor": valor,
                    "dias": dias if dias else []
                }
            })
            continue
        
        # =============================
        # CONFIRMAÇÃO DE ORÇAMENTO (verifica ANTES de tarefa)
        # =============================
        confirmacao = extract_confirmacao_orcamento(bloco)
        if confirmacao and confirmacao["cliente"]:
            eventos.append({
                "tipo": "confirmacao_orcamento",
                "dados": {
                    "cliente": confirmacao["cliente"],
                    "dias": [confirmacao["dia"]] if confirmacao["dia"] else []
                }
            })
            continue
        
        # =============================
        # TAREFA (prioridade sobre orçamento quando há ação)
        # =============================
        # Se tem palavras de ação + "orçamento", é tarefa, não orçamento
        if any(p in bloco_lower for p in [
            "tenho que", "preciso", "ir", "terminar", "revisar", 
            "voltar", "fazer", "preciso fazer", "tenho que fazer",
            "vou", "devo", "preciso ir"
        ]):
            cliente = extract_cliente_tarefa(bloco)
            dias = extract_dias(bloco)
            
            eventos.append({
                "tipo": "tarefa",
                "dados": {
                    "cliente": cliente,
                    "descricao": bloco,
                    "dias": dias if dias else []
                }
            })
            continue
        
        
        # =============================
        # ORÇAMENTO NORMAL
        # =============================
        if any(p in bloco_lower for p in [
            "orçamento", "marquei", "agendei", "marcar", "agendar"
        ]):
            clientes = extract_clientes_orcamento(bloco)
            dias = extract_dias(bloco)
            
            if clientes:
                # Se tem múltiplos clientes e múltiplos dias, associa sequencialmente
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
                    # Se tem mais clientes que dias, usa o último dia para os extras
                    dia_padrao = dias[-1] if dias else ""
                    for cliente in clientes:
                        dia = dias[clientes.index(cliente)] if clientes.index(cliente) < len(dias) else dia_padrao
                        eventos.append({
                            "tipo": "orcamento_agendado",
                            "dados": {
                                "cliente": cliente,
                                "dias": [dia] if dia else []
                            }
                        })
            continue
        
        # =============================
        # NÃO CLASSIFICADO
        # =============================
        eventos.append({
            "tipo": "nao_classificado",
            "dados": {
                "descricao": bloco
            }
        })
    
    # Segunda passagem: processa confirmações e remove duplicatas
    eventos_finais = []
    orcamentos_processados = {}  # {cliente: índice no eventos_finais}
    
    for evento in eventos:
        if evento["tipo"] == "confirmacao_orcamento":
            # Atualiza orçamento existente ou adiciona novo
            cliente = evento["dados"]["cliente"]
            novo_dia = evento["dados"]["dias"][0] if evento["dados"]["dias"] else ""
            
            if cliente in orcamentos_processados:
                # Atualiza orçamento existente
                idx = orcamentos_processados[cliente]
                eventos_finais[idx]["dados"]["dias"] = [novo_dia] if novo_dia else []
            else:
                # Cria novo orçamento
                eventos_finais.append({
                    "tipo": "orcamento_agendado",
                    "dados": {
                        "cliente": cliente,
                        "dias": [novo_dia] if novo_dia else []
                    }
                })
                orcamentos_processados[cliente] = len(eventos_finais) - 1
        elif evento["tipo"] == "orcamento_agendado":
            cliente = evento["dados"]["cliente"]
            # Se já existe confirmação para este cliente, pula o orçamento inicial
            if cliente not in orcamentos_processados:
                eventos_finais.append(evento)
                orcamentos_processados[cliente] = len(eventos_finais) - 1
        else:
            # Outros tipos de eventos são adicionados normalmente
            eventos_finais.append(evento)
    
    return eventos_finais
